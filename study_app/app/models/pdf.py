from datetime import datetime, timezone
from ..extensions import db


class PDFFile(db.Model):
    __tablename__ = "pdf_files"

    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)  # uuid-based safe name
    extracted_text = db.Column(db.Text, default="")
    page_count = db.Column(db.Integer, default=0)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anon_token = db.Column(db.String(36), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)

    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="pdf_files")
    subject = db.relationship("Subject", back_populates="pdf_files")
    annotations = db.relationship("PDFAnnotation", back_populates="pdf_file", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<PDFFile {self.original_filename}>"


class PDFAnnotation(db.Model):
    __tablename__ = "pdf_annotations"

    id = db.Column(db.Integer, primary_key=True)
    pdf_id = db.Column(db.Integer, db.ForeignKey("pdf_files.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anon_token = db.Column(db.String(36), nullable=True)
    page_num = db.Column(db.Integer, nullable=False)
    # Stores: {x, y, width, height} as fractions of page dimensions
    rect_json = db.Column(db.JSON, nullable=False)
    color = db.Column(db.String(7), default="#fbbf24")  # highlight color
    note_text = db.Column(db.Text, default="")

    pdf_file = db.relationship("PDFFile", back_populates="annotations")

    def __repr__(self) -> str:
        return f"<PDFAnnotation pdf={self.pdf_id} page={self.page_num}>"
