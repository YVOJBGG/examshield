from app.services.network_client import NetworkClient


class AuthManager:
    def __init__(self, network_client: NetworkClient) -> None:
        self._network_client = network_client
        self._token: str | None = None
        self._username: str | None = None

    @property
    def token(self) -> str | None:
        return self._token

    @property
    def username(self) -> str | None:
        return self._username

    def login(self, username: str, password: str) -> str:
        data = self._network_client.login(username, password)
        token = str(data["access_token"])
        self._token = token
        self._username = username.strip()
        return token

    def logout(self) -> None:
        self._token = None
        self._username = None
        self._network_client.clear_token()
