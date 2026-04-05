from flask import render_template, request, jsonify, g
from flask_login import current_user
from datetime import datetime, timezone
from . import pomodoro_bp
from app.extensions import db
from app.models.pomodoro import PomodoroSession
from app.models.subject import Subject


def _owner_kwargs():
    if current_user.is_authenticated:
        return {'user_id': current_user.id}
    return {'anon_token': g.anon_token}


def _recent_sessions():
    if current_user.is_authenticated:
        return PomodoroSession.query.filter_by(completed=True, user_id=current_user.id).order_by(PomodoroSession.started_at.desc()).limit(10).all()
    return PomodoroSession.query.filter_by(completed=True, anon_token=g.anon_token).order_by(PomodoroSession.started_at.desc()).limit(10).all()


@pomodoro_bp.route('/')
def index():
    subjects = []
    if current_user.is_authenticated:
        subjects = Subject.query.filter_by(user_id=current_user.id).all()
    recent = _recent_sessions()
    return render_template('pomodoro/index.html', subjects=subjects, recent=recent)


@pomodoro_bp.route('/log', methods=['POST'])
def log_session():
    """Called by JS when a work interval completes."""
    data = request.get_json(silent=True) or {}
    mode = data.get('mode', 'classic')
    if mode not in ('classic', 'deep', 'micro', 'custom'):
        mode = 'custom'
    work_minutes = max(1, min(int(data.get('work_minutes', 25)), 180))
    break_minutes = max(1, min(int(data.get('break_minutes', 5)), 60))

    session = PomodoroSession(
        mode=mode,
        work_minutes=work_minutes,
        break_minutes=break_minutes,
        completed=True,
        completed_at=datetime.now(timezone.utc),
        subject_id=data.get('subject_id') or None,
        **_owner_kwargs()
    )
    db.session.add(session)

    # Award XP for completed session
    if current_user.is_authenticated:
        from app.models.gamification import XPTransaction
        xp_amount = max(1, work_minutes // 5)
        xp = XPTransaction(user_id=current_user.id, amount=xp_amount, reason='Pomodoro session')
        db.session.add(xp)

    db.session.commit()
    return jsonify({'ok': True})
