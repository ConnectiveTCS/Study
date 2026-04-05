from datetime import date, timedelta
from flask import render_template, g
from flask_login import current_user
from . import dashboard_bp
from ...extensions import db
from ...models.gamification import Streak, XPTransaction


@dashboard_bp.route("/")
def index():
    if current_user.is_authenticated:
        uid = current_user.id
        streak = Streak.query.filter_by(user_id=uid).first()

        # Due flashcard count
        from ...models.flashcard import Deck
        decks = Deck.query.filter_by(user_id=uid).all()
        total_due = sum(d.due_count for d in decks)

        # Recent XP activity (last 7 days)
        since = date.today() - timedelta(days=6)
        recent_xp = (
            db.session.query(XPTransaction)
            .filter(XPTransaction.user_id == uid, XPTransaction.created_at >= since)
            .order_by(XPTransaction.created_at.desc())
            .limit(10)
            .all()
        )

        # Upcoming planner events (next 7 days)
        from ...models.planner import StudyEvent
        upcoming = (
            StudyEvent.query
            .filter_by(user_id=uid)
            .filter(StudyEvent.start_dt >= date.today(), StudyEvent.start_dt <= date.today() + timedelta(days=7))
            .order_by(StudyEvent.start_dt)
            .limit(5)
            .all()
        )

        # Active subjects
        from ...models.subject import Subject
        subjects = Subject.query.filter_by(user_id=uid).order_by(Subject.name).all()

        # Subject progress widgets
        from ...models.gamification import SubjectProgress
        subject_progress = {sp.subject_id: sp for sp in SubjectProgress.query.filter_by(user_id=uid).all()}

        return render_template(
            "dashboard/index.html",
            streak=streak,
            total_due=total_due,
            recent_xp=recent_xp,
            upcoming=upcoming,
            subjects=subjects,
            subject_progress=subject_progress,
            total_xp=current_user.total_xp,
        )
    else:
        # Guest / anonymous
        anon_token = g.get("anon_token")
        from ...models.flashcard import Deck
        decks = Deck.query.filter_by(anon_token=anon_token).all() if anon_token else []
        total_due = sum(d.due_count for d in decks)
        return render_template("dashboard/index_guest.html", total_due=total_due)
