/**
 * Shared clipboard and file export utilities.
 *
 * Every component that copies or downloads markdown should use these
 * helpers so error handling and browser fallbacks live in one place.
 */

/**
 * Copy text to the system clipboard.
 *
 * Uses the modern Clipboard API when available, with a textarea-based
 * fallback for older browsers (Safari <13.1, older WebViews).
 *
 * @returns `true` if the copy succeeded.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback: hidden textarea + execCommand
    try {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      // Keep off-screen to avoid layout shift
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      return true;
    } catch {
      console.error('Clipboard copy failed: both Clipboard API and execCommand unavailable');
      return false;
    }
  }
}

/**
 * Download a string as a `.md` file.
 *
 * Creates a temporary Blob URL, triggers a download, then revokes the URL.
 */
export function downloadMarkdown(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Build a full markdown string for a single chat message (Q + A + citations).
 *
 * Used by ChatMessage's per-message copy button so the user gets
 * the complete Q&A block, not just the raw answer text.
 */
export function formatMessageAsMarkdown(
  question: string,
  answer: string,
  riskLevel: string,
  citations: { source: string; page: number | null; section: string | null }[],
): string {
  const lines: string[] = [];
  lines.push(`**Q:** ${question}`);
  lines.push('');
  lines.push(answer);
  lines.push('');
  lines.push(`**Risk Level:** ${riskLevel}`);

  if (citations.length > 0) {
    lines.push('');
    lines.push('**Sources:**');
    citations.forEach((c, i) => {
      let src = `${i + 1}. ${c.source}`;
      if (c.page) src += ` (p. ${c.page})`;
      if (c.section) src += ` - ${c.section}`;
      lines.push(src);
    });
  }

  return lines.join('\n');
}
