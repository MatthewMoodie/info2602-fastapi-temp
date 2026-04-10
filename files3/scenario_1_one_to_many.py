# ================================================================
# SCENARIO 1: ONE-TO-MANY  (Parent → Children)
# ================================================================
# This is the BASE of every exam. Always start here.
# Example: Album has many Tracks
# PLUG = rename to match whatever the exam domain is
# ================================================================


# ================================================================
# models.py
# ================================================================

from sqlmodel import Field, SQLModel, Relationship
from typing import Optional

class Album(SQLModel, table=True):              # PLUG: rename
    id:     int | None = Field(default=None, primary_key=True)
    title:  str                                 # PLUG: your fields
    artist: str                                 # PLUG: your fields
    image:  str = ""                            # PLUG: remove if not needed

class Track(SQLModel, table=True):              # PLUG: rename
    id:       int | None = Field(default=None, primary_key=True)
    title:    str                               # PLUG: your fields
    duration: str = ""                          # PLUG: your fields

    # PLUG: rename album_id and "album.id" to match your parent table name
    album_id: int | None = Field(default=None, foreign_key="album.id")


# ================================================================
# cli.py
# ================================================================

import typer
from app.database import create_db_and_tables, get_cli_session, drop_all
from app.models import *
from app.auth import encrypt_password

cli = typer.Typer()

@cli.command()
def initialize():
    with get_cli_session() as db:
        drop_all()
        create_db_and_tables()

        # Level 1: parents first
        # PLUG: rename Album, change field values
        a1 = Album(title="Album One",   artist="Artist 1", image="https://weblabs.web.app/api/brainrot/1.webp")
        a2 = Album(title="Album Two",   artist="Artist 2", image="https://weblabs.web.app/api/brainrot/2.webp")
        a3 = Album(title="Album Three", artist="Artist 3", image="https://weblabs.web.app/api/brainrot/3.webp")
        db.add_all([a1, a2, a3])
        db.commit()  # ← MUST commit before using .id below

        # Level 2: children (need parent .id)
        # PLUG: rename Track, album_id, field values
        t1 = Track(title="Track 1", duration="3:20", album_id=a1.id)
        t2 = Track(title="Track 2", duration="4:05", album_id=a1.id)
        t3 = Track(title="Track 3", duration="2:55", album_id=a2.id)
        t4 = Track(title="Track 4", duration="3:10", album_id=a3.id)
        db.add_all([t1, t2, t3, t4])
        db.commit()

        # Users (always include)
        db.add_all([
            User(username="user1", email="user1@mail.com", password=encrypt_password("pass123")),
            User(username="user2", email="user2@mail.com", password=encrypt_password("pass123")),
        ])
        db.commit()
        print("Done.")

if __name__ == "__main__":
    cli()


# ================================================================
# main.py
# ================================================================

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers.auth import auth_router
from app.routers.main import main_router

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(auth_router)
app.include_router(main_router)

# ---- app/routers/main.py ----

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.database import SessionDep
from app.auth import AuthDep
from app.utilities.flash import flash, get_flashed_messages
from app.models import Album, Track     # PLUG: your models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
templates.env.globals['get_flashed_messages'] = get_flashed_messages

# Home — load all parents for column 1
# PLUG: rename Album, "albums"
@router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: AuthDep, db: SessionDep):
    albums = db.exec(select(Album)).all()   # PLUG
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"request": request, "user": user, "albums": albums}
    )

# Click a parent → load its children for column 2
# PLUG: rename /albums/{album_id}, Album, Track, Track.album_id
@router.get("/albums/{album_id}", response_class=HTMLResponse)
async def get_album(request: Request, user: AuthDep, db: SessionDep, album_id: int):
    albums         = db.exec(select(Album)).all()
    selected_album = db.get(Album, album_id)                            # PLUG
    tracks         = db.exec(
        select(Track).where(Track.album_id == album_id)                 # PLUG: FK field
    ).all()
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "request": request, "user": user,
            "albums":         albums,
            "selected_album": selected_album,   # PLUG
            "tracks":         tracks,           # PLUG
        }
    )


# ================================================================
# index.html
# ================================================================

"""
{% extends "authenticated-base.html" %}
{% block title %}App{% endblock %}
{% block subpage_content %}

<div class="row" style="margin:0; height:85vh;">

  <!-- COLUMN 1: parent list -->
  <!-- PLUG: rename albums, album, route /albums/{{ album.id }}, fields -->
  <div class="col s4" style="height:100%; overflow-y:auto; border-right:1px solid #ddd; padding:10px;">
    <h5>Albums</h5>
    {% for album in albums %}
    <div class="card" style="margin-bottom:8px;">
      <div class="card-content" style="padding:8px;">
        <div class="row valign-wrapper" style="margin:0;">
          <div class="col s8">
            <b>{{ album.title }}</b><br>
            <small class="grey-text">{{ album.artist }}</small>
          </div>
          <div class="col s4">
            <img src="{{ album.image }}" style="width:50px;height:50px;object-fit:cover;border-radius:4px;">
          </div>
        </div>
      </div>
      <div class="card-action" style="padding:6px 10px;">
        <a href="/albums/{{ album.id }}" class="btn btn-small purple waves-effect">View</a>
      </div>
    </div>
    {% else %}
      <p class="grey-text">Nothing here.</p>
    {% endfor %}
  </div>

  <!-- COLUMN 2: children of selected parent -->
  <!-- PLUG: rename selected_album, tracks, track, route /tracks/{{ track.id }}, fields -->
  <div class="col s4" style="height:100%; overflow-y:auto; border-right:1px solid #ddd; padding:10px;">
    <h5>
      {% if selected_album %}{{ selected_album.title }} Tracks
      {% else %}Select an Album{% endif %}
    </h5>
    {% if tracks %}
      {% for track in tracks %}
      <div class="card" style="margin-bottom:8px;">
        <div class="card-content" style="padding:8px;">
          <b>{{ track.title }}</b>
          <span class="grey-text"> — {{ track.duration }}</span>
        </div>
        <div class="card-action" style="padding:6px 10px;">
          <a href="/tracks/{{ track.id }}" class="btn btn-small btn-flat purple-text">View</a>
        </div>
      </div>
      {% endfor %}
    {% else %}
      <p class="grey-text">{% if selected_album %}No tracks yet.{% else %}Select an album.{% endif %}</p>
    {% endif %}
  </div>

  <!-- COLUMN 3: placeholder — fill from other scenarios -->
  <div class="col s4" style="height:100%; overflow-y:auto; padding:10px;">
    <p class="grey-text">Select a track.</p>
  </div>

</div>
{% endblock %}
"""
