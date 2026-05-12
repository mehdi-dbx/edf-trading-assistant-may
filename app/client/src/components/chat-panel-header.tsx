import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useTableRefresh } from '@/contexts/TableRefreshContext';
import { Switch } from '@/components/ui/switch';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  PlusIcon,
  HistoryIcon,
  Maximize2,
  Minimize2,
  X,
  RotateCcw,
  List,
} from 'lucide-react';
import { SUGGESTED_QUESTIONS } from '@/lib/suggested-questions';

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
  const { refresh } = useTableRefresh();
  const [resetting, setResetting] = useState(false);

  const resetState = async () => {
    setResetting(true);
    try {
      const res = await fetch('/api/reset-state', { method: 'POST', credentials: 'include' });
      if (res.ok) {
        refresh('example_data');
      }
    } catch {
      // Reset failed - no UI feedback
    } finally {
      setResetting(false);
    }
  };

  return (
    <header className="flex shrink-0 items-center justify-between gap-2 border-b bg-background px-3 py-2 min-h-[44px]">
      <div className="flex min-w-0 flex-1" />
      <div className="flex shrink-0 flex-wrap items-center justify-end gap-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={resetState}
          disabled={resetting}
          aria-label="Reset state"
          title="Reset demo state"
        >
          <RotateCcw className={`h-4 w-4 ${resetting ? 'animate-spin' : ''}`} />
        </Button>
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
        {sendMessage && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                aria-label="Suggested questions"
                title="Suggested questions"
              >
                <List className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              side="bottom"
              className="max-h-[min(50vh,400px)] min-w-[280px] max-w-md overflow-y-auto"
            >
              {SUGGESTED_QUESTIONS.map((q) => (
                <DropdownMenuItem
                  key={q}
                  className="cursor-pointer whitespace-normal py-2"
                  onSelect={() => {
                    sendMessage({
                      role: 'user',
                      parts: [{ type: 'text', text: q }],
                    });
                  }}
                >
                  {q}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
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
