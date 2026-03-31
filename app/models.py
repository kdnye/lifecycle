from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash


db = SQLAlchemy()

USERS_TABLE = "users"
ROLE_MATRIX_TABLE = "role_matrix"
QUESTION_MATRIX_TABLE = "question_matrix"
ACTION_MATRIX_TABLE = "action_matrix"
INTAKE_REQUEST_TABLE = "intake_request"


class User(db.Model):
    """Mapped representation of the central FSI users table."""

    __tablename__ = USERS_TABLE

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    name = db.Column(db.String(120))
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    phone = db.Column(db.String(50))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="EMPLOYEE")
    employee_approved = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)


class RoleMatrix(db.Model):
    __tablename__ = ROLE_MATRIX_TABLE

    id = db.Column(db.Integer, primary_key=True)
    role_profile = db.Column(db.String(64), unique=True, nullable=False)
    m365_plan = db.Column(db.String(64), nullable=False)
    hardware_default = db.Column(db.String(128), nullable=False)
    vpn_policy = db.Column(db.String(64), nullable=False)


class QuestionMatrix(db.Model):
    __tablename__ = QUESTION_MATRIX_TABLE

    id = db.Column(db.Integer, primary_key=True)
    role_profile = db.Column(db.String(64), nullable=False)
    question_key = db.Column(db.String(128), nullable=False)
    prompt = db.Column(db.String(512), nullable=False)
    is_required = db.Column(db.Boolean, default=False, nullable=False)


class ActionMatrix(db.Model):
    __tablename__ = ACTION_MATRIX_TABLE

    id = db.Column(db.Integer, primary_key=True)
    intake_condition = db.Column(db.String(128), nullable=False)
    action_name = db.Column(db.String(128), nullable=False)
    target_system = db.Column(db.String(128), nullable=False)


class IntakeRequest(db.Model):
    __tablename__ = INTAKE_REQUEST_TABLE

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    role_profile = db.Column(db.String(64), nullable=False)
    event_type = db.Column(db.String(32), nullable=False)  # onboarding | offboarding
    manager_email = db.Column(db.String(255), nullable=True)
    driver_needs_laptop = db.Column(db.Boolean, nullable=False, default=False)
    driver_needs_printer = db.Column(db.Boolean, nullable=False, default=False)
    driver_needs_fuel_card = db.Column(db.Boolean, nullable=False, default=False)
    driver_needs_vehicle = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(32), nullable=False, default="draft")
