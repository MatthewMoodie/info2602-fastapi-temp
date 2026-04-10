# ================================================================
# EXAM CHEAT SHEET: READING THE QUESTION + COMMON ERRORS
# ================================================================


# ================================================================
# PART A: HOW TO READ THE QUESTION
# ================================================================


# ================================================================
# A1. IDENTIFY YOUR TABLES FROM THE FEATURE LIST
# ================================================================
# Read every feature and ask: "what data does this need to store?"
# Each distinct thing that needs storing = a table.
#
# KEYWORD CLUES IN THE QUESTION:
#
# "browse a collection of X"       → X is a PARENT table
#   e.g. "browse a collection of movies"   → Movie model
#
# "select X to view its Y"         → Y is a CHILD table (FK to X)
#   e.g. "select a movie to view its cast" → Cast model with movie_id FK
#
# "view/add/delete comments/reviews/feedback on X"
#                                  → GRANDCHILD table (FK to X)
#   e.g. "comment on a cast member" → Review model with cast_id FK
#
# "like/dislike/react/rate/favourite/enrol in X"
#                                  → MANY-TO-MANY link table
#   e.g. "react to a cast member"  → UserCast with user_id + cast_id
#
# "log/record weight/reps/score for X"
#                                  → extra fields on the link table
#   e.g. "log weight and reps"     → UserExercise with weight + reps fields
#
# EXAMPLE — reading this feature list:
#   "View Movies"          → Movie (parent)
#   "View Movie Cast"      → CastMember with movie_id (child)
#   "Review Cast Member"   → Review with cast_id (grandchild)
#   "React to Cast Member" → UserCast with user_id + cast_id (link table)
#
# RESULT — your models.py needs:
#   User, Movie, CastMember, Review, UserCast


# ================================================================
# A2. IDENTIFY WHICH SCENARIO TO USE
# ================================================================
# Match features to scenarios:
#
# FEATURE IN QUESTION                      USE SCENARIO
# ─────────────────────────────────────────────────────────
# Browse parent / view children            Scenario 1
# Like / dislike / react / rate            Scenario 2 (many-to-many)
# Comment / review / feedback / log        Scenario 3
# Search bar / filter by keyword           Scenario 4
# Fetch from external API URL              Scenario 5
# Any list with "paginate" or "pages"      Pagination scenarios
#
# COMBINING:
# Reactions AND comments → use Scenario 2 + 3
# but MERGE the detail route (see error #4 below)


# ================================================================
# A3. SPOT THE RENAME — what to change per scenario
# ================================================================
# Every scenario uses Album/Track as placeholders.
# When you get the exam, do this mapping FIRST before touching code:
#
# EXAM DOMAIN    ALBUM(parent)→  TRACK(child)→   COMMENT(grandchild)→
# ───────────────────────────────────────────────────────────────────
# Movies         Movie           CastMember      Review
# Fitness        WorkoutPlan     Exercise        Feedback
# Restaurant     Restaurant      MenuItem        Review
# Library        Book            Chapter         Note
# School         Course          Lesson          Comment
#
# Then for EVERY file do a consistent find-replace:
#   Class name:   Album     → Movie
#   FK field:     album_id  → movie_id
#   FK string:    "album.id"→ "movie.id"
#   Route URL:    /albums/  → /movies/
#   Context key:  "albums"  → "movies"
#   Template var: album.title → movie.title


# ================================================================
# A4. SPOT THE EXTRA FIELDS
# ================================================================
# Beyond the basic id + name + FK, look for these keywords:
#
# "image / poster / cover / photo"    → image: str = ""
# "description / bio / summary"       → description: str = ""
# "rating / score / grade"            → rating: float = 0.0
# "weight / reps / duration / sets"   → weight: float = 0.0, reps: int = 0
# "pass/fail / good/bad / status"     → status: str = ""
# "date / timestamp / when"           → from datetime import datetime
#                                        created_at: datetime = Field(default_factory=datetime.utcnow)
#
# EXAMPLE:
# "The user can log weight and reps for a selected exercise"
# → add to your link table:
#   weight: float = 0.0
#   reps:   int   = 0


# ================================================================
# A5. SPOT THE REACTION VALUES
# ================================================================
# The reaction field won't always be "like/dislike".
# Look for the exact words used in the question.
#
# "Like / Dislike"            → value="like"     / value="dislike"
# "Fan / Not a Fan"           → value="fan"      / value="not_a_fan"
# "Feeling Strong/Struggling" → value="strong"   / value="struggling"
# "Pass / Fail"               → value="pass"     / value="fail"
# "Upvote / Downvote"         → value="up"       / value="down"
#
# These values go in TWO places:
# 1. Your route:  if existing: db.delete(existing) before adding new
# 2. Your HTML buttons:
#    <button type="submit" name="reaction" value="fan">Fan</button>
#    <button type="submit" name="reaction" value="not_a_fan">Not a Fan</button>


