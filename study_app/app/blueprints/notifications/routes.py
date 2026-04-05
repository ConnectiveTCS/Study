from flask import render_template, jsonify, redirect, url_for, abort
from flask_login import login_required, current_user

from . import notifications_bp
from app.models.notification import Notification
from app.extensions import db


@notifications_bp.route("/")
@login_required
def list_notifications():
    notes = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
        .all()
    )
    # Mark all as read automatically on page open
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update(
        {"is_read": True}
    )
    db.session.commit()
    return render_template("notifications/list.html", notifications=notes)


@notifications_bp.route("/unread-count")
@login_required
def unread_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({"count": count})


@notifications_bp.route("/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_read(notif_id):
    n = Notification.query.get_or_404(notif_id)
    if n.user_id != current_user.id:
        abort(403)
    n.is_read = True
    db.session.commit()
    return jsonify({"ok": True})


@notifications_bp.route("/mark-all-read", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update(
        {"is_read": True}
    )
    db.session.commit()
    return redirect(url_for("notifications.list_notifications"))
