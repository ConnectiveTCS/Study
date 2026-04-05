import json
from datetime import date
from flask import render_template, redirect, url_for, flash, request, g, jsonify, abort
from flask_login import current_user
from . import flashcards_bp
from ...extensions import db


def _owner_filter(Model):
    """Return a query filtered to the current user or anon token."""
    if current_user.is_authenticated:
        return Model.query.filter_by(user_id=current_user.id)
    anon = g.get("anon_token")
    if anon:
        return Model.query.filter_by(anon_token=anon)
    return Model.query.filter(False)


def _get_deck_or_404(deck_id):
    from ...models.flashcard import Deck
    return _owner_filter(Deck).filter_by(id=deck_id).first_or_404()


# ── Deck list ──────────────────────────────────────────────────────────────

@flashcards_bp.route("/")
def decks():
    from ...models.flashcard import Deck
    from ...models.subject import Subject
    decks_list = _owner_filter(Deck).order_by(Deck.id.desc()).all()
    subjects    = []
    if current_user.is_authenticated:
        subjects = Subject.query.filter_by(user_id=current_user.id).order_by(Subject.name).all()
    return render_template("flashcards/decks.html", decks=decks_list, subjects=subjects)


# ── Create deck ────────────────────────────────────────────────────────────

@flashcards_bp.route("/new", methods=["GET", "POST"])
def new_deck():
    from ...models.flashcard import Deck
    from ...models.subject import Subject

    if request.method == "POST":
        title       = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        subject_id  = request.form.get("subject_id") or None
        is_public   = request.form.get("is_public") == "on"

        if not title:
            flash("Deck title is required.", "error")
        else:
            deck = Deck(
                title=title,
                description=description,
                subject_id=subject_id,
                is_shared=is_public,
            )
            if current_user.is_authenticated:
                deck.user_id = current_user.id
            else:
                deck.anon_token = g.get("anon_token")
            db.session.add(deck)
            db.session.commit()
            flash(f'Deck "{title}" created!', "success")
            return redirect(url_for("flashcards.deck_detail", deck_id=deck.id))

    subjects = Subject.query.filter_by(user_id=current_user.id).all() if current_user.is_authenticated else []
    return render_template("flashcards/new_deck.html", subjects=subjects)


# ── Deck detail ────────────────────────────────────────────────────────────

@flashcards_bp.route("/<int:deck_id>")
def deck_detail(deck_id):
    from ...models.flashcard import Deck, Card
    deck  = _get_deck_or_404(deck_id)
    cards = Card.query.filter_by(deck_id=deck.id).order_by(Card.id.desc()).all()
    return render_template("flashcards/deck_detail.html", deck=deck, cards=cards)


# ── Add card ───────────────────────────────────────────────────────────────

@flashcards_bp.route("/<int:deck_id>/cards/new", methods=["POST"])
def add_card(deck_id):
    from ...models.flashcard import Deck, Card
    deck  = _get_deck_or_404(deck_id)
    front = request.form.get("front", "").strip()
    back  = request.form.get("back", "").strip()

    if not front or not back:
        flash("Both front and back are required.", "error")
    else:
        card = Card(deck_id=deck.id, front=front, back=back)
        db.session.add(card)
        db.session.commit()
        flash("Card added!", "success")

        # Award XP
        if current_user.is_authenticated:
            _award_xp(current_user, 2, "Added a flashcard")

    return redirect(url_for("flashcards.deck_detail", deck_id=deck.id))


# ── Edit card ──────────────────────────────────────────────────────────────

@flashcards_bp.route("/<int:deck_id>/cards/<int:card_id>/edit", methods=["POST"])
def edit_card(deck_id, card_id):
    from ...models.flashcard import Card
    _get_deck_or_404(deck_id)  # ownership check
    card = Card.query.filter_by(id=card_id, deck_id=deck_id).first_or_404()
    card.front = request.form.get("front", card.front).strip()
    card.back  = request.form.get("back", card.back).strip()
    db.session.commit()
    flash("Card updated!", "success")
    return redirect(url_for("flashcards.deck_detail", deck_id=deck_id))


# ── Delete card ────────────────────────────────────────────────────────────

@flashcards_bp.route("/<int:deck_id>/cards/<int:card_id>/delete", methods=["POST"])
def delete_card(deck_id, card_id):
    from ...models.flashcard import Card
    _get_deck_or_404(deck_id)
    card = Card.query.filter_by(id=card_id, deck_id=deck_id).first_or_404()
    db.session.delete(card)
    db.session.commit()
    flash("Card deleted.", "info")
    return redirect(url_for("flashcards.deck_detail", deck_id=deck_id))


# ── Delete deck ────────────────────────────────────────────────────────────

