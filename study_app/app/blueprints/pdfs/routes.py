import os
import uuid
from flask import render_template, request, jsonify, redirect, url_for, current_app, g, abort
from flask_login import current_user
from werkzeug.utils import secure_filename
from . import pdfs_bp
from app.extensions import db
from app.models.pdf import PDFFile, PDFAnnotation
from app.models.subject import Subject

ALLOWED_EXTENSIONS = {'pdf'}
MAX_PDF_SIZE = 20 * 1024 * 1024  # 20 MB


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _upload_dir():
    d = os.path.join(current_app.instance_path, 'uploads', 'pdfs')
    os.makedirs(d, exist_ok=True)
    return d


def _owner_filter(query):
    if current_user.is_authenticated:
        return query.filter_by(user_id=current_user.id)
    return query.filter_by(anon_token=g.anon_token)


def _owner_kwargs():
    if current_user.is_authenticated:
        return {'user_id': current_user.id}
    return {'anon_token': g.anon_token}


def _can_access(obj):
    if current_user.is_authenticated:
        return obj.user_id == current_user.id
    return obj.anon_token == g.anon_token


@pdfs_bp.route('/')
def list_pdfs():
    pdfs = _owner_filter(PDFFile.query).order_by(PDFFile.uploaded_at.desc()).all()
    subjects = []
    if current_user.is_authenticated:
        subjects = Subject.query.filter_by(user_id=current_user.id).all()
    return render_template('pdfs/list.html', pdfs=pdfs, subjects=subjects)


@pdfs_bp.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return redirect(url_for('pdfs.list_pdfs'))
    file = request.files['file']
    if not file or not file.filename or not _allowed_file(file.filename):
        return redirect(url_for('pdfs.list_pdfs'))

    # Check size
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_PDF_SIZE:
        return redirect(url_for('pdfs.list_pdfs'))

    original_name = secure_filename(file.filename)
    stored_name = f"{uuid.uuid4().hex}.pdf"
    save_path = os.path.join(_upload_dir(), stored_name)
    file.save(save_path)

    extracted_text = ''
    page_count = 0
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(save_path)
        page_count = len(doc)
        texts = []
        for page in doc:
            texts.append(page.get_text())
        extracted_text = '\n'.join(texts)[:50000]
        doc.close()
    except Exception:
        pass

    pdf = PDFFile(
        original_filename=original_name,
        stored_filename=stored_name,
        extracted_text=extracted_text,
        page_count=page_count,
        subject_id=request.form.get('subject_id') or None,
        **_owner_kwargs()
    )
    db.session.add(pdf)
    db.session.commit()
    return redirect(url_for('pdfs.viewer', pdf_id=pdf.id))


@pdfs_bp.route('/<int:pdf_id>')
def viewer(pdf_id):
    pdf = PDFFile.query.get_or_404(pdf_id)
    if not _can_access(pdf):
        abort(403)
    annotations = pdf.annotations.all()
    return render_template('pdfs/viewer.html', pdf=pdf, annotations=annotations)


@pdfs_bp.route('/<int:pdf_id>/file')
def serve_file(pdf_id):
    """Stream the PDF file to the browser (for PDF.js)."""
    from flask import send_from_directory
    pdf = PDFFile.query.get_or_404(pdf_id)
    if not _can_access(pdf):
        abort(403)
    return send_from_directory(_upload_dir(), pdf.stored_filename, mimetype='application/pdf')


@pdfs_bp.route('/<int:pdf_id>/annotations', methods=['GET'])
def get_annotations(pdf_id):
    pdf = PDFFile.query.get_or_404(pdf_id)
    if not _can_access(pdf):
        abort(403)
    annotations = pdf.annotations.all()
    return jsonify([{
        'id': a.id, 'page_num': a.page_num, 'rect': a.rect_json,
        'color': a.color, 'note_text': a.note_text
    } for a in annotations])


@pdfs_bp.route('/<int:pdf_id>/annotations', methods=['POST'])
def add_annotation(pdf_id):
    pdf = PDFFile.query.get_or_404(pdf_id)
    if not _can_access(pdf):
        return jsonify({'ok': False, 'error': 'Forbidden'}), 403
    data = request.get_json(silent=True) or {}
    page_num = int(data.get('page_num', 1))
    rect = data.get('rect')
    if not rect or not isinstance(rect, dict):
        return jsonify({'ok': False, 'error': 'rect required'}), 400
    ann = PDFAnnotation(
        pdf_id=pdf_id,
        page_num=page_num,
        rect_json=rect,
        color=data.get('color', '#fbbf24') or '#fbbf24',
        note_text=(data.get('note_text') or '')[:2000],
        **_owner_kwargs()
    )
    db.session.add(ann)
    db.session.commit()
    return jsonify({'ok': True, 'id': ann.id})


@pdfs_bp.route('/annotations/<int:ann_id>', methods=['PUT'])
def update_annotation(ann_id):
    ann = PDFAnnotation.query.get_or_404(ann_id)
    if not _can_access(ann):
        return jsonify({'ok': False, 'error': 'Forbidden'}), 403
    data = request.get_json(silent=True) or {}
    if 'note_text' in data:
        ann.note_text = (data['note_text'] or '')[:2000]
    if 'color' in data and data['color']:
        ann.color = data['color']
    db.session.commit()
    return jsonify({'ok': True})


@pdfs_bp.route('/annotations/<int:ann_id>', methods=['DELETE'])
def delete_annotation(ann_id):
    ann = PDFAnnotation.query.get_or_404(ann_id)
    if not _can_access(ann):
        return jsonify({'ok': False, 'error': 'Forbidden'}), 403
    db.session.delete(ann)
    db.session.commit()
    return jsonify({'ok': True})


@pdfs_bp.route('/<int:pdf_id>/delete', methods=['POST'])
def delete_pdf(pdf_id):
    pdf = PDFFile.query.get_or_404(pdf_id)
    if not _can_access(pdf):
        abort(403)
    # Remove file
    try:
        os.remove(os.path.join(_upload_dir(), pdf.stored_filename))
    except OSError:
        pass
    db.session.delete(pdf)
    db.session.commit()
    return redirect(url_for('pdfs.list_pdfs'))