# ================================================================
# A6. MAP THE UI COLUMNS
# ================================================================
# The question always describes a 3-column layout. Map it like:
#
# "Column 1: List of X with a View button"
#   → shows PARENT model, View links to /app/parents/{id}
#
# "Column 2: List of Y for the selected X"
#   → shows CHILD filtered by parent FK
#   → each item links to /app/children/{id}
#
# "Column 3: Z for selected Y, form to add Z, delete button"
#   → shows GRANDCHILD + add form + delete buttons
#   → add  POSTs to /app/children/{id}/grandchildren
#   → delete POSTs to /app/grandchildren/{id}/delete
#   → reactions also go here if needed


# ================================================================
# PART B: COMMON ERRORS
# ================================================================


# ================================================================
# 1. IMPORTS — most common cause of crashes
# ================================================================

# main.py — update this line every time you add a new model
from app.models import User, Album, Track, Comment, UserTrack   # PLUG: add yours

# main.py — add func when using pagination or counting
from sqlmodel import select, func   # ← func needed for COUNT queries

# models.py — always needs these at the top
from sqlmodel import Field, SQLModel
from typing import Optional
from pydantic import EmailStr
from pwdlib import PasswordHash


# ================================================================
# 2. FOREIGN KEY STRING MUST MATCH THE ACTUAL TABLE NAME
# ================================================================
# SQLModel lowercases the class name to make the table name.
# The FK string must match that exact lowercased name.

# Class name       → table name in FK string
# Album            → "album.id"          ✓
# Track            → "track.id"          ✓
# WorkoutPlan      → "workoutplan.id"    ✓  (no underscore!)
# UserTrack        → "usertrack.id"      ✓
# AnalysisFeedback → "analysisfeedback.id" ✓

# WRONG:
# workout_plan_id: Optional[int] = Field(foreign_key="workout_plan.id")  ✗

# RIGHT:
# workout_plan_id: Optional[int] = Field(foreign_key="workoutplan.id")   ✓


# ================================================================
# 3. ALWAYS COMMIT BEFORE USING .id
# ================================================================
# .id is None until you commit. If you use it before committing
# all your foreign keys will be None and nothing will link up.

# WRONG:
a1 = Album(title="Album One", artist="Artist 1")
t1 = Track(title="Track 1", album_id=a1.id)   # ✗ a1.id is None here
db.add_all([a1, t1])
db.commit()

# RIGHT:
a1 = Album(title="Album One", artist="Artist 1")
db.add(a1)
db.commit()   # ← commit first so a1.id is assigned
t1 = Track(title="Track 1", album_id=a1.id)   # ✓ a1.id is now set
db.add(t1)
db.commit()


# ================================================================
# 4. DUPLICATE ROUTE NAMES WHEN COMBINING SCENARIOS
# ================================================================
# If you combine scenario 2 (reactions) and scenario 3 (comments)
# they BOTH have a GET /app/tracks/{track_id} route.
# FastAPI will only use the FIRST one it finds — the second is ignored.
# You must MERGE them into one single route.

# WRONG — two routes with same URL:
@app.get('/app/tracks/{track_id}')
def track_view(...):
    comments = ...   # from scenario 3

@app.get('/app/tracks/{track_id}')   # ✗ this one is ignored
def track_view2(...):
    likes = ...      # from scenario 2

# RIGHT — one merged route:
@app.get('/app/tracks/{track_id}')
def track_view(...):
    comments = db.exec(select(Comment).where(Comment.track_id == track_id)).all()
    likes    = db.exec(select(func.count(UserTrack.id)).where(
                   UserTrack.track_id == track_id,
                   UserTrack.reaction == "like")).one()
    dislikes = db.exec(select(func.count(UserTrack.id)).where(
                   UserTrack.track_id == track_id,
                   UserTrack.reaction == "dislike")).one()
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={..., "comments": comments, "likes": likes, "dislikes": dislikes}
    )


# ================================================================
# 5. MODEL IMPORT ORDER IN cli.py
# ================================================================
# from app.models import *  imports everything — but the models
# must be defined in the right order in models.py.
# Parent must come BEFORE child in models.py.

# WRONG order in models.py:
class Track(SQLModel, table=True):
    album_id: Optional[int] = Field(foreign_key="album.id")  # ✗ Album not defined yet

class Album(SQLModel, table=True):   # ✗ defined after Track
    ...

# RIGHT order in models.py:
class Album(SQLModel, table=True):   # ✓ parent first
    ...

class Track(SQLModel, table=True):   # ✓ child after
    album_id: Optional[int] = Field(foreign_key="album.id")


# ================================================================
# 6. FORM FIELD name= MUST MATCH Form() PARAM IN ROUTE
# ================================================================
# The name= attribute in your HTML input must exactly match
# the parameter name in your route's Form() declaration.

# WRONG:
# HTML:  <input type="text" name="comment_text">
# Route: text: str = Form()   ✗ name mismatch — will get 422 error

# RIGHT:
# HTML:  <input type="text" name="text">
# Route: text: str = Form()   ✓ names match


# ================================================================
# 7. POST FORMS ALWAYS NEED method="POST"
# ================================================================
# If you forget method="POST" the form defaults to GET
# and your route will return 405 Method Not Allowed.

