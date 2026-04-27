from __future__ import annotations

from dataclasses import dataclass

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.models import CommunicationOptions, db


@dataclass(frozen=True)
class CommunicationOptionValues:
    it_support_email: str
    it_sales_email: str
    telecon_sales_email: str
    internal_notification_list: str


def _defaults() -> CommunicationOptionValues:
    return CommunicationOptionValues(
        it_support_email=current_app.config.get("STELLAR_SUPPORT_EMAIL", ""),
        it_sales_email=current_app.config.get("STELLAR_SALES_EMAIL", ""),
        telecon_sales_email=current_app.config.get("FSI_OPS_EMAIL", ""),
        internal_notification_list=current_app.config.get("HR_CC_EMAILS", ""),
    )


def get_communication_options() -> CommunicationOptionValues:
    defaults = _defaults()
    try:
        options = CommunicationOptions.query.first()
    except SQLAlchemyError:
        return defaults

    if options is None:
        return defaults

    return CommunicationOptionValues(
        it_support_email=options.it_support_email or defaults.it_support_email,
        it_sales_email=options.it_sales_email or defaults.it_sales_email,
        telecon_sales_email=options.telecon_sales_email or defaults.telecon_sales_email,
        internal_notification_list=options.internal_notification_list or defaults.internal_notification_list,
    )


def save_communication_options(values: CommunicationOptionValues) -> tuple[bool, str]:
    try:
        options = CommunicationOptions.query.first()
        if options is None:
            options = CommunicationOptions()
            db.session.add(options)

        options.it_support_email = values.it_support_email
        options.it_sales_email = values.it_sales_email
        options.telecon_sales_email = values.telecon_sales_email
        options.internal_notification_list = values.internal_notification_list
        db.session.commit()
        return True, "Communication options saved."
    except SQLAlchemyError:
        db.session.rollback()
        return (
            False,
            "Communication options table is unavailable. Run `flask db upgrade` and retry.",
        )
