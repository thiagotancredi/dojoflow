from dojoflow.services.email_templates import (
    LOGO_URL,
    billing_email,
    password_reset_email,
)

PAY = 'https://katsuflow.com.br/pagar/abc'


ADULT_INTRO = (
    'A mensalidade deste mês já está disponível. '
    'Para pagar, é só tocar no botão:'
)


def _billing(academy='Sparta Kombat', student_first_name=None):
    return billing_email(
        recipient_first_name='Lucas',
        academy=academy,
        master='Kennedy Ribeiro',
        pay_link=PAY,
        student_first_name=student_first_name,
    )


def test_billing_email_copy():
    email = _billing()

    assert email.subject == 'Mensalidade disponível — Sparta Kombat'
    assert 'Olá, Lucas! Tudo bem?' in email.html
    assert 'Olá, Lucas! Tudo bem?' in email.text
    assert PAY in email.text
    assert f'href="{PAY}"' in email.html
    assert 'Kennedy Ribeiro' in email.html
    assert 'Enviado com' in email.html
    assert LOGO_URL in email.html
    assert 'Pagar mensalidade' in email.html
    assert 'Se já pagou, desconsidere. Obrigado!' in email.text
    assert 'R$' not in email.html
    assert 'R$' not in email.text


def test_billing_email_to_student_keeps_adult_text():
    email = _billing()

    assert ADULT_INTRO in email.html
    assert ADULT_INTRO in email.text


def test_billing_email_to_responsible_names_the_student():
    email = _billing(student_first_name='Ana')
    intro = (
        'A mensalidade de Ana deste mês já está disponível. '
        'Para pagar, é só tocar no botão:'
    )

    assert intro in email.html
    assert intro in email.text
    assert ADULT_INTRO not in email.text
    assert email.subject == 'Mensalidade disponível — Sparta Kombat'


def test_billing_email_escapes_student_name():
    email = _billing(student_first_name='<Ana>')

    assert 'A mensalidade de &lt;Ana&gt; deste mês' in email.html
    assert '<Ana>' not in email.html


def test_billing_email_escapes_names():
    email = _billing(academy='A&B <Dojo>')

    assert 'A&amp;B &lt;Dojo&gt;' in email.html
    assert '<Dojo>' not in email.html


def test_password_reset_email_copy():
    link = 'https://katsuflow.com.br/redefinir?c=xyz'
    email = password_reset_email(reset_link=link)

    assert email.subject == 'Criar senha nova — Katsuflow'
    for phrase in (
        'Recebemos um pedido para criar uma senha nova. '
        'Toque no botão (vale por 30 minutos):',
        'Se não foi você, ignore este e-mail: sua senha continua a mesma.',
    ):
        assert phrase in email.html
        assert phrase in email.text
    assert 'Criar senha nova' in email.html
    assert 'Equipe Katsuflow' in email.html
    assert 'Equipe Katsuflow' in email.text
    assert f'href="{link}"' in email.html
    assert link in email.text