@flashcards_bp.route("/<int:deck_id>/delete", methods=["POST"])
def delete_deck(deck_id):
    deck = _get_deck_or_404(deck_id)
    db.session.delete(deck)
    db.session.commit()
    flash("Deck deleted.", "info")
    return redirect(url_for("flashcards.decks"))


# ── Study mode (GET: fetch due cards) ─────────────────────────────────────

@flashcards_bp.route("/<int:deck_id>/study")
def study(deck_id):
    from ...models.flashcard import Deck, Card, SM2Review
    deck = _get_deck_or_404(deck_id)

    # Get all cards with their review state
    cards_data = []
    for card in Card.query.filter_by(deck_id=deck.id).all():
        review = SM2Review.query.filter_by(card_id=card.id).first()
        if review is None or review.next_review_date <= date.today():
            cards_data.append({
                "id": card.id,
                "front": card.front,
                "back": card.back,
                "interval": review.interval if review else 0,
                "ease_factor": review.easiness_factor if review else 2.5,
            })

    return render_template("flashcards/study.html", deck=deck, cards_json=json.dumps(cards_data))


# ── Study all cards (ignore SRS schedule) ─────────────────────────────────

@flashcards_bp.route("/<int:deck_id>/study-all")
def study_all(deck_id):
    from ...models.flashcard import Deck, Card, SM2Review
    deck = _get_deck_or_404(deck_id)
    cards_data = []
    for card in Card.query.filter_by(deck_id=deck.id).all():
        review = SM2Review.query.filter_by(card_id=card.id).first()
        cards_data.append({
            "id": card.id,
            "front": card.front,
            "back": card.back,
            "interval": review.interval if review else 0,
            "ease_factor": review.easiness_factor if review else 2.5,
        })
    return render_template("flashcards/study.html", deck=deck, cards_json=json.dumps(cards_data))


# ── Study-next (entry point from dashboard) ───────────────────────────────

@flashcards_bp.route("/study-next")
def study_next():
    from ...models.flashcard import Deck
    decks_list = _owner_filter(Deck).all()
    for deck in decks_list:
        if deck.due_count > 0:
            return redirect(url_for("flashcards.study", deck_id=deck.id))
    flash("No cards due right now — come back later!", "info")
    return redirect(url_for("flashcards.decks"))


# ── Submit SM-2 rating (AJAX) ─────────────────────────────────────────────

@flashcards_bp.route("/rate", methods=["POST"])
def rate_card():
    from ...models.flashcard import Card, SM2Review
    data    = request.get_json(silent=True) or {}
    card_id = data.get("card_id")
    quality = data.get("quality")  # 0=Again 2=Hard 4=Good 5=Easy

    if card_id is None or quality is None:
        return jsonify({"error": "Missing params"}), 400

    quality = max(0, min(5, int(quality)))
    card    = Card.query.get_or_404(card_id)

    # Ownership check
    from ...models.flashcard import Deck
    deck = _owner_filter(Deck).filter_by(id=card.deck_id).first_or_404()

    review = SM2Review.query.filter_by(card_id=card.id).first()
    if review is None:
        review = SM2Review(card_id=card.id)
        if current_user.is_authenticated:
            review.user_id = current_user.id
        else:
            review.anon_token = g.get("anon_token")
        db.session.add(review)

    review.apply_rating(quality)
    db.session.commit()

    # XP & streak for registered users
    if current_user.is_authenticated and quality >= 3:
        _award_xp(current_user, 1, "Flashcard review")
        _update_streak(current_user.id)

    return jsonify({"ok": True, "next_review": review.next_review_date.isoformat()})


# ── Share deck (toggle public) ────────────────────────────────────────────

@flashcards_bp.route("/<int:deck_id>/toggle-public", methods=["POST"])
def toggle_public(deck_id):
    deck = _get_deck_or_404(deck_id)
    deck.is_shared = not deck.is_shared
    db.session.commit()
    status = "public" if deck.is_shared else "private"
    flash(f"Deck is now {status}.", "success")
    return redirect(url_for("flashcards.deck_detail", deck_id=deck_id))


# ── Shared public deck (view only) ────────────────────────────────────────

@flashcards_bp.route("/public/<int:deck_id>")
def public_deck(deck_id):
    from ...models.flashcard import Deck, Card
    deck = Deck.query.filter_by(id=deck_id, is_public=True).first_or_404()
    cards = Card.query.filter_by(deck_id=deck.id).all()
    return render_template("flashcards/deck_detail.html", deck=deck, cards=cards, readonly=True)


# ── Helpers ────────────────────────────────────────────────────────────────

def _award_xp(user, amount: int, reason: str) -> None:
    from ...models.gamification import XPTransaction
    tx = XPTransaction(user_id=user.id, amount=amount, reason=reason)
    db.session.add(tx)


def _update_streak(user_id: int) -> None:
    from ...models.gamification import Streak
    streak = Streak.query.filter_by(user_id=user_id).first()
    if streak:
        streak.record_study_today()
