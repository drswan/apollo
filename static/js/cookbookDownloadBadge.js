// static/js/cookbookDownloadBadge.js
import { parseXetProgress } from './cookbookXetProgress.js';

/**
 * Badge text for a running download. Shared by the live poll and every list
 * re-render so the badge doesn't flip between two labels.
 *
 * live: the last text the live poll computed from the full tmux snapshot
 *   (e.g. "14% · 7.9MB/s"). It knows the real %, so it wins when present.
 * progress: the backend's last progress line (task.progress). Fallback after
 *   a page reload, before the first poll.
 *
 * Pure so it's unit-testable under node.
 */
export function downloadBadgeText(progress, live) {
  if (live) return live;
  const raw = String(progress || '').trim();
  if (!raw) return 'downloading';
  const pct = raw.match(/(\d+)%/);
  if (pct) return pct[0];
  if (/^(?:Downloading|Fetching|Resuming)\s+'[^']+'\s+to\s+'[^']+/i.test(raw)
    || /^Downloading\s*\(incomplete\b/i.test(raw)) {
    return 'downloading';
  }
  // hf >= 1.x Xet line has no %; show bytes + speed instead of the raw bar.
  const xet = parseXetProgress(raw);
  if (xet) return `${xet.downloaded} · ${xet.speed}`;
  return raw;
}
