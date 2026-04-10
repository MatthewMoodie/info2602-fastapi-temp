# ================================================================
# SCENARIO 2: MANY-TO-MANY  (Link/Junction Table)
# ================================================================
# Use when: a user can interact with many items AND an item
#           can be interacted with by many users.
# Example: User likes/dislikes a Track
# Example: User enrols in a Course
# Example: User saves a Post
# ================================================================
# RULE: link table always has two FKs — one to User, one to the item
# ================================================================


# ================================================================
# models.py  (add this BELOW your existing models)
# ================================================================

from sqlmodel import Field, SQLModel
from typing import Optional

# ADD this class below Track (or whatever the item model is)
class UserTrack(SQLModel, table=True):       # PLUG: rename e.g. UserCourse, UserPost
    id: int | None = Field(default=None, primary_key=True)

    # PLUG: second FK — rename track_id and "track.id" to your item table
    user_id:  int | None = Field(default=None, foreign_key="user.id")
    track_id: int | None = Field(default=None, foreign_key="track.id")  # PLUG

    # PLUG: extra field if the link carries data — remove if not needed
    reaction: str = ""      # e.g. "like" / "dislike"


# ================================================================
# cli.py  (add this inside initialize(), AFTER user + track commits)
# ================================================================

# PLUG: rename UserTrack, user_id, track_id, reaction values
# db.add_all([
#     UserTrack(user_id=1, track_id=t1.id, reaction="like"),
#     UserTrack(user_id=2, track_id=t1.id, reaction="like"),
#     UserTrack(user_id=1, track_id=t2.id, reaction="dislike"),
# ])
# db.commit()


# ================================================================
# app/routers/main.py  (add these routes)
# ================================================================

from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select, func
from app.database import SessionDep
from app.auth import AuthDep
from app.models import Track, UserTrack     # PLUG: your models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# View a track — loads comments AND reaction counts
# PLUG: rename /tracks/{id}, Track, UserTrack, track_id FK, reaction values
@router.get("/tracks/{track_id}", response_class=HTMLResponse)
async def get_track(request: Request, user: AuthDep, db: SessionDep, track_id: int):
    albums         = db.exec(select(Album)).all()
    selected_track = db.get(Track, track_id)                        # PLUG
    selected_album = db.get(Album, selected_track.album_id)
    tracks         = db.exec(select(Track).where(Track.album_id == selected_track.album_id)).all()

    # Count reactions — PLUG: rename UserTrack, track_id, reaction values
    likes    = db.exec(select(func.count(UserTrack.id)).where(
                    UserTrack.track_id == track_id,
                    UserTrack.reaction == "like")).one()
    dislikes = db.exec(select(func.count(UserTrack.id)).where(
                    UserTrack.track_id == track_id,
                    UserTrack.reaction == "dislike")).one()

    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "request": request, "user": user,
            "albums":         albums,
            "selected_album": selected_album,
            "tracks":         tracks,
            "selected_track": selected_track,
            "likes":          likes,        # PLUG: rename if needed
            "dislikes":       dislikes,     # PLUG: rename if needed
        }
    )

# React to a track — creates/updates the link record
# PLUG: rename /tracks/{id}/react, UserTrack, track_id, reaction
@router.post("/tracks/{track_id}/react")
async def react(request: Request, track_id: int, user: AuthDep, db: SessionDep,
                reaction: str = Form(...)):     # PLUG: form field name

    # Remove existing reaction from this user (no double reactions)
    existing = db.exec(
        select(UserTrack).where(               # PLUG
            UserTrack.track_id == track_id,    # PLUG: FK field
            UserTrack.user_id  == user.id
        )
    ).first()
    if existing:
        db.delete(existing)

    # Save new reaction
    db.add(UserTrack(                          # PLUG
        user_id=user.id,
        track_id=track_id,                     # PLUG: FK field
        reaction=reaction                      # PLUG: extra field(s)
    ))
    db.commit()
    return RedirectResponse(url=f"/tracks/{track_id}", status_code=status.HTTP_303_SEE_OTHER)


# ================================================================
# index.html  (add inside Column 3, above the comment section)
# ================================================================

"""
<!-- REACTION COUNTS -->
<!-- PLUG: rename likes, dislikes to match context keys from your route -->
<div style="margin-bottom:10px;">
  <span class="chip green white-text">👍 {{ likes }} Likes</span>
  <span class="chip red   white-text">👎 {{ dislikes }} Dislikes</span>
</div>

<!-- REACTION BUTTONS -->
<!-- PLUG: action="/tracks/{{ selected_track.id }}/react" → your route -->
<!-- PLUG: value="like"/"dislike" → your reaction values              -->
<form action="/tracks/{{ selected_track.id }}/react" method="POST" style="margin-bottom:12px;">
  <button type="submit" name="reaction" value="like"    class="btn btn-small green waves-effect">👍 Like</button>
  <button type="submit" name="reaction" value="dislike" class="btn btn-small red   waves-effect">👎 Dislike</button>
</form>
"""
