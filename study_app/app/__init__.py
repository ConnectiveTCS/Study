"""Flask application factory."""
import os
from flask import Flask
from .config import config
from .extensions import db, login_manager, mail, csrf, limiter


def create_app(config_name: str = "default") -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config[config_name])

    # Ensure upload folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialise extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # Register blueprints
    from .blueprints.auth import auth_bp
    from .blueprints.dashboard import dashboard_bp
    from .blueprints.flashcards import flashcards_bp
    from .blueprints.quizzes import quizzes_bp
    from .blueprints.notes import notes_bp
    from .blueprints.planner import planner_bp
    from .blueprints.pomodoro import pomodoro_bp
    from .blueprints.mindmaps import mindmaps_bp
    from .blueprints.pdfs import pdfs_bp
    from .blueprints.groups import groups_bp
    from .blueprints.gamification import gamification_bp
    from .blueprints.notifications import notifications_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(flashcards_bp)
    app.register_blueprint(quizzes_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(planner_bp)
    app.register_blueprint(pomodoro_bp)
    app.register_blueprint(mindmaps_bp)
    app.register_blueprint(pdfs_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(gamification_bp)
    app.register_blueprint(notifications_bp)

    # Serve service worker at root scope (required for full-page caching)
    @app.route("/sw.js")
    def service_worker():
        response = app.send_static_file("sw.js")
        response.headers["Service-Worker-Allowed"] = "/"
        return response

    # Register anonymous session middleware
    from .middleware import init_anon_session
    app.before_request(init_anon_session)

    # Register context processors
    from .context_processors import inject_globals
    app.context_processor(inject_globals)

    # Security headers
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "worker-src 'self' blob:;"
        )
        return response

    # Create all tables
    with app.app_context():
        db.create_all()
        _seed_badges()

    return app


def _seed_badges() -> None:
    """Insert default badges if they don't exist yet."""
    from .models.gamification import Badge
    defaults = [
        {"slug": "first_card", "name": "First Card!", "description": "Created your first flashcard", "icon": "🎴", "xp_threshold": 0, "condition": "first_card"},
        {"slug": "streak_3", "name": "On a Roll", "description": "3-day study streak", "icon": "🔥", "xp_threshold": 0, "condition": "streak_3"},
        {"slug": "streak_7", "name": "Week Warrior", "description": "7-day study streak", "icon": "🗓️", "xp_threshold": 0, "condition": "streak_7"},
        {"slug": "streak_30", "name": "Month Master", "description": "30-day study streak", "icon": "🏆", "xp_threshold": 0, "condition": "streak_30"},
        {"slug": "xp_100", "name": "Century", "description": "Earned 100 XP", "icon": "💯", "xp_threshold": 100, "condition": "xp"},
        {"slug": "xp_500", "name": "Rising Star", "description": "Earned 500 XP", "icon": "⭐", "xp_threshold": 500, "condition": "xp"},
        {"slug": "xp_1000", "name": "Knowledge Seeker", "description": "Earned 1,000 XP", "icon": "🌟", "xp_threshold": 1000, "condition": "xp"},
        {"slug": "first_quiz", "name": "Quiz Taker", "description": "Completed your first quiz", "icon": "📝", "xp_threshold": 0, "condition": "first_quiz"},
        {"slug": "perfect_quiz", "name": "Perfectionist", "description": "Scored 100% on a quiz", "icon": "💎", "xp_threshold": 0, "condition": "perfect_quiz"},
        {"slug": "first_pomodoro", "name": "Focused", "description": "Completed your first Pomodoro session", "icon": "🍅", "xp_threshold": 0, "condition": "first_pomodoro"},
        {"slug": "deck_master", "name": "Deck Master", "description": "All cards in a deck are mastered (interval ≥ 7)", "icon": "🃏", "xp_threshold": 0, "condition": "deck_master"},
    ]
    for data in defaults:
        if not Badge.query.filter_by(slug=data["slug"]).first():
            db.session.add(Badge(**data))
    db.session.commit()
