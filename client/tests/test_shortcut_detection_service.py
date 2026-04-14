from __future__ import annotations

from types import SimpleNamespace

from app.services import shortcut_detection_service as service_module
from app.services.shortcut_detection_service import ShortcutDetectionService


def test_shortcut_detection_emits_once_until_keys_are_released(monkeypatch) -> None:
    events: list[tuple[str, str]] = []
    fake_keyboard = SimpleNamespace(
        Key=SimpleNamespace(
            ctrl="ctrl",
            ctrl_l="ctrl_l",
            ctrl_r="ctrl_r",
            shift="shift",
            shift_l="shift_l",
            shift_r="shift_r",
            tab="tab",
            cmd="cmd",
            cmd_l="cmd_l",
            cmd_r="cmd_r",
            left="left",
            right="right",
            f4="f4",
        ),
        Listener=object,
    )
    monkeypatch.setattr(service_module, "keyboard", fake_keyboard)
    detector = ShortcutDetectionService(lambda violation_type, details: events.append((violation_type, details)))

    detector._on_press(fake_keyboard.Key.ctrl)
    detector._on_press(fake_keyboard.Key.tab)
    detector._on_press(fake_keyboard.Key.tab)
    detector._on_release(fake_keyboard.Key.tab)
    detector._on_press(fake_keyboard.Key.tab)

    assert events == [
        ("tab_switch_attempt", "Detected Ctrl+Tab shortcut attempt during exam"),
        ("tab_switch_attempt", "Detected Ctrl+Tab shortcut attempt during exam"),
    ]
