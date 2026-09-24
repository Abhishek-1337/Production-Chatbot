"""
Regression test: pydantic-ai's stream_text() yields the FULL text so far on
each iteration by default. _run_agent_stream must consume it with delta=True,
otherwise cumulative snapshots get concatenated into a self-repeating answer.
"""
import asyncio
import sys
from unittest.mock import patch

sys.path.insert(0, ".")

import api.v1.controllers.chat_message as cm


class _FakeResult:
    """Emulates StreamedRunResult with real cumulative-snapshot semantics."""

    def __init__(self, snapshots):
        self._snapshots = snapshots

    async def stream_text(self, *, delta=False):
        if delta:
            prev = ""
            for snap in self._snapshots:
                yield snap[len(prev):]
                prev = snap
        else:
            for snap in self._snapshots:
                yield snap

    def usage(self):
        return None


class _FakeStreamCM:
    def __init__(self, result):
        self._result = result

    async def __aenter__(self):
        return self._result

    async def __aexit__(self, *args):
        return False


def test_run_agent_stream_does_not_duplicate_snapshots():
    snapshots = [
        "This cover letter is from Ab",
        "This cover letter is from Abhishek, who is applying",
        "This cover letter is from Abhishek, who is applying for the role.",
    ]
    fake_agent = type("FakeAgent", (), {})()
    fake_agent.run_stream = lambda prompt: _FakeStreamCM(_FakeResult(snapshots))

    with patch.object(cm, "agent", fake_agent):
        full, _ = asyncio.run(cm._run_agent_stream("summarize"))

    assert full == snapshots[-1]
    assert full.count("This cover letter is from") == 1


if __name__ == "__main__":
    test_run_agent_stream_does_not_duplicate_snapshots()
    print("stream accumulation test: PASS")