# WRONG:
# <form action="/app/tracks/1/comments">   ✗ defaults to GET

# RIGHT:
# <form action="/app/tracks/1/comments" method="POST">   ✓


# ================================================================
# 8. REDIRECT AFTER POST — always use 303
# ================================================================
# After any POST (add, delete, react) always redirect.
# Without a redirect, refreshing the page resubmits the form.

# WRONG:
return templates.TemplateResponse(...)   # ✗ after a POST

# RIGHT:
return RedirectResponse(url=f"/app/tracks/{track_id}", status_code=status.HTTP_303_SEE_OTHER)


# ================================================================
# 9. PAGINATION — passing q= with page= in search
# ================================================================
# If search + pagination are combined, always include &q= in
# pagination links or the search term disappears on next page.

# WRONG:
# <a href="/app?page={{ page + 1 }}">Next</a>   ✗ loses search term

# RIGHT:
# <a href="/app?page={{ page + 1 }}&q={{ q or '' }}">Next</a>   ✓


# ================================================================
# 10. PAGINATION — count AFTER applying search filter
# ================================================================
# Count the filtered results, not the total table count.
# Otherwise total_pages will be wrong when searching.

# WRONG:
total = db.exec(select(func.count(Album.id))).one()   # ✗ counts ALL albums

# RIGHT:
statement = select(Album)
if q:
    statement = statement.where(Album.title.ilike(f"%{q}%"))
count_statement = select(func.count()).select_from(statement.subquery())
total = db.exec(count_statement).one()   # ✓ counts only filtered results


# ================================================================
# 11. OWNERSHIP CHECK BEFORE DELETE
# ================================================================
# Always check the item belongs to the logged-in user
# before deleting. Without this anyone can delete anything.

# WRONG:
comment = db.get(Comment, comment_id)
db.delete(comment)   # ✗ no ownership check

# RIGHT:
comment = db.get(Comment, comment_id)
if comment and comment.username == user.username:   # ✓ check first
    db.delete(comment)
    db.commit()


# ================================================================
# 12. JINJA2 VARIABLES — undefined variables crash the template
# ================================================================
# If your template uses {{ selected_track }} but your route
# doesn't pass it in context, you get an UndefinedError.
# Every variable used in the template MUST be in context.

# Always pass ALL variables the template might need, even if None:
context = {
    "albums":         albums,
    "selected_album": selected_album,   # pass even if None
    "tracks":         tracks,           # pass even if []
    "selected_track": selected_track,   # pass even if None
    "comments":       comments,         # pass even if []
    "likes":          likes,            # pass even if 0
    "dislikes":       dislikes,         # pass even if 0
}

# In the template use {% if selected_track %} before accessing it:
# {% if selected_track %}
#   {{ selected_track.title }}   ✓ safe
# {% endif %}


# ================================================================
# 13. MANY-TO-MANY — delete old reaction before adding new one
# ================================================================
# If you don't delete the old reaction first, a user can
# accumulate multiple reactions on the same item.

# WRONG:
db.add(UserTrack(user_id=user.id, track_id=track_id, reaction=reaction))
db.commit()   # ✗ user now has duplicate reactions

# RIGHT:
existing = db.exec(
    select(UserTrack).where(
        UserTrack.user_id  == user.id,
        UserTrack.track_id == track_id
    )
).first()
if existing:
    db.delete(existing)   # ✓ remove old one first
db.add(UserTrack(user_id=user.id, track_id=track_id, reaction=reaction))
db.commit()


# ================================================================
# 14. RUNNING THE APP — commands to remember
# ================================================================

# Setup (first time only):
# python -m venv venv
# venv\Scripts\activate        (Windows)
# venv/bin/activate            (Mac/Linux)
# pip install -e .

# Initialize the database:
# python cli.py initialize

# Run the app:
# fastapi dev --port 9000

# If you change models.py you MUST re-run initialize:
# python cli.py initialize     ← wipes and rebuilds the DB


# ================================================================
# 15. QUICK SANITY CHECKLIST BEFORE SUBMITTING
# ================================================================
# Go through this before you submit:

# models.py
# [ ] All models defined in correct order (parent before child)
# [ ] All foreign key strings match lowercased class names
# [ ] User model is unchanged

# cli.py
# [ ] db.commit() called after each level before using .id
# [ ] All models imported via  from app.models import *
# [ ] Sample data covers all 3 columns (parents, children, grandchildren)

# main.py
# [ ] All models imported at the top
# [ ] func imported from sqlmodel if using COUNT or pagination
# [ ] No duplicate route URLs
# [ ] All POST routes redirect with 303
# [ ] Merged route if combining reactions + comments

# index.html
# [ ] Every {{ variable }} is passed in context from the route
# [ ] All form action= URLs match your route paths
# [ ] All form input name= match Form() param names in routes
# [ ] All forms that POST have method="POST"
# [ ] Pagination links include &q= if search is also present
# [ ] Delete buttons inside {% if comment.username == user.username %}
