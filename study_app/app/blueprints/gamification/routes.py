from flask import render_template
from flask_login import login_required, current_user

from . import gamification_bp
from app.models.user import User
from app.models.gamification import Badge, UserBadge, XPTransaction
from app.extensions import db


@gamification_bp.route("/leaderboard")
@login_required
def leaderboard():
    # Rank users by sum of XP transactions
    xp_sub = (
        db.session.query(
            XPTransaction.user_id,
            db.func.coalesce(db.func.sum(XPTransaction.amount), 0).label("total"),
        )
        .group_by(XPTransaction.user_id)
        .subquery()
    )
    top_users = (
        db.session.query(User, db.func.coalesce(xp_sub.c.total, 0).label("total"))
        .outerjoin(xp_sub, User.id == xp_sub.c.user_id)
        .order_by(db.desc("total"))
        .limit(20)
        .all()
    )

    # Find current user rank
    user_rank = None
    for i, (u, _) in enumerate(top_users, start=1):
        if u.id == current_user.id:
            user_rank = i
            break

    return render_template(
        "gamification/leaderboard.html",
        top_users=top_users,
        user_rank=user_rank,
    )


@gamification_bp.route("/badges")
@login_required
def badges():
    all_badges = Badge.query.order_by(Badge.xp_threshold).all()
    earned_ids = {
        ub.badge_id
        for ub in UserBadge.query.filter_by(user_id=current_user.id).all()
    }
    my_xp = current_user.total_xp

    return render_template(
        "gamification/badges.html",
        all_badges=all_badges,
        earned_ids=earned_ids,
        my_xp=my_xp,
    )
