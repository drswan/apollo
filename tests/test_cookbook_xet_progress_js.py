"""huggingface_hub >= 1.x downloads over Xet and prints a different progress
block than the old hf_transfer bar the Cookbook download card was written for:

    Downloading bytes: ███▏      |  618MB, 11.2MB/s
    Reconstructing (incomplete total...):   1%|  | 67.6MB / 11.6GB, 2.80MB/s
    Fetching 1 files:   0%|       | 0/1 [00:00<?, ?it/s]

"Downloading bytes" is the real network transfer but carries no % (Xet does
not know the total up front). "Reconstructing" writes the final file in order,
so it lags far behind and stalls for long stretches. The card used to read the
% and speed from Reconstructing/Fetching (showing "0% · 2.80MB/s" while the
network ran at 11 MB/s) and keyed the stale-download watchdog off the frozen
"67.6MB / 11.6GB" counter, which could kill a healthy download.

parseXetProgress (cookbookXetProgress.js) reads the Xet block. Pure function,
executed under node (cookbookRunning.js pulls in browser-only modules).
"""

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_HAS_NODE = shutil.which("node") is not None

XET_SNAPSHOT = (
    "Downloading bytes: ███▏                                  |  618MB, 11.2MB/s\n"
    "Reconstructing (incomplete total...):   1%|       | 67.6MB / 11.6GB, 2.80MB/s\n"
    "Fetching 1 files:   0%|                                  | 0/1 [00:00<?, ?it/s]\n"
)


@pytest.fixture(scope="module")
def node_available():
    if not _HAS_NODE:
        pytest.skip("node binary not on PATH")


def _parse(snapshot: str):
    script = textwrap.dedent(f"""
        const {{ parseXetProgress }} = await import('./static/js/cookbookXetProgress.js');
        console.log(JSON.stringify(parseXetProgress({json.dumps(snapshot)})));
    """)
    res = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=_REPO, capture_output=True, timeout=15, text=True, encoding="utf-8",
    )
    if res.returncode != 0:
        raise AssertionError(f"node failed:\n{res.stderr}")
    return json.loads(res.stdout.strip().splitlines()[-1])


def test_uses_downloading_bytes_for_speed_and_percent(node_available):
    p = _parse(XET_SNAPSHOT)
    assert p["downloaded"] == "618MB"
    assert p["speed"] == "11.2MB/s"  # network rate, not Reconstructing's 2.80MB/s
    assert p["pct"] == 5  # 618 MB of 11.6 GB, not the 0-1% of Fetching/Reconstructing


def test_survives_tmux_line_wrap(node_available):
    """tmux capture wraps at the pane width; the parser must not depend on lines."""
    wrapped = (
        "Downloading bytes: ███                   |  1.50GB, 1\n"
        "2.1MB/s\n"
        "Reconstructing (incomplete total...):   1%|  | 67.6MB / 11.6G\n"
        "B, 1.98MB/s\n"
    )
    p = _parse(wrapped)
    assert p["downloaded"] == "1.50GB"
    assert p["pct"] == 13


def test_percent_never_reads_100_before_done(node_available):
    """Downloaded bytes can exceed the 'incomplete' total (protocol overhead,
    total still growing); cap at 99 so the card never claims completion."""
    snap = XET_SNAPSHOT.replace("618MB, 11.2MB/s", "11.9GB, 11.2MB/s")
    assert _parse(snap)["pct"] == 99


def test_no_xet_block_returns_null(node_available):
    """Old hf_transfer output keeps using the existing card logic."""
    assert _parse("Downloading (incomplete total...): 73%| 1.81G/2.49G") is None
    assert _parse("") is None
