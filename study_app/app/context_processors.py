"""Template context processors — inject data available in all templates."""
from datetime import datetime
from flask_login import current_user


def _time_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def inject_globals() -> dict:
    """Inject user, theme prefs, and unread notification count into all templates."""
    theme = {
        "mode": "dark",
        "primary": "#d4a853",
        "accent": "#f0c97a",
        "background": "#0c0b09",
    }
    unread_count = 0

    if current_user.is_authenticated:
        if current_user.theme_prefs:
            theme = current_user.theme_prefs
        unread_count = current_user.unread_notification_count

    return {
        "theme": theme,
        "unread_notification_count": unread_count,
        "time_greeting": _time_greeting(),
    }
