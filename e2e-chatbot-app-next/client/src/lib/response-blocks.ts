/**
 * Parses assistant message text for structured response blocks (turnaround_started,
 * live_turnaround_checklist) so the UI can render them with dedicated styled components.
 * Block format: ```blockType\ncontent\n```
 */

export type ResponseSegment =
  | { type: 'markdown'; content: string }
  | {
      type: 'turnaround_started';
      content: string;
      parsed: { flight: string; etaMin: string; tobt: string };
    }
  | {
      type: 'live_turnaround_checklist';
      content: string;
      parsed: {
        flight: string;
        tasks: Array<{ name: string; status: string }>;
        readiness: string;
      };
    };

const FENCE = '```';
const BLOCK_TURNAROUND_STARTED = 'turnaround_started';
const BLOCK_LIVE_CHECKLIST = 'live_turnaround_checklist';

/** Matches opening fence then optional whitespace/newline then block type (for detection). */
const RE_TURNAROUND_STARTED = /```\s*turnaround_started/i;
const RE_LIVE_CHECKLIST = /```\s*live_turnaround_checklist/i;

function parseTurnaroundStarted(inner: string): {
  flight: string;
  etaMin: string;
  tobt: string;
} {
  const lines = inner.trim().split(/\r?\n/);
  const first = lines[0]?.trim() ?? '';
  const second = lines[1]?.trim() ?? '';
  const flight = first.replace(/^Turnaround started\s*-\s*/i, '').trim();
  const etaMatch = second.match(/ETA:\s*([^\t\s]+)/i);
  const tobtMatch = second.match(/TOBT\s*([^\s]+)/i);
  return {
    flight,
    etaMin: etaMatch?.[1] ?? '',
    tobt: tobtMatch?.[1] ?? '',
  };
}

function parseLiveTurnaroundChecklist(inner: string): {
  flight: string;
  tasks: Array<{ name: string; status: string }>;
  readiness: string;
} {
  const lines = inner.trim().split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  let flight = '';
  const tasks: Array<{ name: string; status: string }> = [];
  let readiness = '';

  const titleLine = 'Live Turnaround Checklist (synced with TMS)';
  const flightPrefix = 'Turnaround - ';
  const readinessPrefix = 'Readiness vs TOBT: ';

  for (const line of lines) {
    if (line === titleLine) continue;
    if (line.startsWith(flightPrefix)) {
      flight = line.slice(flightPrefix.length).trim();
      continue;
    }
    if (line.startsWith(readinessPrefix)) {
      readiness = line.slice(readinessPrefix.length).trim();
      continue;
    }
    const tab = line.indexOf('\t');
    const spaceRun = line.match(/\s{2,}/);
    const statusMatch = line.match(/\s+(Notified|Pending|In Progress|Completed)$/i);
    const sep =
      tab >= 0
        ? tab
        : spaceRun?.index ?? (statusMatch ? line.length - statusMatch[0].length : -1);
    if (sep >= 0) {
      const name = line.slice(0, sep).trim();
      const status = line.slice(sep).trim();
      if (name && status) tasks.push({ name, status });
    }
  }

  return { flight, tasks, readiness };
}

/**
 * Splits message text into segments: markdown and structured blocks.
 * Recognises ```turnaround_started ... ``` and ```live_turnaround_checklist ... ```.
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

    if (lang === BLOCK_TURNAROUND_STARTED) {
      try {
        const parsed = parseTurnaroundStarted(inner);
        segments.push({ type: 'turnaround_started', content: inner, parsed });
      } catch {
        segments.push({ type: 'markdown', content: FENCE + BLOCK_TURNAROUND_STARTED + '\n' + inner + FENCE });
      }
    } else if (lang === BLOCK_LIVE_CHECKLIST) {
      try {
        const parsed = parseLiveTurnaroundChecklist(inner);
        segments.push({ type: 'live_turnaround_checklist', content: inner, parsed });
      } catch {
        segments.push({ type: 'markdown', content: FENCE + BLOCK_LIVE_CHECKLIST + '\n' + inner + FENCE });
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
  return RE_TURNAROUND_STARTED.test(text) || RE_LIVE_CHECKLIST.test(text);
}
