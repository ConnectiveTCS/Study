from datetime import datetime, timezone
from ..extensions import db


class Quiz(db.Model):
    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    is_shared = db.Column(db.Boolean, default=False)
    time_limit_minutes = db.Column(db.Integer, nullable=True)  # None = untimed

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anon_token = db.Column(db.String(36), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)

    user = db.relationship("User", back_populates="quizzes")
    subject = db.relationship("Subject", back_populates="quizzes")
    questions = db.relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan", lazy="dynamic", order_by="QuizQuestion.position")
    attempts = db.relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def question_count(self) -> int:
        return self.questions.count()

    def __repr__(self) -> str:
        return f"<Quiz {self.title}>"


class QuizQuestion(db.Model):
    __tablename__ = "quiz_questions"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    # mcq | true_false | short_answer
    question_type = db.Column(db.String(20), nullable=False, default="mcq")
    options = db.Column(db.JSON, nullable=True)          # list of strings for MCQ
    correct_answer = db.Column(db.Text, nullable=False)  # index str for MCQ, "true"/"false", or text
    explanation = db.Column(db.Text, default="")
    position = db.Column(db.Integer, default=0)

    quiz = db.relationship("Quiz", back_populates="questions")
    attempt_answers = db.relationship("QuizAttemptAnswer", back_populates="question", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<QuizQuestion {self.id} quiz={self.quiz_id}>"


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anon_token = db.Column(db.String(36), nullable=True)
    score = db.Column(db.Float, nullable=True)             # percentage 0-100
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)

    quiz = db.relationship("Quiz", back_populates="attempts")
    answers = db.relationship("QuizAttemptAnswer", back_populates="attempt", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<QuizAttempt {self.id} score={self.score}>"


class QuizAttemptAnswer(db.Model):
    __tablename__ = "quiz_attempt_answers"

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("quiz_questions.id"), nullable=False)
    given_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)

    attempt = db.relationship("QuizAttempt", back_populates="answers")
    question = db.relationship("QuizQuestion", back_populates="attempt_answers")
