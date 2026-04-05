from datetime import datetime, timezone
from ..extensions import db


class PomodoroSession(db.Model):
    __tablename__ = "pomodoro_sessions"

    id = db.Column(db.Integer, primary_key=True)
    # classic | deep | micro | custom
    mode = db.Column(db.String(20), nullable=False, default="classic")
    work_minutes = db.Column(db.Integer, nullable=False, default=25)
    break_minutes = db.Column(db.Integer, nullable=False, default=5)
    completed = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anon_token = db.Column(db.String(36), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)

    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="pomodoro_sessions")

    def __repr__(self) -> str:
        return f"<PomodoroSession mode={self.mode} completed={self.completed}>"
