"""Тесты удалённого рубильника + принудительного обновления."""
from casecut.control.gate import evaluate_status, check_remote


def test_enabled_allows():
    d = evaluate_status({"enabled": True}, "0.1.0")
    assert d.allowed and d.kind == "ok"


def test_missing_enabled_defaults_allow():
    assert evaluate_status({}, "0.1.0").allowed


def test_disabled_blocks_with_message():
    d = evaluate_status({"enabled": False, "message": "стоп"}, "0.1.0")
    assert not d.allowed
    assert d.kind == "disabled"
    assert d.message == "стоп"


def test_min_version_blocks_as_update():
    d = evaluate_status({"enabled": True, "min_version": "0.2.0"}, "0.1.0")
    assert not d.allowed
    assert d.kind == "update"
    assert "0.2.0" in d.message


def test_min_version_ok():
    assert evaluate_status({"enabled": True, "min_version": "0.1.0"}, "0.1.0").allowed


def test_min_version_custom_message():
    d = evaluate_status(
        {"enabled": True, "min_version": "2.0.0", "update_message": "обнови"}, "0.1.0")
    assert not d.allowed and d.message == "обнови"


def test_check_remote_failopen_on_network_error():
    def boom(_u, _t):
        raise OSError("no network")
    assert check_remote("http://x", "0.1.0", fetch=boom).allowed


def test_check_remote_failopen_on_bad_json():
    def fake(_u, _t):
        return "not a json"
    assert check_remote("http://x", "0.1.0", fetch=fake).allowed


def test_check_remote_disabled():
    def fake(_u, _t):
        return '{"enabled": false, "message": "off"}'
    d = check_remote("http://x", "0.1.0", fetch=fake)
    assert not d.allowed and d.kind == "disabled" and d.message == "off"


def test_check_remote_update_required():
    def fake(_u, _t):
        return '{"enabled": true, "min_version": "9.9.9"}'
    d = check_remote("http://x", "0.1.0", fetch=fake)
    assert not d.allowed and d.kind == "update"
