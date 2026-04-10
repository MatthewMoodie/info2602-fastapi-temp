# ================================================================
# PAGINATION SCENARIO 3: PAGINATED COMMENTS / GRANDCHILDREN
# ================================================================
# Use when: column 3 (comments/reviews/feedback) has many entries
#           and needs to be paged through.
# Example: a track with many comments, a product with many reviews
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

# ── Parent ───────────────────────────────────────────────────────
# PLUG: rename Album and fields
class Album(SQLModel, table=True):
    id:     Optional[int] = Field(default=None, primary_key=True)
    title:  str
    artist: str
    image:  str = ""

# ── Child ────────────────────────────────────────────────────────
# PLUG: rename Track and fields
class Track(SQLModel, table=True):
    id:       Optional[int] = Field(default=None, primary_key=True)
    title:    str
    duration: str = ""
    album_id: Optional[int] = Field(default=None, foreign_key="album.id")

# ── Grandchild ───────────────────────────────────────────────────
# PLUG: rename Comment and fields
class Comment(SQLModel, table=True):
    id:       Optional[int] = Field(default=None, primary_key=True)
    text:     str
    username: str
    track_id: Optional[int] = Field(default=None, foreign_key="track.id")


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
        bob_db = User.model_validate(bob)
        db.add(bob_db)
        db.commit()

        # PLUG: rename Album, field values
        a1 = Album(title="Album One", artist="Artist 1", image="https://weblabs.web.app/api/brainrot/1.webp")
        db.add(a1)
        db.commit()

        # PLUG: rename Track, album_id, field values
        t1 = Track(title="Track 1", duration="3:20", album_id=a1.id)
        db.add(t1)
        db.commit()

        # Add enough comments to see pagination
        # PLUG: rename Comment, track_id, text values
        comments = [
            Comment(username="bob", text=f"Comment number {i}", track_id=t1.id)
            for i in range(1, 20)   # 19 comments = 2+ pages at 8 per page
        ]
        db.add_all(comments)
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
from app.models import User, Album, Track, Comment   # PLUG: your models
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

@app.get('/app')
def home_view(request: Request, user: AuthDep, db: SessionDep):
    albums = db.exec(select(Album)).all()
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"albums": albums}
    )

@app.get('/app/albums/{album_id}')
def album_view(request: Request, user: AuthDep, db: SessionDep, album_id: int):
    albums         = db.exec(select(Album)).all()
    selected_album = db.get(Album, album_id)
    tracks         = db.exec(select(Track).where(Track.album_id == album_id)).all()
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"albums": albums, "selected_album": selected_album, "tracks": tracks}
    )

# View track + paginated comments
# PLUG: rename /app/tracks/{id}, Track, Comment, Comment.track_id
# PLUG: change ITEMS_PER_PAGE
@app.get('/app/tracks/{track_id}')
def track_view(request: Request, user: AuthDep, db: SessionDep,
               track_id: int, page: int = 1):

    ITEMS_PER_PAGE = 8                  # PLUG: change this number

    selected_track = db.get(Track, track_id)
    selected_album = db.get(Album, selected_track.album_id)
    albums         = db.exec(select(Album)).all()
    tracks         = db.exec(select(Track).where(Track.album_id == selected_track.album_id)).all()

    # Count comments for this track
    total = db.exec(
        select(func.count(Comment.id)).where(Comment.track_id == track_id)  # PLUG: FK
    ).one()

    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page        = max(1, min(page, total_pages if total_pages > 0 else 1))
    offset      = (page - 1) * ITEMS_PER_PAGE

    comments = db.exec(
        select(Comment)
        .where(Comment.track_id == track_id)    # PLUG: FK field
        .offset(offset)
        .limit(ITEMS_PER_PAGE)
    ).all()

    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "albums":         albums,
            "selected_album": selected_album,
            "tracks":         tracks,
            "selected_track": selected_track,
            "comments":       comments,
            "page":           page,
            "total_pages":    total_pages,
            "track_id":       track_id,         # needed for pagination URLs
        }
    )

# Add comment — redirects back to page 1 after adding
# PLUG: rename /app/tracks/{id}/comments, Comment, track_id, text
@app.post('/app/tracks/{track_id}/comments')
def add_comment(request: Request, user: AuthDep, db: SessionDep,
                track_id: int, text: str = Form()):
    db.add(Comment(username=user.username, text=text, track_id=track_id))
    db.commit()
    return RedirectResponse(url=f"/app/tracks/{track_id}?page=1", status_code=status.HTTP_303_SEE_OTHER)

