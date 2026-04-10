# ================================================================
# PAGINATION SCENARIO 1: PAGINATED PARENT LIST
# ================================================================
# Use when: the parent list (column 1) has too many items
#           and needs to be split across pages.
# Pattern: ?page=1 in the URL, offset/limit in the query
# Example: browsing a large list of Movies, Albums, Plans
# ================================================================
# HOW PAGINATION WORKS:
#   page 1 → skip 0,  show items 1-10
#   page 2 → skip 10, show items 11-20
#   page 3 → skip 20, show items 21-30
#   offset = (page - 1) * limit
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

        # Add enough parents to actually see pagination working
        # PLUG: rename Album, change fields and values
        # 15 records = 2 pages at 8 per page
        albums = [
            Album(title=f"Album {i}", artist=f"Artist {i}", image=f"https://weblabs.web.app/api/brainrot/{(i % 10) + 1}.webp")
            for i in range(1, 16)
        ]
        db.add_all(albums)
        db.commit()

        # PLUG: rename Track, album_id, field values
        for album in albums[:3]:
            db.add_all([
                Track(title=f"Track 1", duration="3:00", album_id=album.id),
                Track(title=f"Track 2", duration="4:00", album_id=album.id),
            ])
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

# Home — paginated parent list
# PLUG: rename Album, "albums"
# PLUG: change ITEMS_PER_PAGE to however many items per page you want
@app.get('/app')
def home_view(request: Request, user: AuthDep, db: SessionDep,
              page: int = 1):          # ?page=1 — keep this param name

    ITEMS_PER_PAGE = 8                 # PLUG: change this number

    # Count total records for calculating total pages
    total = db.exec(select(func.count(Album.id))).one()   # PLUG: rename Album

    # Calculate total pages — always round UP
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    # Clamp page to valid range
    page = max(1, min(page, total_pages))

    # offset = how many records to skip
    offset = (page - 1) * ITEMS_PER_PAGE

    albums = db.exec(
        select(Album).offset(offset).limit(ITEMS_PER_PAGE)  # PLUG: rename Album
    ).all()

    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "albums":       albums,        # PLUG
            "page":         page,          # current page number
            "total_pages":  total_pages,   # for rendering page buttons
        }
    )

# Click parent → load children (no pagination needed here usually)
# PLUG: rename /app/albums/{id}, Album, Track, Track.album_id
@app.get('/app/albums/{album_id}')
def album_view(request: Request, user: AuthDep, db: SessionDep, album_id: int):
    albums         = db.exec(select(Album)).all()
    selected_album = db.get(Album, album_id)
    tracks         = db.exec(select(Track).where(Track.album_id == album_id)).all()
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "albums":         albums,
            "selected_album": selected_album,
            "tracks":         tracks,
            "page":           1,
            "total_pages":    1,
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

    <!-- COLUMN 1: paginated parent list -->
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
          <p class="grey-text" style="padding:8px;">Nothing here yet.</p>
        {% endfor %}

      </div>

      <!-- PAGINATION CONTROLS -->
      <!-- PLUG: /app → your list route -->
      <!-- these always stay the same — just change the route URL -->
      <div class="center-align" style="padding:8px; border-top:1px solid #ddd;">

        <!-- Previous button — disabled on page 1 -->
        {% if page > 1 %}
          <a href="/app?page={{ page - 1 }}" class="btn-small purple waves-effect">
            <i class="material-icons">chevron_left</i>
          </a>
        {% else %}
          <a class="btn-small disabled">
            <i class="material-icons">chevron_left</i>
          </a>
        {% endif %}

        <!-- Page indicator -->
        <span style="margin:0 8px;">{{ page }} / {{ total_pages }}</span>

        <!-- Next button — disabled on last page -->
        {% if page < total_pages %}
          <a href="/app?page={{ page + 1 }}" class="btn-small purple waves-effect">
            <i class="material-icons">chevron_right</i>
          </a>
        {% else %}
          <a class="btn-small disabled">
            <i class="material-icons">chevron_right</i>
          </a>
        {% endif %}

      </div>
    </div>

    <!-- COLUMN 2: children of selected parent -->
    <!-- PLUG: rename selected_album, tracks, track, fields -->
    <div class="col s4 m5" style="display:flex; flex-direction:column;">
      <h6>{% if selected_album %}{{ selected_album.title }} Tracks{% else %}Selected Album Tracks{% endif %}</h6>
      <div style="overflow-y:scroll; flex:1;">
        {% if tracks %}
          {% for track in tracks %}
          <div class="card">
            <div class="card-content">
              <span>{{ track.title }}</span>
              <span class="grey-text"> — {{ track.duration }}</span>
            </div>
          </div>
          {% endfor %}
        {% else %}
          <p class="grey-text" style="padding:8px;">
            {% if selected_album %}No tracks.{% else %}Select an album.{% endif %}
          </p>
        {% endif %}
      </div>
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
