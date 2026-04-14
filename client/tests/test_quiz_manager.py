from __future__ import annotations

from pathlib import Path

import pytest

from app.services.quiz_manager import QuizManager


def build_written_exam_payload() -> dict:
    return {
        "id": "exam-1",
        "exam_code": "123456",
        "title": "Distributed Systems",
        "exam_type": "written",
        "time_limit_minutes": 60,
        "instructions": "Answer all questions",
        "questions": [
            {
                "id": "q-1",
                "text": "Explain CAP theorem",
                "points": 5,
                "order_index": 1,
                "options": [],
            },
            {
                "id": "q-2",
                "text": "Explain consistency models",
                "points": 5,
                "order_index": 2,
                "options": [],
            },
        ],
    }


def build_mcq_exam_payload() -> dict:
    return {
        "id": "exam-2",
        "exam_code": "654321",
        "title": "Networking Quiz",
        "exam_type": "mcq",
        "time_limit_minutes": 20,
        "instructions": None,
        "questions": [
            {
                "id": "q-1",
                "text": "Which layer handles routing?",
                "points": 1,
                "order_index": 1,
                "options": [
                    {"id": "o-1", "option_text": "Network", "order_index": 1},
                    {"id": "o-2", "option_text": "Session", "order_index": 2},
                ],
            }
        ],
    }


def test_quiz_manager_written_exam_flow_persists_local_cache(client_data_dir, fake_network_client) -> None:
    fake_network_client.exam_payload = build_written_exam_payload()
    manager = QuizManager(fake_network_client)
    manager.begin_user_session("Student1")

    exam = manager.load_exam("123456")
    attempt_id = manager.start_attempt()
    manager.set_written_answer("q-1", "Draft answer")

    autosave_response = manager.autosave()
    submit_response = manager.submit()

    assert exam.title == "Distributed Systems"
    assert attempt_id == "attempt-1"
    assert autosave_response == [{"ok": True}]
    assert submit_response == {"attempt": {"status": "submitted"}}
    assert manager.has_dirty_cache() is False
    assert not (Path(client_data_dir) / "cache" / "attempt_attempt-1.json").exists()
    assert list((Path(client_data_dir) / "archive").glob("attempt_attempt-1_*.json"))


def test_quiz_manager_restores_cached_answers_when_exam_is_reopened(
    client_data_dir, fake_network_client
) -> None:
    fake_network_client.exam_payload = build_written_exam_payload()
    manager = QuizManager(fake_network_client)
    manager.begin_user_session("student1")
    manager.load_exam("123456")
    manager.set_written_answer("q-1", "Recovered answer")

    fresh_manager = QuizManager(fake_network_client)
    fresh_manager.begin_user_session("student1")
    fresh_manager.load_exam("123456")

    assert fresh_manager.get_written_answer("q-1") == "Recovered answer"
    assert fresh_manager.has_dirty_cache() is True


def test_quiz_manager_marks_cache_dirty_if_autosave_fails(client_data_dir, fake_network_client) -> None:
    fake_network_client.exam_payload = build_written_exam_payload()
    fake_network_client.raise_on_autosave = RuntimeError("offline")
    manager = QuizManager(fake_network_client)
    manager.begin_user_session("student1")
    manager.load_exam("123456")
    manager.start_attempt()
    manager.set_written_answer("q-1", "Offline draft")

    with pytest.raises(RuntimeError, match="offline"):
        manager.autosave()

    assert manager.has_dirty_cache() is True
    cache_file = Path(client_data_dir) / "cache" / "attempt_attempt-1.json"
    assert cache_file.exists()
    assert "Offline draft" in cache_file.read_text(encoding="utf-8")


def test_quiz_manager_normalizes_mcq_cache_without_legacy_text_answers(
    client_data_dir, fake_network_client
) -> None:
    fake_network_client.exam_payload = build_mcq_exam_payload()
    cache_dir = Path(client_data_dir) / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "exam_student1_exam-2.json").write_text(
        """
        {
          "attempt_id": "",
          "exam_id": "exam-2",
          "user_key": "student1",
          "answers": {
            "q-1": {
              "answer_text": "legacy text",
              "selected_option_ids": ["o-2"]
            }
          },
          "last_local_save": "2026-04-14T08:00:00+00:00",
          "dirty": true
        }
        """.strip(),
        encoding="utf-8",
    )

    manager = QuizManager(fake_network_client)
    manager.begin_user_session("student1")
    manager.load_exam("654321")

    assert manager.get_selected_option_ids("q-1") == ["o-2"]
    assert manager.get_written_answer("q-1") == ""