# Delete comment — redirects back to page 1 after deleting
# PLUG: rename /app/comments/{id}/delete, Comment
@app.post('/app/comments/{comment_id}/delete')
def delete_comment(request: Request, user: AuthDep, db: SessionDep, comment_id: int):
    comment = db.get(Comment, comment_id)
    if comment and comment.username == user.username:
        track_id = comment.track_id
        db.delete(comment)
        db.commit()
        return RedirectResponse(url=f"/app/tracks/{track_id}?page=1", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/app", status_code=status.HTTP_303_SEE_OTHER)


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

    <!-- COLUMN 1 -->
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

    <!-- COLUMN 2 -->
    <!-- PLUG: rename selected_album, tracks, track, /app/tracks/{{ track.id }}, fields -->
    <div class="col s4 m5" style="display:flex; flex-direction:column;">
      <h6>{% if selected_album %}{{ selected_album.title }} Tracks{% else %}Selected Album Tracks{% endif %}</h6>
      <div style="overflow-y:scroll; flex:1;">
        {% if tracks %}
          {% for track in tracks %}
          <div class="card">
            <div class="card-content">
              <span>{{ track.title }}</span>
              <a href="/app/tracks/{{ track.id }}" class="btn-small right waves-effect purple lighten-1">
                View Comments >
              </a>
            </div>
          </div>
          {% endfor %}
        {% else %}
          <p class="grey-text" style="padding:8px;">{% if selected_album %}No tracks.{% else %}Select an album.{% endif %}</p>
        {% endif %}
      </div>
    </div>

    <!-- COLUMN 3: paginated comments -->
    <!-- PLUG: rename selected_track, comments, comment, fields -->
    <!-- PLUG: pagination URLs /app/tracks/{{ track_id }}?page=X -->
    <!-- PLUG: form action /app/tracks/{{ selected_track.id }}/comments -->
    <!-- PLUG: delete action /app/comments/{{ comment.id }}/delete -->
    <div class="col s4 m4" style="display:flex; flex-direction:column;">
      <h6>{% if selected_track %}Comments – {{ selected_track.title }}{% else %}Selected Track Comments{% endif %}</h6>

      {% if selected_track %}

        <!-- ADD COMMENT FORM -->
        <form class="row" action="/app/tracks/{{ selected_track.id }}/comments" method="POST" style="margin-bottom:0;">
          <div class="input-field col s9">
            <input type="text" name="text" id="comment" placeholder="Write a comment…">
            <label for="comment">Comment</label>
          </div>
          <div class="col s3" style="display:flex; align-items:center;">
            <button class="btn waves-effect purple waves-light" type="submit">Add</button>
          </div>
        </form>

        <!-- COMMENT LIST -->
        <div style="overflow-y:scroll; flex:1;">
          <ul class="collection">
            {% for comment in comments %}
            <li class="collection-item">
              <strong>{{ comment.username }}:</strong> {{ comment.text }}
              {% if comment.username == user.username %}
              <form action="/app/comments/{{ comment.id }}/delete" method="POST" style="display:inline;">
                <button type="submit" class="secondary-content btn-flat" style="padding:0;">
                  <i class="material-icons">delete</i>
                </button>
              </form>
              {% endif %}
            </li>
            {% else %}
              <li class="collection-item grey-text">No comments yet.</li>
            {% endfor %}
          </ul>
        </div>

        <!-- PAGINATION CONTROLS for column 3 -->
        <!-- PLUG: /app/tracks/{{ track_id }} → your child detail route -->
        <div class="center-align" style="padding:8px; border-top:1px solid #ddd;">

          {% if page > 1 %}
            <a href="/app/tracks/{{ track_id }}?page={{ page - 1 }}" class="btn-small purple waves-effect">
              <i class="material-icons">chevron_left</i>
            </a>
          {% else %}
            <a class="btn-small disabled">
              <i class="material-icons">chevron_left</i>
            </a>
          {% endif %}

          <span style="margin:0 8px;">{{ page }} / {{ total_pages if total_pages > 0 else 1 }}</span>

          {% if page < total_pages %}
            <a href="/app/tracks/{{ track_id }}?page={{ page + 1 }}" class="btn-small purple waves-effect">
              <i class="material-icons">chevron_right</i>
            </a>
          {% else %}
            <a class="btn-small disabled">
              <i class="material-icons">chevron_right</i>
            </a>
          {% endif %}

        </div>

      {% else %}
        <p class="grey-text" style="padding:8px;">Select a track to view comments.</p>
      {% endif %}

    </div>

  </main>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
  <script>M.AutoInit();</script>
</body>
</html>
"""
