from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar = db.Column(db.String(10), default="🎓")  # emoji avatar
    theme_prefs = db.Column(db.JSON, default=lambda: {
        "mode": "dark",
        "primary": "#d4a853",
        "accent": "#f0c97a",
        "background": "#0c0b09",
    })
    onboarding_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    subjects = db.relationship("Subject", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    decks = db.relationship("Deck", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    quizzes = db.relationship("Quiz", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    notes = db.relationship("Note", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    study_events = db.relationship("StudyEvent", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    pomodoro_sessions = db.relationship("PomodoroSession", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    mind_maps = db.relationship("MindMap", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    pdf_files = db.relationship("PDFFile", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    streak = db.relationship("Streak", back_populates="user", uselist=False, cascade="all, delete-orphan")
    xp_transactions = db.relationship("XPTransaction", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    user_badges = db.relationship("UserBadge", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    subject_progress = db.relationship("SubjectProgress", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    group_memberships = db.relationship("GroupMember", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def total_xp(self) -> int:
        return db.session.query(
            db.func.coalesce(db.func.sum(XPTransaction.amount), 0)
        ).filter_by(user_id=self.id).scalar()

    @property
    def unread_notification_count(self) -> int:
        from .notification import Notification
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class AnonymousSession(db.Model):
    __tablename__ = "anonymous_sessions"

    id = db.Column(db.Integer, primary_key=True)
    session_token = db.Column(db.String(36), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))
