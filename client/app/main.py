import sys

from PyQt6.QtWidgets import QApplication

from app.config import DEFAULT_API_BASE_URL
from app.services.auth_manager import AuthManager
from app.services.network_client import NetworkClient
from app.services.quiz_manager import QuizManager
from app.ui.login_window import LoginWindow


def main() -> int:
    app = QApplication(sys.argv)

    network_client = NetworkClient(DEFAULT_API_BASE_URL)
    auth_manager = AuthManager(network_client)
    quiz_manager = QuizManager(network_client)

    login_window = LoginWindow(auth_manager=auth_manager, quiz_manager=quiz_manager)
    login_window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
