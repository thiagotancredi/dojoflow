from dataclasses import dataclass
from html import escape

from dojoflow.core.settings import settings

LOGO_URL = f'{settings.WEB_APP_URL}/email/katsuflow-logo.png'


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


def _paragraph(content: str, bottom: int) -> str:
    return (
        f'<p style="margin:0 0 {bottom}px;font-size:15px;line-height:1.5;'
        f'color:#2b2a27">{content}</p>'
    )


def _button(label: str, link: str) -> str:
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" '
        'width="100%" style="margin:0 0 22px"><tr>'
        '<td align="center" bgcolor="#4f6b3a" style="background:#4f6b3a;'
        'border-radius:10px">'
        f'<a href="{escape(link, quote=True)}" style="display:block;'
        'padding:14px 20px;font-family:Arial,Helvetica,sans-serif;'
        'font-size:16px;font-weight:bold;color:#ffffff;'
        f'text-decoration:none">{escape(label)}</a>'
        '</td></tr></table>'
    )


def _layout(*, title: str, body: str, signature: str) -> str:
    """Monta o layout L1: cartão branco e "Enviado com" + logo embaixo."""
    return (
        '<!DOCTYPE html><html lang="pt-BR"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{escape(title)}</title></head>'
        '<body style="margin:0;padding:0;background:#f4f3ef">'
        '<table role="presentation" cellpadding="0" cellspacing="0" '
        'width="100%" bgcolor="#f4f3ef" style="background:#f4f3ef">'
        '<tr><td align="center" style="padding:18px 14px;'
        'font-family:Arial,Helvetica,sans-serif">'
        '<table role="presentation" cellpadding="0" cellspacing="0" '
        'width="100%" style="max-width:480px">'
        '<tr><td bgcolor="#ffffff" style="background:#ffffff;'
        'border:1px solid #e2dfd8;border-radius:16px;padding:26px 24px;'
        f'font-family:Arial,Helvetica,sans-serif">{body}{signature}'
        '</td></tr>'
        '<tr><td align="center" style="padding-top:16px;'
        'font-family:Arial,Helvetica,sans-serif">'
        '<div style="font-size:11px;color:#8a877f;margin-bottom:6px">'
        'Enviado com</div>'
        f'<img src="{escape(LOGO_URL, quote=True)}" alt="Katsuflow" '
        'height="38" style="height:38px;width:auto;border:0">'
        '</td></tr></table></td></tr></table></body></html>'
    )


def _signature(name: str, line: str | None = None) -> str:
    second = (
        f'<br><span style="color:#8a877f">{escape(line)}</span>'
        if line
        else ''
    )
    return (
        '<p style="margin:0;font-size:15px;line-height:1.5;color:#2b2a27">'
        f'<b>{escape(name)}</b>{second}</p>'
    )


def billing_email(
    *,
    recipient_first_name: str,
    academy: str,
    master: str,
    pay_link: str,
) -> RenderedEmail:
    greeting = f'Olá, {recipient_first_name}! Tudo bem?'
    intro = (
        'A mensalidade deste mês já está disponível. '
        'Para pagar, é só tocar no botão:'
    )
    outro = 'Se já pagou, desconsidere. Obrigado!'
    body = (
        _paragraph(escape(greeting), 14)
        + _paragraph(escape(intro), 20)
        + _button('Pagar mensalidade', pay_link)
        + _paragraph(escape(outro), 18)
    )
    subject = f'Mensalidade disponível — {academy}'
    text = (
        f'{greeting}\n\n{intro}\n{pay_link}\n\n{outro}\n\n{master}\n{academy}\n'
    )
    return RenderedEmail(
        subject=subject,
        html=_layout(
            title=subject,
            body=body,
            signature=_signature(master, academy),
        ),
        text=text,
    )


def password_reset_email(*, reset_link: str) -> RenderedEmail:
    intro = (
        'Recebemos um pedido para criar uma senha nova. '
        'Toque no botão (vale por 30 minutos):'
    )
    outro = 'Se não foi você, ignore este e-mail: sua senha continua a mesma.'
    body = (
        _paragraph(escape(intro), 20)
        + _button('Criar senha nova', reset_link)
        + _paragraph(escape(outro), 18)
    )
    subject = 'Criar senha nova — Katsuflow'
    text = f'{intro}\n{reset_link}\n\n{outro}\n\nEquipe Katsuflow\n'
    return RenderedEmail(
        subject=subject,
        html=_layout(
            title=subject,
            body=body,
            signature=_signature('Equipe Katsuflow'),
        ),
        text=text,
    )
