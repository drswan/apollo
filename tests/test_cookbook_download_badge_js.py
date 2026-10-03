"""The Cookbook download badge is drawn by two paths: the ~3 s live poll (which
parses the whole tmux snapshot and knows the real %) and every list re-render
(_taskBadge, which only has task.progress = the backend's last progress line).

With hf >= 1.x the last line is Xet's "Downloading bytes: ███ | 1.58GB, 10.2MB/s",
which the re-render path did not recognise, so the badge flipped every few
seconds between "14% · 7.9MB/s" and the raw progress line.

downloadBadgeText (cookbookDownloadBadge.js) is the shared text for both paths:
the last live-poll text wins, else a compact form of the progress line.
"""

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_HAS_NODE = shutil.which("node") is not None

XET_LINE = "Downloading bytes: █████▏          |  1.58GB, 10.2MB/s"


@pytest.fixture(scope="module")
def node_available():
    if not _HAS_NODE:
        pytest.skip("node binary not on PATH")


def _badge(progress, live=None):
    script = textwrap.dedent(f"""
        const {{ downloadBadgeText }} = await import('./static/js/cookbookDownloadBadge.js');
        console.log(JSON.stringify(downloadBadgeText({json.dumps(progress)}, {json.dumps(live)})));
    """)
    res = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=_REPO, capture_output=True, timeout=15, text=True, encoding="utf-8",
    )
    if res.returncode != 0:
        raise AssertionError(f"node failed:\n{res.stderr}")
    return json.loads(res.stdout.strip().splitlines()[-1])


def test_live_poll_text_wins_over_progress_line(node_available):
    assert _badge(XET_LINE, "14% · 7.9MB/s") == "14% · 7.9MB/s"


def test_xet_line_without_live_text_is_compact(node_available):
    """After a page reload there is no live text yet: never show the raw bar."""
    assert _badge(XET_LINE) == "1.58GB · 10.2MB/s"


def test_existing_progress_forms_unchanged(node_available):
    assert _badge("") == "downloading"
    assert _badge("Downloading (incomplete total...): 73%| 1.81G/2.49G") == "73%"
    assert _badge("Downloading 'a.gguf' to '/x/a.gguf.incomplete'") == "downloading"
    assert _badge("finishing") == "finishing"
