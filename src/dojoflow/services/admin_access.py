"""Quem é o administrador da plataforma."""

from dojoflow.core.settings import settings
from dojoflow.schemas.master_context import MasterContextRead


def is_admin_email(email: str | None) -> bool:
    admin_email = settings.ADMIN_EMAIL.strip().lower()

    return bool(admin_email) and (email or '').strip().lower() == admin_email


def is_admin(context: MasterContextRead) -> bool:
    # Em modo suporte o administrador age como a academia vista: o painel
    # e as ações de conta ficam fechados
    return not context.support_mode and is_admin_email(context.email)
