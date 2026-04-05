from datetime import date, timedelta
from ..extensions import db


class Deck(db.Model):
    __tablename__ = "decks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    is_shared = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anon_token = db.Column(db.String(36), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)

    user = db.relationship("User", back_populates="decks")
    subject = db.relationship("Subject", back_populates="decks")
    cards = db.relationship("Card", back_populates="deck", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def card_count(self) -> int:
        return self.cards.count()

    @property
    def due_count(self) -> int:
        """Cards due for review today: new cards (no review row) + cards whose next_review_date <= today."""
        reviewed_ids = db.session.query(SM2Review.card_id).join(Card).filter(
            Card.deck_id == self.id,
        ).subquery()
        new_cards = self.cards.filter(Card.id.notin_(reviewed_ids)).count()
        due_cards = SM2Review.query.join(Card).filter(
            Card.deck_id == self.id,
            SM2Review.next_review_date <= date.today(),
        ).count()
        return new_cards + due_cards

    def __repr__(self) -> str:
        return f"<Deck {self.title}>"


class Card(db.Model):
    __tablename__ = "cards"

    id = db.Column(db.Integer, primary_key=True)
    front = db.Column(db.Text, nullable=False)
    back = db.Column(db.Text, nullable=False)
    deck_id = db.Column(db.Integer, db.ForeignKey("decks.id"), nullable=False)

    deck = db.relationship("Deck", back_populates="cards")
    reviews = db.relationship("SM2Review", back_populates="card", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Card {self.id} deck={self.deck_id}>"


class SM2Review(db.Model):
    """Stores SM-2 spaced repetition state for one card × one learner."""
    __tablename__ = "sm2_reviews"

    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey("cards.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anon_token = db.Column(db.String(36), nullable=True)

    easiness_factor = db.Column(db.Float, default=2.5)
    interval = db.Column(db.Integer, default=0)   # days
    repetitions = db.Column(db.Integer, default=0)
    next_review_date = db.Column(db.Date, default=date.today)

    card = db.relationship("Card", back_populates="reviews")

    def apply_rating(self, quality: int) -> None:
        """Apply SM-2 algorithm. quality: 0=Again,1=Again,2=Hard,3=Hard,4=Good,5=Easy."""
        ef = self.easiness_factor
        interval = self.interval
        reps = self.repetitions

        if quality < 3:
            reps = 0
            interval = 1
        else:
            if reps == 0:
                interval = 1
            elif reps == 1:
                interval = 6
            else:
                interval = round(interval * ef)
            reps += 1

        ef = max(1.3, ef + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

        self.easiness_factor = ef
        self.interval = interval
        self.repetitions = reps
        self.next_review_date = date.today() + timedelta(days=interval)

    @property
    def is_mastered(self) -> bool:
        return self.interval >= 7

    def __repr__(self) -> str:
        return f"<SM2Review card={self.card_id} next={self.next_review_date}>"
