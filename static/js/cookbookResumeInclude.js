// static/js/cookbookResumeInclude.js
/**
 * Include filter for resuming a cached model's download. Without one, `hf
 * download <repo>` pulls every file: for a GGUF repo that is every quant
 * (e.g. 94.7 GB instead of the 11.6 GB Q4_K_M that was asked for).
 *
 * 1. The include of the latest Cookbook download task for this repo.
 * 2. Else the single quant shared by the GGUF files already in the cache.
 * 3. Else null: unknown, the caller must warn that the whole repo downloads.
 *
 * Pure so it's unit-testable under node.
 */
const _QUANT_RE = /(?:^|[-_./])((?:UD-)?(?:IQ[1-8]_[A-Z0-9]+|Q[2-8]_K_[MLS]|Q[2-8]_K|Q[2-8]_[0-9]|MXFP4|BF16|F16|F32))(?=[-_./]|$)/i;

export function resumeIncludeFor(repo, tasks, ggufFiles) {
  const fromTask = (Array.isArray(tasks) ? tasks : [])
    .filter(t => t && t.type === 'download' && t.payload?.repo_id === repo && t.payload?.include)
    .sort((a, b) => (b.ts || 0) - (a.ts || 0))[0];
  if (fromTask) return fromTask.payload.include;

  const quants = new Set();
  for (const f of (Array.isArray(ggufFiles) ? ggufFiles : [])) {
    const m = String(f).replace(/\.gguf$/i, '').match(_QUANT_RE);
    quants.add(m ? m[1].toUpperCase() : null);
  }
  if (quants.size === 1) {
    const [q] = quants;
    if (q) return `*${q}*`;
  }
  return null;
}
