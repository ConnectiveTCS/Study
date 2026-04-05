from datetime import datetime, timezone
from ..extensions import db


class StudyEvent(db.Model):
    __tablename__ = "study_events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    # study | exam | deadline | assignment
    event_type = db.Column(db.String(20), nullable=False, default="study")
    start_dt = db.Column(db.DateTime, nullable=False)
    end_dt = db.Column(db.DateTime, nullable=True)
    all_day = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, default="")

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anon_token = db.Column(db.String(36), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)

    user = db.relationship("User", back_populates="study_events")
    subject = db.relationship("Subject", back_populates="study_events")

    def to_calendar_dict(self) -> dict:
        """Return dict compatible with FullCalendar event format."""
        color = self.subject.color if self.subject else "#7c3aed"
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start_dt.isoformat(),
            "end": self.end_dt.isoformat() if self.end_dt else None,
            "allDay": self.all_day,
            "color": color,
            "extendedProps": {
                "event_type": self.event_type,
                "notes": self.notes,
                "subject_id": self.subject_id,
            },
        }

    def __repr__(self) -> str:
        return f"<StudyEvent {self.title} {self.event_type}>"
