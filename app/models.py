from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()

ROLE_MATRIX_TABLE = "role_matrix"
QUESTION_MATRIX_TABLE = "question_matrix"
ACTION_MATRIX_TABLE = "action_matrix"
INTAKE_REQUEST_TABLE = "intake_request"


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
    employee_name = db.Column(db.String(128), nullable=False)
    role_profile = db.Column(db.String(64), nullable=False)
    event_type = db.Column(db.String(32), nullable=False)  # onboarding | offboarding
    status = db.Column(db.String(32), nullable=False, default="draft")
