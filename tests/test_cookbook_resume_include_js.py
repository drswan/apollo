"""Cookbook "Resume download" on a cached model sent only {repo_id}, with no
include filter. For GGUF repos that means every quant: resuming a stalled
gpt-oss-20b-GGUF Q4_K_M download (11.6 GB) started a 22-file, 94.7 GB pull.

resumeIncludeFor (cookbookResumeInclude.js) recovers the filter: first the
include of the latest Cookbook download task for the repo, else the single
quant shared by the GGUF files already in the cache. null means unknown, and
the caller warns that the whole repo will be downloaded. Pure, run under node.
"""

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_HAS_NODE = shutil.which("node") is not None
REPO = "unsloth/gpt-oss-20b-GGUF"


@pytest.fixture(scope="module")
def node_available():
    if not _HAS_NODE:
        pytest.skip("node binary not on PATH")


def _include(repo, tasks=None, gguf_files=None):
    script = textwrap.dedent(f"""
        const {{ resumeIncludeFor }} = await import('./static/js/cookbookResumeInclude.js');
        const r = resumeIncludeFor({json.dumps(repo)}, {json.dumps(tasks)}, {json.dumps(gguf_files)});
        console.log(JSON.stringify(r === undefined ? 'UNDEFINED' : r));
    """)
    res = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=_REPO, capture_output=True, timeout=15, text=True, encoding="utf-8",
    )
    if res.returncode != 0:
        raise AssertionError(f"node failed:\n{res.stderr}")
    return json.loads(res.stdout.strip().splitlines()[-1])


def _task(repo, include, ts):
    return {"type": "download", "ts": ts, "payload": {"repo_id": repo, "include": include}}


def test_reuses_include_of_latest_download_task(node_available):
    tasks = [
        _task(REPO, "*Q8_0*", 1),
        _task("other/repo-GGUF", "*Q2_K*", 5),
        _task(REPO, "*Q4_K_M*", 3),
        {"type": "serve", "ts": 9, "payload": {"repo_id": REPO}},
    ]
    assert _include(REPO, tasks) == "*Q4_K_M*"


def test_infers_single_quant_from_cached_gguf_files(node_available):
    assert _include(REPO, [], ["gpt-oss-20b-Q4_K_M.gguf"]) == "*Q4_K_M*"
    assert _include(REPO, None, ["Q5_K_M/m-00001-of-00002.gguf", "Q5_K_M/m-00002-of-00002.gguf"]) == "*Q5_K_M*"
    assert _include(REPO, None, ["gpt-oss-20b-F16.gguf"]) == "*F16*"


def test_unknown_when_quants_mixed_or_nothing_known(node_available):
    assert _include(REPO, [], ["m-Q4_K_M.gguf", "m-Q8_0.gguf"]) is None
    assert _include(REPO, [], []) is None
    assert _include(REPO) is None
    # A task for the repo without an include (e.g. a safetensors repo) is not a filter.
    assert _include(REPO, [_task(REPO, None, 1)]) is None
