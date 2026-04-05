from datetime import datetime, date, timezone
from ..extensions import db


class Streak(db.Model):
    __tablename__ = "streaks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    current_streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    last_study_date = db.Column(db.Date, nullable=True)

    user = db.relationship("User", back_populates="streak")

    def record_study_today(self) -> None:
        today = date.today()
        if self.last_study_date == today:
            return  # already recorded today
        from datetime import timedelta
        yesterday = today - timedelta(days=1)
        if self.last_study_date == yesterday:
            self.current_streak += 1
        else:
            self.current_streak = 1
        self.last_study_date = today
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

    def __repr__(self) -> str:
        return f"<Streak user={self.user_id} current={self.current_streak}>"


class XPTransaction(db.Model):
    __tablename__ = "xp_transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="xp_transactions")

    def __repr__(self) -> str:
        return f"<XPTransaction user={self.user_id} +{self.amount} {self.reason}>"


class Badge(db.Model):
    __tablename__ = "badges"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(10), nullable=False)       # emoji
    xp_threshold = db.Column(db.Integer, default=0)
    condition = db.Column(db.String(50), nullable=False)  # e.g. "xp", "streak_7", "first_card"

    user_badges = db.relationship("UserBadge", back_populates="badge", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Badge {self.slug}>"


class UserBadge(db.Model):
    __tablename__ = "user_badges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey("badges.id"), nullable=False)
    earned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="user_badges")
    badge = db.relationship("Badge", back_populates="user_badges")

    def __repr__(self) -> str:
        return f"<UserBadge user={self.user_id} badge={self.badge_id}>"


class SubjectProgress(db.Model):
    __tablename__ = "subject_progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    mastery_score = db.Column(db.Float, default=0.0)   # 0.0 - 100.0
    cards_reviewed = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="subject_progress")
    subject = db.relationship("Subject")

    def __repr__(self) -> str:
        return f"<SubjectProgress user={self.user_id} subject={self.subject_id} mastery={self.mastery_score:.1f}>"
