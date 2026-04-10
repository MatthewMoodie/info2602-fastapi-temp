# ================================================================
# SCENARIO 3: COMMENTS  (Grandchild — Create + Delete)
# ================================================================
# Use when: users can leave text on an item and delete their own.
# Example: comment on a Track
# Example: review a Product
# Example: reply to a Post
# ================================================================


# ================================================================
# models.py  (add this BELOW your Track/item model)
# ================================================================

from sqlmodel import Field, SQLModel
from typing import Optional

class Comment(SQLModel, table=True):             # PLUG: rename (Review, Reply etc.)
    id:       int | None = Field(default=None, primary_key=True)
    username: str                                # PLUG: or swap for user_id FK if preferred
    text:     str                                # PLUG: rename (body, content, review_text)

    # PLUG: rename track_id and "track.id" to match your parent table
    track_id: int | None = Field(default=None, foreign_key="track.id")


# ================================================================
# cli.py  (add inside initialize(), AFTER track commit)
# ================================================================

# PLUG: rename Comment, track_id, username, text values
# db.add_all([
#     Comment(username="user1", text="Love this track!", track_id=t1.id),
#     Comment(username="user2", text="Great vibes",      track_id=t1.id),
#     Comment(username="user1", text="Nice one",         track_id=t2.id),
#     Comment(username="user3", text="Not bad at all",   track_id=t3.id),
# ])
# db.commit()


# ================================================================
# app/routers/main.py  (add these routes)
# ================================================================

from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from app.database import SessionDep
from app.auth import AuthDep
from app.utilities.flash import flash, get_flashed_messages
from app.models import Track, Comment   # PLUG: your models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
templates.env.globals['get_flashed_messages'] = get_flashed_messages

# View item + its comments
# PLUG: rename /tracks/{id}, Track, Comment, Comment.track_id
# NOTE: if you already have a get_track() route from scenario 2,
#       just ADD the comments query and "comments" to the context — don't make a second route
@router.get("/tracks/{track_id}", response_class=HTMLResponse)
async def get_track(request: Request, user: AuthDep, db: SessionDep, track_id: int):
    albums         = db.exec(select(Album)).all()
    selected_track = db.get(Track, track_id)                         # PLUG
    selected_album = db.get(Album, selected_track.album_id)
    tracks         = db.exec(select(Track).where(Track.album_id == selected_track.album_id)).all()
    comments       = db.exec(
        select(Comment).where(Comment.track_id == track_id)          # PLUG: FK field
    ).all()

    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "request": request, "user": user,
            "albums":         albums,
            "selected_album": selected_album,
            "tracks":         tracks,
            "selected_track": selected_track,
            "comments":       comments,     # PLUG: rename
        }
    )

# Add a comment
# PLUG: rename /tracks/{id}/comments, Comment, track_id, text
@router.post("/tracks/{track_id}/comments")
async def add_comment(request: Request, track_id: int, user: AuthDep, db: SessionDep,
                      text: str = Form(...)):   # PLUG: form field name
    db.add(Comment(                             # PLUG: rename Comment
        username=user.username,                 # auto-fills from logged-in user
        text=text,                              # PLUG: field name
        track_id=track_id                       # PLUG: FK field name
    ))
    db.commit()
    flash(request, "Comment added!", "success")
    return RedirectResponse(url=f"/tracks/{track_id}", status_code=status.HTTP_303_SEE_OTHER)

# Delete a comment
# PLUG: rename /comments/{id}/delete, Comment, track_id
@router.post("/comments/{comment_id}/delete")
async def delete_comment(comment_id: int, user: AuthDep, db: SessionDep):
    comment = db.get(Comment, comment_id)                   # PLUG
    if comment and comment.username == user.username:       # ownership check
        track_id = comment.track_id                         # PLUG: to redirect back
        db.delete(comment)
        db.commit()
        return RedirectResponse(url=f"/tracks/{track_id}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


# ================================================================
# index.html  (this is all of Column 3)
# ================================================================

"""
<!-- COLUMN 3: comments for selected item -->
<!-- PLUG: rename selected_track, comments, comment, all routes and fields -->
<div class="col s4" style="height:100%; overflow-y:auto; padding:10px;">
  <h5>
    {% if selected_track %}
      Comments – {{ selected_track.title }}
    {% else %}
      Select a Track
    {% endif %}
  </h5>

  {% if selected_track %}

    <!-- Paste reaction buttons from Scenario 2 here if needed -->

    <!-- ADD COMMENT FORM -->
    <!-- PLUG: action="/tracks/{{ selected_track.id }}/comments" → your route -->
    <!-- PLUG: name="text" must match Form(...) param name in route            -->
    <div class="card" style="padding:10px; margin-bottom:10px;">
      <form action="/tracks/{{ selected_track.id }}/comments" method="POST">
        <div class="input-field">
          <textarea name="text" class="materialize-textarea"
                    placeholder="Write a comment…" required></textarea>
        </div>
        <button type="submit" class="btn btn-small purple waves-effect">Add</button>
      </form>
    </div>

    <!-- COMMENT LIST -->
    <!-- PLUG: rename comments, comment, field names -->
    <!-- PLUG: delete route /comments/{{ comment.id }}/delete -->
    {% for comment in comments %}
    <div class="card" style="padding:8px; margin-bottom:6px;">
      <div class="row valign-wrapper" style="margin:0;">
        <div class="col s10">
          <b>{{ comment.username }}:</b> {{ comment.text }}
        </div>
        <div class="col s2 right-align">
          {% if comment.username == user.username %}
          <form action="/comments/{{ comment.id }}/delete" method="POST">
            <button type="submit" class="btn-flat">
              <i class="material-icons red-text">delete</i>
            </button>
          </form>
          {% endif %}
        </div>
      </div>
    </div>
    {% else %}
      <p class="grey-text">No comments yet.</p>
    {% endfor %}

  {% else %}
    <p class="grey-text">Select a track to view comments.</p>
  {% endif %}
</div>
"""
