import json
from flask import render_template, redirect, url_for, flash, request, g, jsonify
from flask_login import current_user
from . import notes_bp
from ...extensions import db


def _owner_filter(Model):
    if current_user.is_authenticated:
        return Model.query.filter_by(user_id=current_user.id)
    anon = g.get("anon_token")
    if anon:
        return Model.query.filter_by(anon_token=anon)
    return Model.query.filter(False)


@notes_bp.route("/")
def list():
    from ...models.note import Note
    from ...models.subject import Subject
    notes_list = _owner_filter(Note).order_by(Note.updated_at.desc()).all()
    subjects   = Subject.query.filter_by(user_id=current_user.id).all() if current_user.is_authenticated else []
    return render_template("notes/list.html", notes=notes_list, subjects=subjects)


@notes_bp.route("/new", methods=["GET", "POST"])
def new_note():
    from ...models.note import Note
    from ...models.subject import Subject

    if request.method == "POST":
        title        = request.form.get("title", "Untitled").strip() or "Untitled"
        content_json = request.form.get("content_json", "{}")
        content_plain = request.form.get("content_plain", "").strip()
        subject_id   = request.form.get("subject_id") or None

        note = Note(title=title, content_json=content_json, content_plain=content_plain, subject_id=subject_id)
        if current_user.is_authenticated:
            note.user_id = current_user.id
        else:
            note.anon_token = g.get("anon_token")
        db.session.add(note)
        db.session.commit()

        if current_user.is_authenticated:
            from ...models.gamification import XPTransaction
            db.session.add(XPTransaction(user_id=current_user.id, amount=5, reason="Created a note"))
            db.session.commit()

        flash("Note saved!", "success")
        return redirect(url_for("notes.edit_note", note_id=note.id))

    subjects = Subject.query.filter_by(user_id=current_user.id).all() if current_user.is_authenticated else []
    return render_template("notes/editor.html", note=None, subjects=subjects)


@notes_bp.route("/<int:note_id>/edit", methods=["GET", "POST"])
def edit_note(note_id):
    from ...models.note import Note
    from ...models.subject import Subject
    note = _owner_filter(Note).filter_by(id=note_id).first_or_404()

    if request.method == "POST":
        note.title         = request.form.get("title", note.title).strip() or note.title
        note.content_json  = request.form.get("content_json", note.content_json)
        note.content_plain = request.form.get("content_plain", "").strip()
        note.subject_id    = request.form.get("subject_id") or None
        db.session.commit()
        return jsonify({"ok": True, "title": note.title})

    subjects = Subject.query.filter_by(user_id=current_user.id).all() if current_user.is_authenticated else []
    return render_template("notes/editor.html", note=note, subjects=subjects)


@notes_bp.route("/<int:note_id>/delete", methods=["POST"])
def delete_note(note_id):
    from ...models.note import Note
    note = _owner_filter(Note).filter_by(id=note_id).first_or_404()
    db.session.delete(note)
    db.session.commit()
    flash("Note deleted.", "info")
    return redirect(url_for("notes.list"))


@notes_bp.route("/export-json")
def export_json():
    """Return all notes as JSON with a pre-written AI system prompt."""
    from ...models.note import Note
    notes_list = _owner_filter(Note).order_by(Note.updated_at.desc()).all()
    notes_data = [
        {
            "title": n.title,
            "subject": n.subject.name if n.subject else None,
            "date": n.updated_at.strftime("%Y-%m-%d"),
            "content": n.content_plain,
        }
        for n in notes_list
    ]
    system_prompt = (
        "You are a knowledgeable study assistant. The following JSON contains the user's notes. "
        "Use them to answer questions, create summaries, generate practice questions, "
        "or help with revision as requested. Be concise and accurate."
    )
    return jsonify({"system_prompt": system_prompt, "notes": notes_data})
