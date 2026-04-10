# ================================================================
# PAGINATION SCENARIO 2: PAGINATED CHILDREN LIST
# ================================================================
# Use when: column 2 (the children) has many items
#           and needs to be paged through.
# Example: a plan with many exercises, album with many tracks
# The pagination controls sit at the bottom of column 2.
# ================================================================


# ================================================================
# models.py
# ================================================================

from sqlmodel import Field, SQLModel
from typing import Optional
from pydantic import EmailStr
from pwdlib import PasswordHash

# ── User (DO NOT CHANGE) ─────────────────────────────────────────
class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email:    EmailStr = Field(index=True, unique=True)
    password: str

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    def check_password(self, plaintext_password: str):
        return PasswordHash.recommended().verify(password=plaintext_password, hash=self.password)

# ── Parent model ─────────────────────────────────────────────────
# PLUG: rename Album and fields
class Album(SQLModel, table=True):
    id:     Optional[int] = Field(default=None, primary_key=True)
    title:  str
    artist: str
    image:  str = ""

# ── Child model ──────────────────────────────────────────────────
# PLUG: rename Track and fields
class Track(SQLModel, table=True):
    id:       Optional[int] = Field(default=None, primary_key=True)
    title:    str
    duration: str = ""
    album_id: Optional[int] = Field(default=None, foreign_key="album.id")


# ================================================================
# cli.py
# ================================================================

import typer
from app.database import create_db_and_tables, get_cli_session, drop_all
from app.models import *
from app.utilities import encrypt_password

cli = typer.Typer()

@cli.command()
def initialize():
    with get_cli_session() as db:
        drop_all()
        create_db_and_tables()

        bob = UserBase(username='bob', email='bob@mail.com', password=encrypt_password("bobpass"))
        db.add(User.model_validate(bob))
        db.commit()

        # PLUG: rename Album, field values
        a1 = Album(title="Album One",   artist="Artist 1", image="https://weblabs.web.app/api/brainrot/1.webp")
        a2 = Album(title="Album Two",   artist="Artist 2", image="https://weblabs.web.app/api/brainrot/2.webp")
        db.add_all([a1, a2])
        db.commit()

        # Add enough children to see pagination
        # PLUG: rename Track, album_id, field values
        tracks = [
            Track(title=f"Track {i}", duration=f"{3 + i % 3}:00", album_id=a1.id)
            for i in range(1, 16)   # 15 tracks = 2 pages at 8 per page
        ]
        db.add_all(tracks)
        db.commit()

        print("Database Initialized")

if __name__ == "__main__":
    cli()


# ================================================================
# main.py
# ================================================================

import uvicorn
from fastapi import FastAPI, Request, status, Form
from fastapi.responses import RedirectResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from app.config import get_settings
from app.dependencies import IsUserLoggedIn, SessionDep, AuthDep
from fastapi.templating import Jinja2Templates
from app.utilities import get_flashed_messages, flash
from jinja2 import Environment, FileSystemLoader
from sqlmodel import select, func
from app.models import User, Album, Track   # PLUG: your models
from fastapi.staticfiles import StaticFiles

app = FastAPI(middleware=[
    Middleware(SessionMiddleware, secret_key=get_settings().secret_key)
])

template_env = Environment(loader=FileSystemLoader("app/templates"))
template_env.globals['get_flashed_messages'] = get_flashed_messages
templates = Jinja2Templates(env=template_env)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ── Auth routes (DO NOT CHANGE) ──────────────────────────────────
@app.get('/', response_class=RedirectResponse)
async def index_view(request: Request, user_logged_in: IsUserLoggedIn):
    if user_logged_in:
        return RedirectResponse(url=request.url_for('home_view'), status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url=request.url_for('login_view'), status_code=status.HTTP_303_SEE_OTHER)

@app.get("/login")
async def login_view(user_logged_in: IsUserLoggedIn, request: Request):
    if user_logged_in:
        return RedirectResponse(url=request.url_for('home_view'), status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="login.html")

@app.post('/login')
def login_action(request: Request, db: SessionDep, username: str = Form(), password: str = Form()):
    from app.utilities import create_access_token
    user = db.exec(select(User).where(User.username == username)).one_or_none()
    if user and user.check_password(password):
        response = RedirectResponse(url=request.url_for("index_view"), status_code=status.HTTP_303_SEE_OTHER)
        access_token = create_access_token(data={"sub": f"{user.id}"})
        response.set_cookie(key="access_token", value=access_token, httponly=False, samesite="lax", secure=True)
        return response
    flash(request, 'Invalid username or password')
    return RedirectResponse(url=request.url_for('login_view'), status_code=status.HTTP_303_SEE_OTHER)

@app.get('/logout')
async def logout(request: Request):
    response = RedirectResponse(url=request.url_for("login_view"), status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token", httponly=True, samesite="none", secure=True)
    flash(request, 'Logged out')
    return response

# ── App routes ───────────────────────────────────────────────────

# Home — unpaginated parent list
# PLUG: rename Album, "albums"
@app.get('/app')
def home_view(request: Request, user: AuthDep, db: SessionDep):
    albums = db.exec(select(Album)).all()   # PLUG
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"albums": albums}
    )

