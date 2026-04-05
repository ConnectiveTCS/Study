from datetime import datetime, timezone
from ..extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # badge_unlock | group_invite | study_reminder | quiz_graded | info
    notification_type = db.Column(db.String(30), nullable=False, default="info")
    message = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(255), nullable=True)   # optional deep link
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification user={self.user_id} type={self.notification_type} read={self.is_read}>"
