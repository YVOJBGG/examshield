from app.services.auth_manager import AuthManager


def test_login_stores_token_and_trimmed_username(fake_network_client) -> None:
    manager = AuthManager(fake_network_client)

    token = manager.login(" student1 ", "student123")

    assert token == "token-123"
    assert manager.token == "token-123"
    assert manager.username == "student1"


def test_logout_clears_auth_state_and_delegates_to_network_client(fake_network_client) -> None:
    manager = AuthManager(fake_network_client)
    manager.login("student1", "student123")

    manager.logout()

    assert manager.token is None
    assert manager.username is None
    assert fake_network_client.cleared_token is True
