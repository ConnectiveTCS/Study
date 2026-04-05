from ..extensions import db


class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(7), default="#7c3aed")  # hex color
    icon = db.Column(db.String(10), default="📚")  # emoji icon

    # Owner: either a registered user or an anonymous session
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anon_token = db.Column(db.String(36), nullable=True)

    user = db.relationship("User", back_populates="subjects")

    # Relationships to content
    decks = db.relationship("Deck", back_populates="subject", lazy="dynamic")
    quizzes = db.relationship("Quiz", back_populates="subject", lazy="dynamic")
    notes = db.relationship("Note", back_populates="subject", lazy="dynamic")
    study_events = db.relationship("StudyEvent", back_populates="subject", lazy="dynamic")
    pdf_files = db.relationship("PDFFile", back_populates="subject", lazy="dynamic")
    mind_maps = db.relationship("MindMap", back_populates="subject", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Subject {self.name}>"
