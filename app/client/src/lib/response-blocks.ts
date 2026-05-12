/**
 * Parses assistant message text for structured response blocks (refresh_table,
 * knowledge_base) so the UI can render them with dedicated styled components.
 * Block format: ```blockType\ncontent\n```
 */

export type ResponseSegment =
  | { type: 'markdown'; content: string }
  | {
      type: 'refresh_table';
      content: string;
      parsed: { table: string };
    }
  | {
      type: 'knowledge_base';
      content: string;
      parsed: { header: string; items: string[]; footer?: string };
    };

const FENCE = '```';
const BLOCK_REFRESH_TABLE = 'refresh_table';
const BLOCK_KNOWLEDGE_BASE = 'knowledge_base';

/** Matches opening fence then optional whitespace/newline then block type (for detection). */
const RE_REFRESH_TABLE = /```\s*refresh_table/i;
const RE_KNOWLEDGE_BASE = /```\s*knowledge_base/i;

function parseRefreshTable(inner: string): { table: string } {
  const table = inner.trim().split(/\r?\n/)[0]?.trim() ?? '';
  return { table };
}

/** Parse knowledge_base: header, bullet items, optional --- divider, optional footer. */
function parseKnowledgeBase(inner: string): {
  header: string;
  items: string[];
  footer?: string;
} {
  const lines = inner.trim().split(/\r?\n/).map((l) => l.trim());
  const headerLines: string[] = [];
  const items: string[] = [];
  let footer = '';
  let phase: 'header' | 'items' | 'footer' = 'header';

  for (const line of lines) {
    if (line === '---') {
      phase = 'footer';
      continue;
    }
    if (phase === 'header') {
      if (line.startsWith('- ')) {
        phase = 'items';
        items.push(line.slice(2).trim());
      } else {
        headerLines.push(line);
      }
      continue;
    }
    if (phase === 'items') {
      if (line.startsWith('- ')) {
        items.push(line.slice(2).trim());
      } else if (line === '---') {
        phase = 'footer';
      } else if (line) {
        items.push(line);
      }
      continue;
    }
    if (phase === 'footer' && line) {
      footer += (footer ? '\n' : '') + line;
    }
  }

  return {
    header: headerLines.join(' ').trim(),
    items,
    footer: footer.trim() || undefined,
  };
}

/**
 * Splits message text into segments: markdown and structured blocks.
 */
export function parseResponseBlocks(text: string): ResponseSegment[] {
  const segments: ResponseSegment[] = [];
  let remaining = text;

  while (remaining.length > 0) {
    const open = remaining.indexOf(FENCE);
    if (open < 0) {
      if (remaining.trim()) segments.push({ type: 'markdown', content: remaining });
      break;
    }

    const before = remaining.slice(0, open);
    if (before.trim()) segments.push({ type: 'markdown', content: before });
    remaining = remaining.slice(open + FENCE.length);
    // Allow optional whitespace/newline after ``` before language tag
    const afterFence = remaining.replace(/^\s+/, '');
    const newline = afterFence.indexOf('\n');
    const lang =
      newline >= 0
        ? afterFence.slice(0, newline).trim().toLowerCase()
        : afterFence.trim().toLowerCase();
    const contentStart =
      remaining.length - afterFence.length + (newline >= 0 ? newline + 1 : afterFence.length);
    const closeIdx = remaining.indexOf(FENCE, contentStart);
    if (closeIdx < 0) {
      segments.push({ type: 'markdown', content: FENCE + remaining });
      break;
    }

    const inner = remaining.slice(contentStart, closeIdx);
    remaining = remaining.slice(closeIdx + FENCE.length);

    if (lang === BLOCK_REFRESH_TABLE) {
      try {
        const parsed = parseRefreshTable(inner);
        segments.push({ type: 'refresh_table', content: inner, parsed });
      } catch {
        segments.push({
          type: 'markdown',
          content: FENCE + BLOCK_REFRESH_TABLE + '\n' + inner + FENCE,
        });
      }
    } else if (lang === BLOCK_KNOWLEDGE_BASE) {
      try {
        const parsed = parseKnowledgeBase(inner);
        segments.push({ type: 'knowledge_base', content: inner, parsed });
      } catch {
        segments.push({
          type: 'markdown',
          content: FENCE + BLOCK_KNOWLEDGE_BASE + '\n' + inner + FENCE,
        });
      }
    } else {
      segments.push({
        type: 'markdown',
        content: FENCE + lang + (newline >= 0 ? '\n' + inner : '') + FENCE,
      });
    }
  }

  return segments;
}

/** Returns true if text contains any structured block we handle. */
export function hasResponseBlocks(text: string): boolean {
  return RE_REFRESH_TABLE.test(text) || RE_KNOWLEDGE_BASE.test(text);
}
