from datetime import date
from uuid import uuid4

from dojoflow.services.billing import (
    Contact,
    StudentContact,
    choose_email_recipient,
)

TODAY = date(2026, 10, 26)


def _student(
    *,
    birth_date: date | None,
    email: str | None,
    responsibles: tuple[Contact, ...] = (),
) -> StudentContact:
    return StudentContact(
        public_id=uuid4(),
        name='Lucas',
        phone=None,
        birth_date=birth_date,
        responsibles=responsibles,
        pay_token='token',  # noqa: S106
        email=email,
    )


def test_choose_email_recipient_minor_prefers_responsible_then_self():
    minor = date(2015, 1, 1)
    mother = Contact('Maria', None, 'mae@exemplo.com')
    silent = Contact('Pai', None, None)

    with_both = _student(
        birth_date=minor, email='lucas@exemplo.com', responsibles=(mother,)
    )
    only_self = _student(
        birth_date=minor, email='lucas@exemplo.com', responsibles=(silent,)
    )
    nobody = _student(birth_date=minor, email='  ', responsibles=(silent,))

    assert choose_email_recipient(with_both, TODAY) == (mother, True)
    contact, is_responsible = choose_email_recipient(only_self, TODAY)
    assert contact.email == 'lucas@exemplo.com'
    assert is_responsible is False
    assert choose_email_recipient(nobody, TODAY) is None


def test_choose_email_recipient_adult_prefers_self():
    mother = Contact('Maria', None, 'mae@exemplo.com')
    adult = _student(
        birth_date=date(1990, 1, 1),
        email='lucas@exemplo.com',
        responsibles=(mother,),
    )
    no_email = _student(birth_date=None, email=None, responsibles=(mother,))

    contact, is_responsible = choose_email_recipient(adult, TODAY)
    assert contact.name == 'Lucas'
    assert is_responsible is False
    assert choose_email_recipient(no_email, TODAY) == (mother, True)
