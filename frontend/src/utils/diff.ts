export interface DiffSegment {
  type: 'unchanged' | 'added' | 'removed';
  value: string;
}

/**
 * Computes word-level diff between original and revised text
 * using Longest Common Subsequence (LCS) algorithm.
 */
export function computeWordDiff(origStr: string, revStr: string): DiffSegment[] {
  if (!origStr && !revStr) return [];
  if (!origStr) return [{ type: 'added', value: revStr }];
  if (!revStr) return [{ type: 'removed', value: origStr }];

  // Tokenize while preserving whitespace/punctuation boundaries
  const origTokens = origStr.match(/\S+|\s+/g) || [];
  const revTokens = revStr.match(/\S+|\s+/g) || [];

  const m = origTokens.length;
  const n = revTokens.length;

  // LCS dynamic programming table
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (origTokens[i - 1] === revTokens[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack to construct diff segments
  let i = m;
  let j = n;
  const rawSegments: DiffSegment[] = [];

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && origTokens[i - 1] === revTokens[j - 1]) {
      rawSegments.unshift({ type: 'unchanged', value: origTokens[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      rawSegments.unshift({ type: 'added', value: revTokens[j - 1] });
      j--;
    } else if (i > 0 && (j === 0 || dp[i][j - 1] < dp[i - 1][j])) {
      rawSegments.unshift({ type: 'removed', value: origTokens[i - 1] });
      i--;
    }
  }

  // Merge contiguous segments of the same type
  const merged: DiffSegment[] = [];
  for (const seg of rawSegments) {
    const last = merged[merged.length - 1];
    if (last && last.type === seg.type) {
      last.value += seg.value;
    } else {
      merged.push({ ...seg });
    }
  }

  return merged;
}
