import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import {
  PlusIcon,
  HistoryIcon,
  Maximize2,
  Minimize2,
  X,
  SkipBack,
  SkipForward,
} from 'lucide-react';

const CHECKLIST_FOR_CURRENT_TIME_MESSAGE = 'Show the turnaround checklist';

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    const h = d.getHours();
    const m = d.getMinutes();
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
  } catch {
    return iso;
  }
}

export function ChatPanelHeader({
  showIntermediateSteps,
  onToggleIntermediateSteps,
  onNewChat,
  onHistory,
  expanded,
  onExpand,
  onClose,
  sendMessage,
}: {
  showIntermediateSteps: boolean;
  onToggleIntermediateSteps: () => void;
  onNewChat: () => void;
  onHistory: () => void;
  expanded: boolean;
  onExpand: () => void;
  onClose?: () => void;
  sendMessage?: (message: {
    role: 'user';
    parts: Array<{ type: 'text'; text: string }>;
    metadata?: { source?: string };
  }) => void;
}) {
  const [displayTime, setDisplayTime] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTime = async (advance: boolean) => {
    const q = advance ? 'advance=true' : 'advance=false';
    const res = await fetch(`/api/current-time?${q}`);
    const data = await res.json().catch(() => ({}));
    const currentTime = (data as { currentTime?: string }).currentTime;
    if (res.ok && typeof currentTime === 'string') {
      setDisplayTime(currentTime);
      setError(null);
    } else {
      setError((data as { error?: string }).error || `Error ${res.status}`);
    }
  };

  const advanceTime = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/current-time?advance=true');
      const data = await res.json().catch(() => ({}));
      const currentTime = (data as { currentTime?: string }).currentTime;
      if (res.ok && typeof currentTime === 'string') {
        setDisplayTime(currentTime);
        setError(null);
        if (sendMessage) {
          sendMessage({
            role: 'user',
            parts: [{ type: 'text', text: CHECKLIST_FOR_CURRENT_TIME_MESSAGE }],
            metadata: { source: 'system' },
          });
        }
      } else {
        setError((data as { error?: string }).error || `Error ${res.status}`);
      }
    } catch {
      setError('Request failed');
    } finally {
      setLoading(false);
    }
  };

  const backwardTime = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/current-time/backward');
      const data = await res.json().catch(() => ({}));
      const currentTime = (data as { currentTime?: string }).currentTime;
      if (res.ok && typeof currentTime === 'string') {
        setDisplayTime(currentTime);
        setError(null);
      } else {
        setError((data as { error?: string }).error || `Error ${res.status}`);
      }
    } catch {
      setError('Request failed');
    } finally {
      setLoading(false);
    }
  };

  // Peek on mount so widget shows current simulated time without advancing
  useEffect(() => {
    fetchTime(false).catch(() => {});
  }, []);

  return (
    <header className="flex shrink-0 items-center justify-between gap-2 border-b bg-background px-3 py-2">
      <span className="font-semibold tracking-tight text-purple-600 text-sm">
        Garv AI Ops Advisor
      </span>
      <div className="flex items-center gap-1">
        <div className="flex items-center gap-1.5 rounded-full border border-border/80 bg-muted/50 px-2.5 py-1.5">
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 shrink-0 rounded-full"
            onClick={backwardTime}
            disabled={loading}
            aria-label="Step simulated time back"
            title="Step simulated time back"
          >
            <SkipBack className="h-3.5 w-3.5 text-muted-foreground" />
          </Button>
          <span
            className="min-w-10 font-mono text-xs tabular-nums text-muted-foreground"
            title={error ?? displayTime ?? 'Simulated time'}
          >
            {error ? (
              <span className="text-destructive" title={error}>
                Error
              </span>
            ) : displayTime ? (
              formatTime(displayTime)
            ) : (
              '—'
            )}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 shrink-0 rounded-full"
            onClick={advanceTime}
            disabled={loading}
            aria-label="Advance simulated time"
            title="Advance simulated time"
          >
            <SkipForward className="h-3.5 w-3.5 text-muted-foreground" />
          </Button>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onNewChat}
          aria-label="New chat"
        >
          <PlusIcon className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onHistory}
          aria-label="History"
        >
          <HistoryIcon className="h-4 w-4" />
        </Button>
        <Switch
          checked={showIntermediateSteps}
          onCheckedChange={onToggleIntermediateSteps}
          label="Steps"
          title="Show/hide tool steps"
        />
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onExpand}
          aria-label={expanded ? 'Tuck chat' : 'Expand chat'}
        >
          {expanded ? (
            <Minimize2 className="h-4 w-4" />
          ) : (
            <Maximize2 className="h-4 w-4" />
          )}
        </Button>
        {onClose != null && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
    </header>
  );
}
