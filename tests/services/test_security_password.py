from dojoflow.services.security import generate_password

PASSWORD_LENGTH = 12


def test_generate_password_shape() -> None:
    password = generate_password()

    assert len(password) == PASSWORD_LENGTH
    assert not set(password) & set('0O1lI')


def test_generate_password_is_random() -> None:
    assert generate_password() != generate_password()
