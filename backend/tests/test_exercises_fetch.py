import json
import os
import tempfile
from pathlib import Path

import backend.main as main


def make_temp_json(data: dict) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    Path(path).write_text(json.dumps(data), encoding="utf-8")
    return "file://" + path


def test_load_exercises_from_uri_with_valid_local_file():
    data = {
        "exercise_library": [
            {
                "exercise_id": 101,
                "name": "Test Squat",
                "equipment_type": "Barbell",
                "target_muscle_groups": {"primary": ["Legs"]},
                "utility": "Strength",
            },
            {
                "exercise_id": 102,
                "name": "Test Run",
                "equipment_type": None,
                "target_muscle_groups": {"primary": ["Full Body"]},
                "utility": "Cardio",
            },
        ]
    }
    uri = make_temp_json(data)
    items = main.load_exercises_from_uri(uri, timeout=2.0)
    assert isinstance(items, list)
    assert len(items) == 2
    assert items[0].id == 101 and items[0].name == "Test Squat"
    assert items[1].type == "cardio"


def test_load_exercises_from_uri_with_invalid_json_returns_empty():
    # create a temp file with invalid JSON
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    Path(path).write_text("{ invalid json ", encoding="utf-8")
    uri = "file://" + path
    items = main.load_exercises_from_uri(uri, timeout=1.0)
    assert items == []
