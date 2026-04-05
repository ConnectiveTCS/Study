import json
from flask import render_template, redirect, url_for, flash, request, g, jsonify
from flask_login import current_user
from . import quizzes_bp
from ...extensions import db


def _owner_filter(Model):
    if current_user.is_authenticated:
        return Model.query.filter_by(user_id=current_user.id)
    anon = g.get("anon_token")
    if anon:
        return Model.query.filter_by(anon_token=anon)
    return Model.query.filter(False)


# ── Quiz list ──────────────────────────────────────────────────────────────

@quizzes_bp.route("/")
def list():
    from ...models.quiz import Quiz
    from ...models.subject import Subject
    quizzes_list = _owner_filter(Quiz).order_by(Quiz.id.desc()).all()
    subjects     = Subject.query.filter_by(user_id=current_user.id).all() if current_user.is_authenticated else []
    return render_template("quizzes/list.html", quizzes=quizzes_list, subjects=subjects)


# ── Create quiz ────────────────────────────────────────────────────────────

@quizzes_bp.route("/new", methods=["GET", "POST"])
def new_quiz():
    from ...models.quiz import Quiz, QuizQuestion
    from ...models.subject import Subject

    if request.method == "POST":
        title       = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        subject_id  = request.form.get("subject_id") or None
        time_limit  = request.form.get("time_limit") or None
        is_public   = request.form.get("is_public") == "on"

        if not title:
            flash("Quiz title is required.", "error")
            subjects = Subject.query.filter_by(user_id=current_user.id).all() if current_user.is_authenticated else []
            return render_template("quizzes/new_quiz.html", subjects=subjects)

        quiz = Quiz(title=title, description=description, subject_id=subject_id,
                    time_limit_minutes=int(time_limit) if time_limit else None,
                    is_shared=is_public)
        if current_user.is_authenticated:
            quiz.user_id = current_user.id
        else:
            quiz.anon_token = g.get("anon_token")
        db.session.add(quiz)
        db.session.flush()

        # Parse questions from form
        qtype_list   = request.form.getlist("q_type[]")
        qtext_list   = request.form.getlist("q_text[]")
        qcorrect_list = request.form.getlist("q_correct[]")

        for i, qtext in enumerate(qtext_list):
            qtext = qtext.strip()
            if not qtext:
                continue
            qtype   = qtype_list[i] if i < len(qtype_list) else "mcq"
            correct = qcorrect_list[i] if i < len(qcorrect_list) else ""
            options = []
            if qtype == "mcq":
                opts = request.form.getlist(f"q_opts_{i}[]")
                options = [o.strip() for o in opts if o.strip()]

            db.session.add(QuizQuestion(
                quiz_id=quiz.id, question_type=qtype, question_text=qtext,
                options=options, correct_answer=correct, position=i,
            ))

        db.session.commit()
        flash(f'Quiz "{title}" created!', "success")
        return redirect(url_for("quizzes.quiz_detail", quiz_id=quiz.id))

    subjects = Subject.query.filter_by(user_id=current_user.id).all() if current_user.is_authenticated else []
    return render_template("quizzes/new_quiz.html", subjects=subjects)


# ── Quiz detail ────────────────────────────────────────────────────────────

@quizzes_bp.route("/<int:quiz_id>")
def quiz_detail(quiz_id):
    from ...models.quiz import Quiz, QuizAttempt
    quiz     = _owner_filter(Quiz).filter_by(id=quiz_id).first_or_404()
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz.id).order_by(QuizAttempt.started_at.desc()).limit(10).all()
    return render_template("quizzes/quiz_detail.html", quiz=quiz, attempts=attempts)


# ── Take quiz ──────────────────────────────────────────────────────────────

@quizzes_bp.route("/<int:quiz_id>/take")
def take_quiz(quiz_id):
    from ...models.quiz import Quiz
    quiz = _owner_filter(Quiz).filter_by(id=quiz_id).first_or_404()
    questions_json = json.dumps([{
        "id": q.id, "type": q.question_type, "text": q.question_text,
        "options": q.options or [],
    } for q in sorted(quiz.questions, key=lambda q: q.position)])
    return render_template("quizzes/take_quiz.html", quiz=quiz, questions_json=questions_json)


# ── Submit quiz ────────────────────────────────────────────────────────────

@quizzes_bp.route("/<int:quiz_id>/submit", methods=["POST"])
def submit_quiz(quiz_id):
    from ...models.quiz import Quiz, QuizAttempt, QuizAttemptAnswer
    quiz = _owner_filter(Quiz).filter_by(id=quiz_id).first_or_404()

    data       = request.get_json(silent=True) or {}
    answers    = data.get("answers", {})   # {question_id: user_answer}
    time_taken = data.get("time_taken")

    attempt = QuizAttempt(quiz_id=quiz.id)
    if current_user.is_authenticated:
        attempt.user_id = current_user.id
    else:
        attempt.anon_token = g.get("anon_token")
    db.session.add(attempt)
    db.session.flush()

    correct = 0
    total   = len(quiz.questions)
    attempt_answers = []

    for q in quiz.questions:
        user_ans = str(answers.get(str(q.id), "")).strip().lower()
        is_cor   = user_ans == str(q.correct_answer).strip().lower()
        if is_cor:
            correct += 1
        attempt_answers.append(QuizAttemptAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            given_answer=user_ans,
            is_correct=is_cor,
        ))

    db.session.bulk_save_objects(attempt_answers)
    attempt.score = (correct / total * 100) if total else 0
    db.session.commit()

    if current_user.is_authenticated:
        xp = max(1, int(attempt.score / 10))
        from ...models.gamification import XPTransaction, Streak
        db.session.add(XPTransaction(user_id=current_user.id, amount=xp, reason=f"Completed quiz: {quiz.title}"))
        streak = Streak.query.filter_by(user_id=current_user.id).first()
        if streak:
            streak.record_study_today()
        db.session.commit()

    return jsonify({"ok": True, "score": attempt.score, "correct": correct, "total": total, "attempt_id": attempt.id})


# ── Results ────────────────────────────────────────────────────────────────

@quizzes_bp.route("/attempts/<int:attempt_id>")
def attempt_results(attempt_id):
    from ...models.quiz import QuizAttempt
    if current_user.is_authenticated:
        attempt = QuizAttempt.query.filter_by(id=attempt_id, user_id=current_user.id).first_or_404()
    else:
        anon = g.get("anon_token")
        attempt = QuizAttempt.query.filter_by(id=attempt_id, anon_token=anon).first_or_404()
    return render_template("quizzes/results.html", attempt=attempt)


# ── Delete quiz ────────────────────────────────────────────────────────────

@quizzes_bp.route("/<int:quiz_id>/delete", methods=["POST"])
def delete_quiz(quiz_id):
    from ...models.quiz import Quiz
    quiz = _owner_filter(Quiz).filter_by(id=quiz_id).first_or_404()
    db.session.delete(quiz)
    db.session.commit()
    flash("Quiz deleted.", "info")
    return redirect(url_for("quizzes.list"))
