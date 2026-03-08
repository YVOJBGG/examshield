from app.services.network_client import NetworkClient


class AuthManager:
    def __init__(self, network_client: NetworkClient) -> None:
        self._network_client = network_client
        self._token: str | None = None

    @property
    def token(self) -> str | None:
        return self._token

    def login(self, username: str, password: str) -> str:
        data = self._network_client.login(username, password)
        token = str(data["access_token"])
        self._token = token
        return token
