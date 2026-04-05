from datetime import datetime, timezone
from ..extensions import db


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    # Quill Delta JSON stored as text
    content_json = db.Column(db.Text, default="{}")
    # Plain text extracted from delta for JSON export
    content_plain = db.Column(db.Text, default="")
    is_shared = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anon_token = db.Column(db.String(36), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="notes")
    subject = db.relationship("Subject", back_populates="notes")

    def __repr__(self) -> str:
        return f"<Note {self.title}>"
