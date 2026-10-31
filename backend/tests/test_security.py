from backend.core.security import get_password_hash, verify_password


def test_verify_password_does_not_print_credentials(capsys):
    password = "senha-segura-para-teste"
    password_hash = get_password_hash(password)

    assert verify_password(password, password_hash) is True
    assert verify_password("senha-incorreta", password_hash) is False

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
