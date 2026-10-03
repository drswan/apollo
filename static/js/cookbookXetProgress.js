// static/js/cookbookXetProgress.js
/**
 * Progress for huggingface_hub's Xet downloader (hf CLI >= 1.x), which prints:
 *
 *   Downloading bytes: ███▏      |  618MB, 11.2MB/s
 *   Reconstructing (incomplete total...):   1%|  | 67.6MB / 11.6GB, 2.80MB/s
 *   Fetching 1 files:   0%|       | 0/1 [00:00<?, ?it/s]
 *
 * "Downloading bytes" is the real network transfer but has no % because Xet
 * does not know the total up front. "Reconstructing" writes the final file in
 * order, so its %, speed and byte counter lag far behind and freeze for long
 * stretches. Read the downloaded bytes and speed from the first line and the
 * size from the second's "/ 11.6GB".
 *
 * Returns { downloaded, speed, pct } or null when there is no Xet block (old
 * hf_transfer output keeps the existing card logic). pct is null when the size
 * is not printed yet, and is capped at 99: the total is "incomplete" and can
 * grow, so only the task finishing means 100%.
 *
 * Pure (string in, object out) so it's unit-testable under node.
 */
const _UNIT = { '': 1, K: 1e3, M: 1e6, G: 1e9, T: 1e12 };

function _toBytes(num, unit) {
  return parseFloat(num) * (_UNIT[(unit || '').toUpperCase()] || 1);
}

export function parseXetProgress(snapshot) {
  // Drop line breaks without adding spaces: tmux wraps at the pane width and
  // can split a token ("11.6G" / "B"), so rejoining keeps numbers intact.
  const flat = String(snapshot || '').replace(/[\r\n]+/g, '');
  const dl = [...flat.matchAll(/Downloading bytes:[^|]*\|\s*([\d.]+)\s?([KMGT]?)B,\s*([\d.]+\s?[KMGT]?B\/s)/gi)].pop();
  if (!dl) return null;
  const total = [...flat.matchAll(/Reconstructing[^|]*\|[^|]*\|\s*[\d.]+\s?[KMGT]?B\s*\/\s*([\d.]+)\s?([KMGT]?)B/gi)].pop();
  const doneBytes = _toBytes(dl[1], dl[2]);
  const totalBytes = total ? _toBytes(total[1], total[2]) : 0;
  return {
    downloaded: `${dl[1]}${dl[2]}B`,
    speed: dl[3].replace(/\s/g, ''),
    pct: totalBytes > 0 ? Math.min(99, Math.round((doneBytes / totalBytes) * 100)) : null,
  };
}
