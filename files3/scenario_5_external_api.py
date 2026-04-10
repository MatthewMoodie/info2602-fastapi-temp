# ================================================================
# SCENARIO 5: EXTERNAL API  (Fetch + Display + Save to DB)
# ================================================================
# Use when: the exam gives you an API URL to pull data from.
# Pattern: fetch from API → display in template →
#          user clicks Save → POST stores it in your DB
# ================================================================


# ================================================================
# models.py
# ================================================================

from sqlmodel import Field, SQLModel
from typing import Optional

# Your regular models still go here
class Album(SQLModel, table=True):              # PLUG: rename/keep if needed
    id:     int | None = Field(default=None, primary_key=True)
    title:  str
    artist: str
    image:  str = ""

# SavedItem = model for storing whatever you fetched from the API
# PLUG: rename, change fields to match what the API returns
class SavedItem(SQLModel, table=True):          # PLUG: rename
    id:          int | None = Field(default=None, primary_key=True)
    external_id: str = ""       # the ID from the API response
    name:        str = ""       # PLUG: fields you want to store
    image_url:   str = ""       # PLUG: fields you want to store
    user_id:     int | None = Field(default=None, foreign_key="user.id")


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

        # Users
        db.add_all([
            User(username="user1", email="user1@mail.com", password=encrypt_password("pass123")),
            User(username="user2", email="user2@mail.com", password=encrypt_password("pass123")),
        ])
        db.commit()

        # NOTE: no need to seed API data — it's fetched live from the API
        print("Done.")

if __name__ == "__main__":
    cli()


# ================================================================
# app/routers/main.py
# ================================================================

import httpx
from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.database import SessionDep
from app.auth import AuthDep
from app.utilities.flash import flash, get_flashed_messages
from app.models import Album, SavedItem     # PLUG: your models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
templates.env.globals['get_flashed_messages'] = get_flashed_messages

# Home — shows your DB data
# PLUG: rename Album, "albums"
@router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: AuthDep, db: SessionDep):
    albums = db.exec(select(Album)).all()   # PLUG
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"request": request, "user": user, "albums": albums}
    )

# Browse — fetches and displays items from external API
# PLUG: rename /browse, API_URL, "api_items"
@router.get("/browse", response_class=HTMLResponse)
async def browse(request: Request, user: AuthDep, db: SessionDep):

    # PLUG: replace with the API URL given in the exam
    API_URL = "https://weblabs.web.app/api/brainrot"

    async with httpx.AsyncClient() as client:
        response = await client.get(API_URL)
        data = response.json()

    # PLUG: adjust based on what the API returns:
    # plain list        → items = data
    # {"results": [...] → items = data["results"]
    # {"data": [...]}   → items = data["data"]
    items = data    # PLUG

    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"request": request, "user": user, "api_items": items}
    )

# Save an API item to your DB
# PLUG: rename /save-item, SavedItem, form field names
@router.post("/save-item")
async def save_item(
    request:     Request,
    user:        AuthDep,
    db:          SessionDep,
    external_id: str = Form(...),   # PLUG: must match hidden input name=
    name:        str = Form(...),   # PLUG: must match hidden input name=
    image_url:   str = Form("")     # PLUG: must match hidden input name=
):
    # Prevent saving duplicates
    existing = db.exec(
        select(SavedItem).where(        # PLUG: rename SavedItem
            SavedItem.user_id     == user.id,
            SavedItem.external_id == external_id
        )
    ).first()

    if not existing:
        db.add(SavedItem(               # PLUG: rename + fields
            user_id=user.id,
            external_id=external_id,
            name=name,
            image_url=image_url
        ))
        db.commit()
        flash(request, "Saved!", "success")
    else:
        flash(request, "Already saved.", "warning")

    return RedirectResponse(url="/browse", status_code=status.HTTP_303_SEE_OTHER)


# ================================================================
# index.html
# ================================================================

"""
{% extends "authenticated-base.html" %}
{% block title %}App{% endblock %}
{% block subpage_content %}

<div class="row" style="margin:0; height:85vh;">

  <!-- COLUMN 1: your DB data (albums, saved items etc.) -->
  <!-- PLUG: rename albums, album, fields -->
  <div class="col s4" style="height:100%; overflow-y:auto; border-right:1px solid #ddd; padding:10px;">
    <h5>Albums</h5>
    {% for album in albums %}
    <div class="card" style="margin-bottom:8px;">
      <div class="card-content" style="padding:8px;">
        <b>{{ album.title }}</b><br>
        <small class="grey-text">{{ album.artist }}</small>
      </div>
    </div>
    {% else %}
      <p class="grey-text">Nothing saved yet.</p>
    {% endfor %}
  </div>

  <!-- COLUMN 2: items from external API -->
  <!-- PLUG: rename api_items, item, field names — check what the API returns -->
  <div class="col s8" style="height:100%; overflow-y:auto; padding:10px;">
    <h5>Browse</h5>
    <a href="/browse" class="btn purple waves-effect" style="margin-bottom:10px;">Load from API</a>

    {% for item in api_items %}
    <div class="card" style="margin-bottom:8px;">
      <div class="card-content" style="padding:8px;">
        <div class="row valign-wrapper" style="margin:0;">
          <div class="col s2">
            <!-- PLUG: item.image → actual API field name for the image -->
            <img src="{{ item.image }}" style="width:60px;height:60px;object-fit:cover;border-radius:4px;">
          </div>
          <div class="col s7">
            <b>{{ item.name }}</b><br>         <!-- PLUG: API field -->
            <small class="grey-text">{{ item.type }}</small>  <!-- PLUG: API field -->
          </div>
          <div class="col s3 right-align">

            <!-- SAVE BUTTON -->
            <!-- PLUG: action="/save-item" → your save route           -->
            <!-- PLUG: hidden input name= must match Form(...) in route -->
            <!-- PLUG: value="{{ item.X }}" → actual API field names    -->
            <form action="/save-item" method="POST">
              <input type="hidden" name="external_id" value="{{ item.id }}">      <!-- PLUG -->
              <input type="hidden" name="name"         value="{{ item.name }}">   <!-- PLUG -->
              <input type="hidden" name="image_url"    value="{{ item.image }}">  <!-- PLUG -->
              <button type="submit" class="btn btn-small purple waves-effect">Save</button>
            </form>

          </div>
        </div>
      </div>
    </div>
    {% else %}
      {% if api_items is defined %}
        <p class="grey-text">No items returned from API.</p>
      {% endif %}
    {% endfor %}

    {% for message in get_flashed_messages(request) %}
      <div class="card-panel {{ message.type }}">{{ message.message }}</div>
    {% endfor %}
  </div>

</div>
{% endblock %}
"""
