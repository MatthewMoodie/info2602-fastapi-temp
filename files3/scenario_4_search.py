# ================================================================
# SCENARIO 4: SEARCH & FILTER
# ================================================================
# Use when: there is a search bar to filter a list.
# Only difference from Scenario 1 is the list route accepts
# a ?q= param and filters results before passing to template.
# ================================================================


# ================================================================
# models.py
# ================================================================

from sqlmodel import Field, SQLModel
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
    album_id: int | None = Field(default=None, foreign_key="album.id")  # PLUG


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

        # PLUG: rename Album, change field values
        a1 = Album(title="Album One",   artist="Artist 1", image="https://weblabs.web.app/api/brainrot/1.webp")
        a2 = Album(title="Album Two",   artist="Artist 2", image="https://weblabs.web.app/api/brainrot/2.webp")
        a3 = Album(title="Album Three", artist="Artist 3", image="https://weblabs.web.app/api/brainrot/3.webp")
        db.add_all([a1, a2, a3])
        db.commit()

        # PLUG: rename Track, album_id, field values
        t1 = Track(title="Track 1", duration="3:20", album_id=a1.id)
        t2 = Track(title="Track 2", duration="4:05", album_id=a1.id)
        t3 = Track(title="Track 3", duration="2:55", album_id=a2.id)
        t4 = Track(title="Track 4", duration="3:10", album_id=a3.id)
        db.add_all([t1, t2, t3, t4])
        db.commit()

        db.add_all([
            User(username="user1", email="user1@mail.com", password=encrypt_password("pass123")),
            User(username="user2", email="user2@mail.com", password=encrypt_password("pass123")),
        ])
        db.commit()
        print("Done.")

if __name__ == "__main__":
    cli()


# ================================================================
# app/routers/main.py
# ================================================================

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

# Home — list with search
# KEY DIFFERENCE FROM SCENARIO 1: add  q: str = None  and the if q: block
# PLUG: rename Album, "albums", Album.title to the field you want to search
@router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: AuthDep, db: SessionDep, q: str = None):
    statement = select(Album)   # PLUG

    if q:
        # Search ONE field — PLUG: Album.title → YourModel.field
        statement = statement.where(Album.title.ilike(f"%{q}%"))

        # Search MULTIPLE fields (OR) — uncomment and rename if needed
        # statement = statement.where(
        #     Album.title.ilike(f"%{q}%")  |
        #     Album.artist.ilike(f"%{q}%")
        # )

    albums = db.exec(statement).all()   # PLUG: rename

    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "request": request, "user": user,
            "albums": albums,   # PLUG
            "q": q,             # pass back so input stays filled
        }
    )

# Click parent → load children
# PLUG: rename /albums/{album_id}, Album, Track, Track.album_id
@router.get("/albums/{album_id}", response_class=HTMLResponse)
async def get_album(request: Request, user: AuthDep, db: SessionDep, album_id: int):
    albums         = db.exec(select(Album)).all()
    selected_album = db.get(Album, album_id)
    tracks         = db.exec(select(Track).where(Track.album_id == album_id)).all()
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "request": request, "user": user,
            "albums": albums, "selected_album": selected_album,
            "tracks": tracks, "q": None,
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

  <!-- COLUMN 1: parent list with search -->
  <!-- PLUG: rename albums, album, /albums/{{ album.id }}, fields -->
  <div class="col s4" style="height:100%; overflow-y:auto; border-right:1px solid #ddd; padding:10px;">
    <h5>Albums</h5>

    <!-- SEARCH BAR — PLUG: action="/" → your list route -->
    <form action="/" method="GET" style="margin-bottom:10px;">
      <div style="display:flex; gap:8px; align-items:center;">
        <input type="text" name="q" value="{{ q or '' }}"
               placeholder="Search…" style="flex:1;">
        <button type="submit" class="btn btn-small purple waves-effect">
          <i class="material-icons">search</i>
        </button>
      </div>
    </form>
    {% if q %}
      <a href="/" class="btn-flat btn-small grey-text" style="margin-bottom:6px;">✕ Clear</a>
    {% endif %}

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
      <p class="grey-text">
        {% if q %}No results for "{{ q }}".{% else %}Nothing here yet.{% endif %}
      </p>
    {% endfor %}
  </div>

  <!-- COLUMN 2: children of selected parent -->
  <!-- PLUG: rename selected_album, tracks, track, fields -->
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
      <p class="grey-text">{% if selected_album %}No tracks.{% else %}Select an album.{% endif %}</p>
    {% endif %}
  </div>

  <!-- COLUMN 3: placeholder -->
  <div class="col s4" style="height:100%; overflow-y:auto; padding:10px;">
    <p class="grey-text">Select a track.</p>
  </div>

</div>
{% endblock %}
"""
