import json

from app.storage.local_cache import LocalCache


def test_save_and_load_attempt_and_exam_cache(client_data_dir) -> None:
    cache = LocalCache(base_dir=client_data_dir)
    answers = {"q-1": {"answer_text": "Draft answer", "selected_option_ids": []}}

    cache.save_exam_cache("exam-1", "Student One", answers, dirty=True)
    cache.save_attempt_cache("attempt-1", "exam-1", "Student One", answers, dirty=False)

    exam_record = cache.load_exam_cache("exam-1", "Student One")
    attempt_record = cache.load_attempt_cache("attempt-1", "Student One")

    assert exam_record is not None
    assert exam_record.dirty is True
    assert exam_record.answers["q-1"]["answer_text"] == "Draft answer"
    assert attempt_record is not None
    assert attempt_record.dirty is False


def test_load_latest_for_exam_prefers_newer_attempt_cache(client_data_dir) -> None:
    cache = LocalCache(base_dir=client_data_dir)
    cache.save_exam_cache(
        "exam-1",
        "student1",
        {"q-1": {"answer_text": "Older", "selected_option_ids": []}},
        dirty=True,
    )
    cache.save_attempt_cache(
        "attempt-1",
        "exam-1",
        "student1",
        {"q-1": {"answer_text": "Newer", "selected_option_ids": []}},
        dirty=False,
    )

    latest = cache.load_latest_for_exam("exam-1", "student1")

    assert latest is not None
    assert latest.attempt_id == "attempt-1"
    assert latest.answers["q-1"]["answer_text"] == "Newer"


def test_corrupted_cache_is_quarantined_and_ignored(client_data_dir) -> None:
    cache = LocalCache(base_dir=client_data_dir)
    broken_path = cache.attempt_path("broken")
    broken_path.write_text("{not-valid-json", encoding="utf-8")

    result = cache.load_attempt_cache("broken", "student1")

    assert result is None
    assert broken_path.exists() is False
    assert list(cache.cache_dir.glob("attempt_broken.json.corrupt.*"))


def test_submit_archive_moves_attempt_cache_out_of_active_cache(client_data_dir) -> None:
    cache = LocalCache(base_dir=client_data_dir)
    cache.save_attempt_cache(
        "attempt-2",
        "exam-2",
        "student2",
        {"q-1": {"answer_text": "Final", "selected_option_ids": []}},
        dirty=False,
    )

    cache.archive_attempt_cache("attempt-2")

    assert cache.attempt_path("attempt-2").exists() is False
    archived_files = list(cache.archive_dir.glob("attempt_attempt-2_*.json"))
    assert len(archived_files) == 1
    payload = json.loads(archived_files[0].read_text(encoding="utf-8"))
    assert payload["answers"]["q-1"]["answer_text"] == "Final"
