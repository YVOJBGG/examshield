from __future__ import annotations

import logging
from collections.abc import Callable

try:
    from pynput import keyboard
except ImportError:  # pragma: no cover - depends on local client environment
    keyboard = None

logger = logging.getLogger(__name__)

ShortcutCallback = Callable[[str, str], None]


class ShortcutDetectionService:
    def __init__(self, callback: ShortcutCallback) -> None:
        self._callback = callback
        self._listener: keyboard.Listener | None = None if keyboard else None
        self._pressed_keys: set[str] = set()
        self._triggered_signatures: set[str] = set()
        self._running = False

    def start(self) -> bool:
        if keyboard is None:
            logger.warning("Shortcut detection unavailable: pynput is not installed")
            return False
        if self._running:
            return True
        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()
            self._running = True
            return True
        except Exception as exc:  # pragma: no cover - platform dependent
            logger.warning("Shortcut detection could not start: %s", exc)
            self._listener = None
            self._running = False
            return False

    def stop(self) -> None:
        self._running = False
        self._pressed_keys.clear()
        self._triggered_signatures.clear()
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:  # pragma: no cover - platform dependent
                pass
            self._listener = None

    def _on_press(self, key: object) -> None:
        normalized = self._normalize_key(key)
        if normalized is None:
            return
        self._pressed_keys.add(normalized)
        self._detect_shortcuts()

    def _on_release(self, key: object) -> None:
        normalized = self._normalize_key(key)
        if normalized is not None:
            self._pressed_keys.discard(normalized)
        self._triggered_signatures.clear()

    def _detect_shortcuts(self) -> None:
        if self._is_pressed({"ctrl", "shift", "tab"}):
            self._emit_once(
                "ctrl_shift_tab",
                "tab_switch_attempt",
                "Detected Ctrl+Shift+Tab shortcut attempt during exam",
            )
            return
        if self._is_pressed({"ctrl", "tab"}):
            self._emit_once(
                "ctrl_tab",
                "tab_switch_attempt",
                "Detected Ctrl+Tab shortcut attempt during exam",
            )
            return
        if self._is_pressed({"win", "ctrl", "left"}):
            self._emit_once(
                "win_ctrl_left",
                "desktop_switch_attempt",
                "Detected Windows+Ctrl+Left shortcut attempt during exam",
            )
            return
        if self._is_pressed({"win", "ctrl", "right"}):
            self._emit_once(
                "win_ctrl_right",
                "desktop_switch_attempt",
                "Detected Windows+Ctrl+Right shortcut attempt during exam",
            )
            return
        if self._is_pressed({"win", "ctrl", "d"}):
            self._emit_once(
                "win_ctrl_d",
                "desktop_switch_attempt",
                "Detected Windows+Ctrl+D shortcut attempt during exam",
            )
            return
        if self._is_pressed({"win", "ctrl", "f4"}):
            self._emit_once(
                "win_ctrl_f4",
                "desktop_switch_attempt",
                "Detected Windows+Ctrl+F4 shortcut attempt during exam",
            )

    def _emit_once(self, signature: str, violation_type: str, details: str) -> None:
        if signature in self._triggered_signatures:
            return
        self._triggered_signatures.add(signature)
        self._callback(violation_type, details)

    def _is_pressed(self, keys: set[str]) -> bool:
        return keys.issubset(self._pressed_keys)

    @staticmethod
    def _normalize_key(key: object) -> str | None:
        if keyboard is None:
            return None
        special_keys = {
            keyboard.Key.ctrl: "ctrl",
            keyboard.Key.ctrl_l: "ctrl",
            keyboard.Key.ctrl_r: "ctrl",
            keyboard.Key.shift: "shift",
            keyboard.Key.shift_l: "shift",
            keyboard.Key.shift_r: "shift",
            keyboard.Key.tab: "tab",
            keyboard.Key.cmd: "win",
            keyboard.Key.cmd_l: "win",
            keyboard.Key.cmd_r: "win",
            keyboard.Key.left: "left",
            keyboard.Key.right: "right",
            keyboard.Key.f4: "f4",
        }
        if key in special_keys:
            return special_keys[key]

        char = getattr(key, "char", None)
        if not isinstance(char, str) or not char:
            return None
        lowered = char.lower()
        if lowered in {"d"}:
            return lowered
        return None
