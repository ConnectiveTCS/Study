from flask import render_template, request, jsonify, g
from flask_login import current_user
from datetime import datetime
from . import planner_bp
from app.extensions import db
from app.models.planner import StudyEvent
from app.models.subject import Subject


def _owner_filter(query):
    if current_user.is_authenticated:
        return query.filter_by(user_id=current_user.id)
    return query.filter_by(anon_token=g.anon_token)


def _owner_kwargs():
    if current_user.is_authenticated:
        return {'user_id': current_user.id}
    return {'anon_token': g.anon_token}


@planner_bp.route('/')
def index():
    subjects = []
    if current_user.is_authenticated:
        subjects = Subject.query.filter_by(user_id=current_user.id).all()
    return render_template('planner/index.html', subjects=subjects)


@planner_bp.route('/events')
def events_api():
    """Return events as FullCalendar-compatible JSON."""
    start = request.args.get('start')
    end = request.args.get('end')
    q = _owner_filter(StudyEvent.query)
    if start:
        try:
            q = q.filter(StudyEvent.start_dt >= datetime.fromisoformat(start))
        except ValueError:
            pass
    if end:
        try:
            q = q.filter(StudyEvent.start_dt <= datetime.fromisoformat(end))
        except ValueError:
            pass
    events = q.all()
    return jsonify([e.to_calendar_dict() for e in events])


@planner_bp.route('/events', methods=['POST'])
def create_event():
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title or len(title) > 200:
        return jsonify({'ok': False, 'error': 'Invalid title'}), 400

    try:
        start = datetime.fromisoformat(data['start'])
    except (KeyError, ValueError):
        return jsonify({'ok': False, 'error': 'Invalid start time'}), 400

    end_raw = data.get('end')
    end = None
    if end_raw:
        try:
            end = datetime.fromisoformat(end_raw)
        except ValueError:
            pass

    event = StudyEvent(
        title=title,
        notes=(data.get('description') or '')[:512],
        start_dt=start,
        end_dt=end,
        all_day=bool(data.get('allDay', False)),
        event_type=data.get('event_type', 'study') or 'study',
        subject_id=data.get('subject_id') or None,
        **_owner_kwargs()
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({'ok': True, 'event': event.to_calendar_dict()})


@planner_bp.route('/events/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    event = StudyEvent.query.get_or_404(event_id)
    if not _can_modify(event):
        return jsonify({'ok': False, 'error': 'Forbidden'}), 403

    data = request.get_json(silent=True) or {}
    if 'title' in data and data['title']:
        event.title = data['title'][:200]
    if 'description' in data:
        event.notes = (data['description'] or '')[:512]
    if 'start' in data:
        try:
            event.start_dt = datetime.fromisoformat(data['start'])
        except ValueError:
            pass
    if 'end' in data and data['end']:
        try:
            event.end_dt = datetime.fromisoformat(data['end'])
        except ValueError:
            pass
    if 'allDay' in data:
        event.all_day = bool(data['allDay'])
    if 'event_type' in data and data['event_type']:
        event.event_type = data['event_type']
    db.session.commit()
    return jsonify({'ok': True, 'event': event.to_calendar_dict()})


@planner_bp.route('/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    event = StudyEvent.query.get_or_404(event_id)
    if not _can_modify(event):
        return jsonify({'ok': False, 'error': 'Forbidden'}), 403
    db.session.delete(event)
    db.session.commit()
    return jsonify({'ok': True})


def _can_modify(event):
    if current_user.is_authenticated:
        return event.user_id == current_user.id
    return event.anon_token == g.anon_token
