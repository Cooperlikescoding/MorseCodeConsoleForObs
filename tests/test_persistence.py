import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from config import Settings, load_settings_into, save_settings


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "user_settings.json")

    original = Settings(wpm=15, tone_hz=700.0, tolerance_percent=80, theme_name="latte")
    original.practice_words.append("JUPITER")
    original.presets["kids"] = {"wpm": 5, "tone_hz": 600, "tolerance_percent": 90}
    save_settings(original)

    restored = Settings()  # fresh defaults, should be overwritten by the load
    loaded = load_settings_into(restored)

    assert loaded is True
    assert restored.wpm == 15
    assert restored.tone_hz == 700.0
    assert restored.tolerance_percent == 80
    assert restored.theme_name == "latte"
    assert "JUPITER" in restored.practice_words
    assert restored.presets["kids"] == {"wpm": 5, "tone_hz": 600, "tolerance_percent": 90}


def test_pin_hashes_persist(tmp_path, monkeypatch):
    # A changed PIN (and the previous one, for `pin undo`) must survive a restart.
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "user_settings.json")
    original = Settings(admin_pin_hash="newhash", previous_admin_pin_hash="oldhash")
    save_settings(original)

    restored = Settings()
    load_settings_into(restored)
    assert restored.admin_pin_hash == "newhash"
    assert restored.previous_admin_pin_hash == "oldhash"


def test_load_missing_file_is_a_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "does_not_exist.json")
    target = Settings(wpm=8)
    loaded = load_settings_into(target)
    assert loaded is False
    assert target.wpm == 8  # untouched


def test_load_corrupt_file_is_a_noop(tmp_path, monkeypatch):
    bad_file = tmp_path / "corrupt.json"
    bad_file.write_text("{not valid json")
    monkeypatch.setattr(config, "SETTINGS_FILE", bad_file)
    target = Settings(wpm=8)
    loaded = load_settings_into(target)
    assert loaded is False
    assert target.wpm == 8


def test_fullscreen_is_never_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "user_settings.json")
    save_settings(Settings())
    data = (tmp_path / "user_settings.json").read_text()
    assert "fullscreen" not in data
