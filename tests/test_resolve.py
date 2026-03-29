import os
from pathlib import Path
from unittest.mock import patch

from ansel.template import resolve_vars


def test_resolve_static():
    raw = {"planet": "tatooine", "moons": 2}
    resolved = resolve_vars(raw, Path("."))
    assert resolved == {"planet": "tatooine", "moons": 2}


def test_resolve_env():
    with patch.dict(os.environ, {"USER": "vader"}):
        raw = {"pilot": "${USER}"}
        resolved = resolve_vars(raw, Path("."))
        assert resolved["pilot"] == "vader"


def test_resolve_cmd(tmp_path):
    raw = {"ship": "!cmd echo 'millennium-falcon'"}
    resolved = resolve_vars(raw, tmp_path)
    assert resolved["ship"] == "millennium-falcon"


def test_resolve_nested(tmp_path):
    raw = {
        "empire": "galactic-empire",
        "lord": "!cmd echo 'vader'",
        "threat": "!cmd echo 'Hello, ${lord} from ${empire}'",
    }
    resolved = resolve_vars(raw, tmp_path)
    assert resolved["empire"] == "galactic-empire"
    assert resolved["lord"] == "vader"
    assert resolved["threat"] == "Hello, vader from galactic-empire"


def test_resolve_order_independence(tmp_path):
    raw = {
        "threat": "!cmd echo 'Hello, ${lord} from ${empire}'",
        "empire": "galactic-empire",
        "lord": "!cmd echo 'vader'",
    }
    resolved = resolve_vars(raw, tmp_path)
    assert resolved["threat"] == "Hello, vader from galactic-empire"


def test_resolve_unknown_env(tmp_path):
    raw = {"force_side": "${UNKNOWN_SIDE}_side"}
    resolved = resolve_vars(raw, tmp_path)
    assert resolved["force_side"] == "_side"


def test_resolve_env_fallback():
    with patch.dict(os.environ, {}, clear=True):
        raw = {"captain": "${MISSING_CAPTAIN:-han-solo}"}
        resolved = resolve_vars(raw, Path("."))
        assert resolved["captain"] == "han-solo"

    with patch.dict(os.environ, {"EXISTING_USER": "del-piero"}):
        raw = {"captain": "${EXISTING_USER:-fallback-captain}"}
        resolved = resolve_vars(raw, Path("."))
        assert resolved["captain"] == "del-piero"
