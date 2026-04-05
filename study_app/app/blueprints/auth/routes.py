import json
from flask import render_template, redirect, url_for, flash, request, g, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp
from ...extensions import db, limiter
from ...models.user import User
from ...models.subject import Subject
from ...models.gamification import Streak


# ---------- Register ----------
@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email        = request.form.get("email", "").strip().lower()
        display_name = request.form.get("display_name", "").strip()
        password     = request.form.get("password", "")
        confirm      = request.form.get("confirm_password", "")

        # Validation
        errors = []
        if not email or "@" not in email:
            errors.append("Please enter a valid email address.")
        if len(display_name) < 2:
            errors.append("Display name must be at least 2 characters.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if User.query.filter_by(email=email).first():
            errors.append("An account with that email already exists.")

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("auth/register.html")

        user = User(email=email, display_name=display_name)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # get user.id before migrating anon data

        # Migrate anonymous data to new account
        anon_token = g.get("anon_token")
        if anon_token:
            _migrate_anon_to_user(anon_token, user.id)

        # Create streak record
        streak = Streak(user_id=user.id)
        db.session.add(streak)
        db.session.commit()

        login_user(user)
        flash("Welcome to StudyForce! Let's set up your workspace. 🎉", "success")
        return redirect(url_for("auth.onboarding_step1"))

    return render_template("auth/register.html")


# ---------- Login ----------
@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per hour")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "error")
            return render_template("auth/login.html")

        login_user(user, remember=remember)

        next_page = request.args.get("next")
        # Prevent open redirect — only allow relative paths
        if next_page and next_page.startswith("/") and not next_page.startswith("//"):
            return redirect(next_page)

        if not user.onboarding_complete:
            return redirect(url_for("auth.onboarding_step1"))
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


# ---------- Logout ----------
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out. See you soon! 👋", "info")
    return redirect(url_for("auth.login"))


# ---------- Profile ----------
@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_user.display_name = request.form.get("display_name", current_user.display_name).strip()
        current_user.avatar       = request.form.get("avatar", current_user.avatar)
        new_password = request.form.get("new_password", "")
        if new_password:
            if len(new_password) < 8:
                flash("New password must be at least 8 characters.", "error")
                return redirect(url_for("auth.profile"))
            current_user.set_password(new_password)
        db.session.commit()
        flash("Profile updated!", "success")
        return redirect(url_for("auth.profile"))

    from ...models.gamification import UserBadge
    earned_badges = UserBadge.query.filter_by(user_id=current_user.id).all()
    return render_template("auth/profile.html", earned_badges=earned_badges)


# ---------- Save theme prefs (AJAX) ----------
@auth_bp.route("/theme", methods=["POST"])
def save_theme():
    if not current_user.is_authenticated:
        return jsonify({"ok": True})  # anon users: nothing to persist server-side

    data = request.get_json(silent=True) or {}
    allowed_keys = {"mode", "primary", "accent", "background"}
    prefs = {k: v for k, v in data.items() if k in allowed_keys}
    if prefs:
        current_user.theme_prefs = {**(current_user.theme_prefs or {}), **prefs}
        db.session.commit()
    return jsonify({"ok": True})


# ---------- Onboarding wizard ----------
@auth_bp.route("/onboarding/1", methods=["GET", "POST"])
@login_required
def onboarding_step1():
    """Step 1: Pick subjects + colours."""
    if request.method == "POST":
        names  = request.form.getlist("subject_name")
        colors = request.form.getlist("subject_color")
        icons  = request.form.getlist("subject_icon")

        for i, name in enumerate(names):
            name = name.strip()
            if not name:
                continue
            color = colors[i] if i < len(colors) else "#7c3aed"
            icon  = icons[i]  if i < len(icons)  else "📚"
            db.session.add(Subject(user_id=current_user.id, name=name, color=color, icon=icon))

        db.session.commit()
        return redirect(url_for("auth.onboarding_step2"))

    return render_template("auth/onboarding_step1.html")


@auth_bp.route("/onboarding/2", methods=["GET", "POST"])
@login_required
def onboarding_step2():
    """Step 2: Set daily study goal (stored in theme_prefs for now)."""
    if request.method == "POST":
        goal_minutes = request.form.get("goal_minutes", "60")
        try:
            goal_minutes = max(5, min(int(goal_minutes), 480))
        except ValueError:
            goal_minutes = 60

        prefs = current_user.theme_prefs or {}
        prefs["daily_goal_minutes"] = goal_minutes
        current_user.theme_prefs = prefs
        db.session.commit()
        return redirect(url_for("auth.onboarding_step3"))

    return render_template("auth/onboarding_step2.html")


@auth_bp.route("/onboarding/3", methods=["GET", "POST"])
@login_required
def onboarding_step3():
    """Step 3: Choose theme."""
    if request.method == "POST":
        mode       = request.form.get("mode", "dark")
        primary    = request.form.get("primary", "#d4a853")
        accent     = request.form.get("accent", "#f0c97a")
        background = request.form.get("background", "#0c0b09")

        current_user.theme_prefs = {
            "mode": mode,
            "primary": primary,
            "accent": accent,
            "background": background,
            "daily_goal_minutes": (current_user.theme_prefs or {}).get("daily_goal_minutes", 60),
        }
        current_user.onboarding_complete = True
        db.session.commit()
        flash("You're all set! Happy studying 🎓", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/onboarding_step3.html")


# ---------- Internal helper ----------
def _migrate_anon_to_user(anon_token: str, user_id: int) -> None:
    """Reassign all anonymous-session data to the new user account."""
    from ...models.flashcard import Deck, SM2Review
    from ...models.quiz import Quiz, QuizAttempt
    from ...models.note import Note
    from ...models.planner import StudyEvent
    from ...models.pomodoro import PomodoroSession
    from ...models.mindmap import MindMap
    from ...models.pdf import PDFFile, PDFAnnotation

    models_with_anon = [Subject, Deck, Quiz, Note, StudyEvent, PomodoroSession, MindMap, PDFFile]
    for Model in models_with_anon:
        Model.query.filter_by(anon_token=anon_token).update(
            {"user_id": user_id, "anon_token": None},
            synchronize_session=False,
        )

    # SM2Reviews and attempt answers use anon_token directly
    SM2Review.query.filter_by(anon_token=anon_token).update(
        {"user_id": user_id, "anon_token": None}, synchronize_session=False
    )
    QuizAttempt.query.filter_by(anon_token=anon_token).update(
        {"user_id": user_id, "anon_token": None}, synchronize_session=False
    )
    PDFAnnotation.query.filter_by(anon_token=anon_token).update(
        {"user_id": user_id, "anon_token": None}, synchronize_session=False
    )


# ---------- Forgot Password (stub) ----------
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    sent = False
    if request.method == "POST":
        # In a real deployment wire up Flask-Mail token email here.
        sent = True
    return render_template("auth/forgot_password.html", sent=sent)
