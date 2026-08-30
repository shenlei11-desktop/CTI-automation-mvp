"""Unit tests for the OpenCode CLI wrapper (subprocess.run is mocked, no CLI invoked)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from research.lib.opencode_client import _run_opencode, classify, ping


def _text_event(text: str) -> str:
    return json.dumps({"type": "text", "part": {"type": "text", "text": text}})


def _completed(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


# --- _run_opencode -----------------------------------------------------------------


def test_run_opencode_concatenates_text_chunks_and_ignores_noise():
    ndjson = "\n".join(
        [
            _text_event("Hello "),
            "",
            "this is not json",
            json.dumps({"type": "tool", "part": {"type": "tool", "text": "ignored"}}),
            json.dumps({"type": "text", "part": {"type": "other", "text": "ignored"}}),
            _text_event("World"),
        ]
    )
    patched = patch("research.lib.opencode_client.subprocess.run", return_value=_completed(ndjson))
    with patched as mock_run:
        assert _run_opencode("p", "m", timeout=30) == "Hello World"
    cmd, kwargs = mock_run.call_args.args[0], mock_run.call_args.kwargs
    # The prompt is attached as a file (-f <path>), not passed on the command line --
    # a real prompt routinely exceeds cmd.exe's ~8191-char limit (npx always resolves
    # to npx.cmd on Windows, which always runs through cmd.exe).
    assert "run" in cmd and "m" in cmd and "--format" in cmd and "-f" in cmd
    assert "p" not in cmd
    attached_path = Path(cmd[cmd.index("-f") + 1])
    assert not attached_path.exists(), "temp prompt file should be cleaned up after the call"
    assert kwargs["timeout"] == 30 and kwargs["capture_output"] is True


def test_run_opencode_writes_prompt_to_attached_file():
    ndjson = _text_event("ok")
    captured_path = {}

    def _fake_run(cmd, **kwargs):
        path = Path(cmd[cmd.index("-f") + 1])
        captured_path["content"] = path.read_text(encoding="utf-8")
        return _completed(ndjson)

    with patch("research.lib.opencode_client.subprocess.run", side_effect=_fake_run):
        assert _run_opencode("the real prompt text", "m") == "ok"
    assert captured_path["content"] == "the real prompt text"


def test_run_opencode_empty_on_nonzero_exit():
    completed = _completed("", returncode=1)
    with patch("research.lib.opencode_client.subprocess.run", return_value=completed):
        assert _run_opencode("p", "m") == ""


def test_run_opencode_empty_on_timeout():
    with patch(
        "research.lib.opencode_client.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=[], timeout=10),
    ):
        assert _run_opencode("p", "m", timeout=10) == ""


# --- ping --------------------------------------------------------------------------


def test_ping_strips_successful_reply():
    with patch("research.lib.opencode_client._run_opencode", return_value="  ready  ") as mock_run:
        assert ping("m", timeout=45) == "ready"
    assert mock_run.call_args.args[1] == "m" and mock_run.call_args.kwargs["timeout"] == 45


def test_ping_raises_when_no_reply():
    with patch("research.lib.opencode_client._run_opencode", return_value=""):
        with pytest.raises(RuntimeError):
            ping("m")


# --- classify ----------------------------------------------------------------------

_VALID_JSON = '{"predicted_techniques": [{"technique_id": "T1059", "rank": 1}]}'


def test_classify_parses_valid_json_and_forwards_args():
    with patch("research.lib.opencode_client._run_opencode", return_value=_VALID_JSON) as mock_run:
        result = classify("my-model", "my-prompt", {"T1059"}, timeout=99)
    assert result.parse_failure is False
    assert result.ranked_ids == ["T1059"]
    assert result.attempts == 1
    args, kwargs = mock_run.call_args.args, mock_run.call_args.kwargs
    assert args[0] == "my-prompt" and args[1] == "my-model" and kwargs["timeout"] == 99


def test_classify_retries_once_then_succeeds():
    with patch(
        "research.lib.opencode_client._run_opencode",
        side_effect=["not valid json", _VALID_JSON],
    ) as mock_run:
        result = classify("m", "p", {"T1059"})
    assert result.parse_failure is False
    assert result.attempts == 2
    assert result.ranked_ids == ["T1059"]
    assert mock_run.call_count == 2
    second_prompt = mock_run.call_args_list[1].args[0]
    assert "not valid JSON" in second_prompt and "not valid json" in second_prompt


def test_classify_terminal_failure_after_two_invalid():
    with patch(
        "research.lib.opencode_client._run_opencode",
        side_effect=["nope", "still nope"],
    ) as mock_run:
        result = classify("m", "p", {"T1059"})
    assert result.parse_failure is True
    assert result.ranked_ids == []
    assert result.attempts == 2
    assert mock_run.call_count == 2


def test_classify_cache_hit_skips_subprocess():
    cache = MagicMock()
    cache.get.return_value = {
        "ranked_ids": ["T1059"],
        "parse_failure": False,
        "raw_text": "cached",
        "attempts": 1,
        "hallucinated": [],
    }
    with patch("research.lib.opencode_client._run_opencode") as mock_run:
        result = classify("m", "p", {"T1059"}, cache=cache)
    assert result.from_cache is True
    assert result.ranked_ids == ["T1059"]
    cache.get.assert_called_once_with("m", "p", "opencode-json")
    mock_run.assert_not_called()


def test_classify_cache_write_on_success():
    cache = MagicMock()
    cache.get.return_value = None
    with patch("research.lib.opencode_client._run_opencode", return_value=_VALID_JSON):
        result = classify("m", "p", {"T1059"}, cache=cache)
    assert result.ranked_ids == ["T1059"]
    cache.set.assert_called_once()
    model, prompt, fmt, stored = cache.set.call_args.args
    assert (model, prompt, fmt) == ("m", "p", "opencode-json")
    assert stored["ranked_ids"] == ["T1059"]
    assert "from_cache" not in stored
