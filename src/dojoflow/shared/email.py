"""Regras de endereço de e-mail usadas em mais de um lugar."""

import re

# Domínio dos alunos fictícios da carga de demonstração (seed_demo)
DEMO_EMAIL_DOMAIN = 'demo.dojoflow.test'
# Domínios reservados (RFC 2606/6761): nunca recebem e-mail de verdade
RESERVED_DOMAIN_SUFFIXES = ('.test', '.example', '.invalid', '.localhost')
# Um endereço só: um @, sem espaço, ";" ou ",", e domínio com ponto
SINGLE_ADDRESS = re.compile(r'[^@\s;,]+@[^@\s;,]+\.[^@\s;,]+')


def is_deliverable_email(address: str | None) -> bool:
    """Dá para enviar: um endereço só e fora dos domínios reservados e de
    demonstração."""
    address = (address or '').strip()
    if not SINGLE_ADDRESS.fullmatch(address):
        return False
    domain = address.rsplit('@', 1)[1].lower()
    return domain != DEMO_EMAIL_DOMAIN and not domain.endswith(
        RESERVED_DOMAIN_SUFFIXES
    )