# Click parent → paginated children list
# PLUG: rename /app/albums/{id}, Album, Track, Track.album_id
# PLUG: change ITEMS_PER_PAGE
@app.get('/app/albums/{album_id}')
def album_view(request: Request, user: AuthDep, db: SessionDep,
               album_id: int, page: int = 1):   # page param keeps track of current page

    ITEMS_PER_PAGE = 8                          # PLUG: change this number

    albums         = db.exec(select(Album)).all()
    selected_album = db.get(Album, album_id)    # PLUG

    # Count children for this parent
    total = db.exec(
        select(func.count(Track.id)).where(Track.album_id == album_id)  # PLUG: FK field
    ).one()

    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page        = max(1, min(page, total_pages if total_pages > 0 else 1))
    offset      = (page - 1) * ITEMS_PER_PAGE

    tracks = db.exec(
        select(Track)
        .where(Track.album_id == album_id)      # PLUG: FK field
        .offset(offset)
        .limit(ITEMS_PER_PAGE)
    ).all()

    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "albums":         albums,
            "selected_album": selected_album,
            "tracks":         tracks,           # PLUG
            "page":           page,
            "total_pages":    total_pages,
            "album_id":       album_id,         # needed for pagination URLs
        }
    )


# ================================================================
# index.html
# ================================================================

"""
<!doctype html>
<html lang="en">
<head>
  <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>LE App</title>
  <style>
    * { box-sizing: border-box; }
    .row { margin: 0; }
    body { display: flex; height: 100vh; flex-direction: column; }
    nav  { flex-grow: 1; margin-bottom: 0; }
    main { flex-grow: 28; display: flex; width: 100%; flex-direction: row; align-items: stretch; }
    .card { margin: 2px; }
  </style>
</head>
<body>

  <nav class="nav-extended purple">
    <div class="nav-wrapper">
      <span style="margin-left:10px;">LE App</span>
      <ul id="nav-mobile" class="right">
        <li><a href="/logout">Logout</a></li>
      </ul>
    </div>
  </nav>

  {% with messages = get_flashed_messages(request) %}
    {% if messages %}
      <div class="row" style="margin-top:10px; position:absolute; z-index:10; width:100vw;">
        {% for message in messages %}
          <div class="blue lighten-5 col s10 offset-s1">
            <div class="row">
              <div class="col s11" style="font-weight:bold; text-align:center;">{{ message }}</div>
              <div class="col s1"><a href="" style="font-size:1.5em">&times;</a></div>
            </div>
          </div>
        {% endfor %}
      </div>
    {% endif %}
  {% endwith %}

  <main class="row">

    <!-- COLUMN 1: parent list (no pagination here) -->
    <!-- PLUG: rename albums, album, /app/albums/{{ album.id }}, fields -->
    <div class="col s4 m3" style="display:flex; flex-direction:column;">
      <h6>Albums</h6>
      <div style="overflow-y:scroll; flex:1;">
        {% for album in albums %}
        <div class="card horizontal">
          <div class="card-stacked">
            <div class="card-content">
              <p><strong>{{ album.title }}</strong></p>
              <p>{{ album.artist }}</p>
              <a href="/app/albums/{{ album.id }}" class="btn-small waves-effect purple">View</a>
            </div>
          </div>
          <div class="card-image">
            <img src="{{ album.image }}" alt="cover">
          </div>
        </div>
        {% else %}
          <p class="grey-text" style="padding:8px;">Nothing here.</p>
        {% endfor %}
      </div>
    </div>

    <!-- COLUMN 2: paginated children -->
    <!-- PLUG: rename selected_album, tracks, track, /app/tracks/{{ track.id }}, fields -->
    <!-- PLUG: pagination URLs /app/albums/{{ album_id }}?page=X -->
    <div class="col s4 m5" style="display:flex; flex-direction:column;">
      <h6>{% if selected_album %}{{ selected_album.title }} Tracks{% else %}Selected Album Tracks{% endif %}</h6>

      <div style="overflow-y:scroll; flex:1;">
        {% if tracks %}
          {% for track in tracks %}
          <div class="card">
            <div class="card-content">
              <span>{{ track.title }}</span>
              <span class="grey-text"> — {{ track.duration }}</span>
              <a href="/app/tracks/{{ track.id }}" class="btn-small right waves-effect purple lighten-1">
                View >
              </a>
            </div>
          </div>
          {% endfor %}
        {% else %}
          <p class="grey-text" style="padding:8px;">
            {% if selected_album %}No tracks.{% else %}Select an album.{% endif %}
          </p>
        {% endif %}
      </div>

      <!-- PAGINATION CONTROLS for column 2 -->
      <!-- PLUG: /app/albums/{{ album_id }} → your parent detail route -->
      {% if selected_album %}
      <div class="center-align" style="padding:8px; border-top:1px solid #ddd;">

        {% if page > 1 %}
          <a href="/app/albums/{{ album_id }}?page={{ page - 1 }}" class="btn-small purple waves-effect">
            <i class="material-icons">chevron_left</i>
          </a>
        {% else %}
          <a class="btn-small disabled">
            <i class="material-icons">chevron_left</i>
          </a>
        {% endif %}

        <span style="margin:0 8px;">{{ page }} / {{ total_pages }}</span>

        {% if page < total_pages %}
          <a href="/app/albums/{{ album_id }}?page={{ page + 1 }}" class="btn-small purple waves-effect">
            <i class="material-icons">chevron_right</i>
          </a>
        {% else %}
          <a class="btn-small disabled">
            <i class="material-icons">chevron_right</i>
          </a>
        {% endif %}

      </div>
      {% endif %}

    </div>

    <!-- COLUMN 3: placeholder -->
    <div class="col s4 m4" style="display:flex; flex-direction:column;">
      <h6>Details</h6>
      <p class="grey-text" style="padding:8px;">Select a track.</p>
    </div>

  </main>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
  <script>M.AutoInit();</script>
</body>
</html>
"""
