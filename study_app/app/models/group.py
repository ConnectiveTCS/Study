import uuid
from datetime import datetime, timezone
from ..extensions import db


class StudyGroup(db.Model):
    __tablename__ = "study_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    invite_code = db.Column(db.String(36), unique=True, nullable=False,
                            default=lambda: str(uuid.uuid4()))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    members = db.relationship("GroupMember", back_populates="group", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def member_count(self) -> int:
        return self.members.count()

    def __repr__(self) -> str:
        return f"<StudyGroup {self.name}>"


class GroupMember(db.Model):
    __tablename__ = "group_members"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("study_groups.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # owner | member
    role = db.Column(db.String(20), nullable=False, default="member")
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    group = db.relationship("StudyGroup", back_populates="members")
    user = db.relationship("User", back_populates="group_memberships")

    def __repr__(self) -> str:
        return f"<GroupMember user={self.user_id} group={self.group_id} role={self.role}>"
