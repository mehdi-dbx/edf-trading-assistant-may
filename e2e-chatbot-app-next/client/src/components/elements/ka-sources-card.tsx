import { memo, useState } from 'react';
import { ChevronDownIcon } from 'lucide-react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';

export type KaSourceItem = { title: string; excerpt: string };

export type KaToolPayload = {
  answer: string;
  assistant_name?: string;
  sources?: KaSourceItem[];
};

function normalizeSourceRow(raw: Record<string, unknown>): KaSourceItem | null {
  const title =
    (typeof raw.title === 'string' && raw.title) ||
    (typeof raw.document_name === 'string' && raw.document_name) ||
    (typeof raw.name === 'string' && raw.name) ||
    '';
  const excerpt =
    typeof raw.excerpt === 'string'
      ? raw.excerpt
      : typeof raw.text === 'string'
        ? raw.text
        : '';
  if (!title && !excerpt) return null;
  return { title: title || 'Source', excerpt };
}

function payloadFromParsedObject(o: Record<string, unknown>): KaToolPayload | null {
  if (typeof o.answer !== 'string') return null;
  const rawSources = o.sources ?? o.source_documents ?? o.documents;
  const sources: KaSourceItem[] = Array.isArray(rawSources)
    ? rawSources
        .map((s) =>
          s && typeof s === 'object'
            ? normalizeSourceRow(s as Record<string, unknown>)
            : null,
        )
        .filter((x): x is KaSourceItem => x !== null)
    : [];
  return {
    answer: o.answer,
    assistant_name:
      typeof o.assistant_name === 'string' ? o.assistant_name : undefined,
    sources,
  };
}

/** Parses structured JSON from `query_knowledge_assistant` tool output; returns null if not valid. */
export function parseKaToolOutput(output: string): KaToolPayload | null {
  try {
    const parsed: unknown = JSON.parse(output);
    if (!parsed || typeof parsed !== 'object') return null;
    return payloadFromParsedObject(parsed as Record<string, unknown>);
  } catch {
    return null;
  }
}

/**
 * Tool output may arrive as a JSON string or as an already-parsed object from the AI SDK stream.
 */
export function parseKaToolOutputFromUnknown(
  output: unknown,
): KaToolPayload | null {
  if (output == null) return null;
  if (typeof output === 'object' && !Array.isArray(output)) {
    return payloadFromParsedObject(output as Record<string, unknown>);
  }
  if (typeof output === 'string') {
    return parseKaToolOutput(output);
  }
  return null;
}

type KaSourcesCardProps = {
  answer: string;
  sources: KaSourceItem[];
  assistantName?: string;
};

export const KaSourcesCard = memo(function KaSourcesCard({
  answer,
  sources,
  assistantName,
}: KaSourcesCardProps) {
  const [open, setOpen] = useState(false);
  const n = sources.length;

  return (
    <div
      className={cn(
        'rounded-lg border-2 border-slate-200 bg-gray-100 px-4 py-3 shadow-sm',
        'dark:border-slate-600 dark:bg-gray-800/60',
      )}
      data-response-type="ka_sources"
    >
      {assistantName ? (
        <p className="mb-2 text-muted-foreground text-xs">{assistantName}</p>
      ) : null}
      <div className="whitespace-pre-wrap text-foreground text-sm">{answer}</div>
      {n === 0 ? (
        <p className="mt-2 text-muted-foreground text-xs">
          No source documents list was returned for this query (citations may be
          absent from the API response).
        </p>
      ) : null}
      {n > 0 ? (
        <Collapsible
          open={open}
          onOpenChange={setOpen}
          className="group mt-3 w-full"
        >
          <CollapsibleTrigger
            className={cn(
              'flex w-full items-center justify-between gap-2 rounded-md border border-slate-200 bg-muted/40 px-3 py-2',
              'text-left text-muted-foreground text-xs uppercase tracking-wide',
              'dark:border-slate-600',
            )}
          >
            <span>Sources ({n})</span>
            <ChevronDownIcon className="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-180" />
          </CollapsibleTrigger>
          <CollapsibleContent
            className={cn(
              'mt-2 space-y-2 border-slate-200 border-t pt-2 dark:border-slate-600',
              'data-[state=closed]:animate-out data-[state=open]:animate-in',
            )}
          >
            <ul className="space-y-3">
              {sources.map((s, i) => (
                <li key={`${s.title}-${i}`} className="text-sm">
                  <p className="font-medium text-foreground">{s.title}</p>
                  {s.excerpt ? (
                    <p className="wrap-break-word mt-1 text-muted-foreground">
                      {s.excerpt}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          </CollapsibleContent>
        </Collapsible>
      ) : null}
    </div>
  );
});
