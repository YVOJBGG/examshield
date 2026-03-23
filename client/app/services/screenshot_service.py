from __future__ import annotations

import io
import logging
import threading
import time

from PIL import ImageGrab

from app.services.network_client import NetworkClient

logger = logging.getLogger(__name__)


class ScreenshotService:
    def __init__(self, network_client: NetworkClient) -> None:
        self._network_client = network_client
        self._attempt_id: str | None = None
        self._active = False
        self._upload_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_status_message = "Screenshot capture idle"

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def last_status_message(self) -> str:
        return self._last_status_message

    def start(self, attempt_id: str) -> None:
        with self._lock:
            self._attempt_id = attempt_id
            self._active = True
            self._last_status_message = "Screenshot capture active"

    def stop(self) -> None:
        with self._lock:
            self._active = False
            self._attempt_id = None
            self._last_status_message = "Screenshot capture stopped"

    def capture_and_upload_async(self) -> None:
        with self._lock:
            if not self._active or not self._attempt_id:
                return
            if self._upload_thread is not None and self._upload_thread.is_alive():
                return
            attempt_id = self._attempt_id
            self._upload_thread = threading.Thread(
                target=self._capture_and_upload,
                args=(attempt_id,),
                daemon=True,
            )
            self._upload_thread.start()

    def _capture_and_upload(self, attempt_id: str) -> None:
        try:
            image = ImageGrab.grab()
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            filename = f"screenshot-{int(time.time())}.png"
            self._network_client.upload_screenshot(
                attempt_id=attempt_id,
                filename=filename,
                content=buffer.getvalue(),
                content_type="image/png",
            )
            self._last_status_message = "Screenshot uploaded"
        except Exception as exc:
            self._last_status_message = "Screenshot upload failed"
            logger.warning("Screenshot capture/upload failed: %s", exc)
