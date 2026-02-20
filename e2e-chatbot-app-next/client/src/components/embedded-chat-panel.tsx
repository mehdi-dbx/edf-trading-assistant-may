import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Chat } from '@/components/chat';
import { SidebarHistory } from '@/components/sidebar-history';
import {
  Sheet,
  SheetContent,
  SheetTitle,
} from '@/components/ui/sheet';
import { useSession } from '@/contexts/SessionContext';
import { useChatData } from '@/hooks/useChatData';
import { generateUUID } from '@/lib/utils';
import type { LanguageModelUsage } from 'ai';
import type { LanguageModelV3Usage } from '@ai-sdk/provider';

function fromV3Usage(
  usage: LanguageModelV3Usage | null | undefined,
): LanguageModelUsage | undefined {
  if (!usage) return undefined;
  return {
    inputTokens: usage.inputTokens?.total,
    outputTokens: usage.outputTokens?.total,
    totalTokens:
      (usage.inputTokens?.total ?? 0) + (usage.outputTokens?.total ?? 0),
    inputTokenDetails: {
      noCacheTokens: usage.inputTokens?.noCache,
      cacheReadTokens: usage.inputTokens?.cacheRead,
      cacheWriteTokens: usage.inputTokens?.cacheWrite,
    },
    outputTokenDetails: {
      textTokens: usage.outputTokens?.text,
      reasoningTokens: usage.outputTokens?.reasoning,
    },
  };
}

const CHAT_PANEL_WIDTH = 525; // 420 + 25%

export function EmbeddedChatPanel({
  chatId,
  onNewChat,
}: {
  chatId: string;
  onNewChat: () => void;
}) {
  const { session } = useSession();
  const location = useLocation();
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [modelId, setModelId] = useState('chat-model');

  const isExistingChat = location.pathname.startsWith('/chat/');
  const { chatData, error } = useChatData(chatId, isExistingChat);

  useEffect(() => {
    const saved = localStorage.getItem('chat-model');
    if (saved) setModelId(saved);
  }, []);

  useEffect(() => {
    if (historyOpen && location.pathname.startsWith('/chat/')) {
      setHistoryOpen(false);
    }
  }, [historyOpen, location.pathname]);

  const handleClose = () => {
    setExpanded(false);
  };

  if (!session?.user) {
    return null;
  }

  const showLoading =
    isExistingChat && (error !== undefined || !chatData || chatData.chat.id !== chatId);
  const showError = isExistingChat && error !== undefined && !chatData;

  return (
    <>
      <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
        <SheetContent
          side="right"
          className="w-full sm:max-w-md"
          aria-describedby={undefined}
        >
          <SheetTitle className="sr-only">Chat history</SheetTitle>
          <div className="mt-4 flex flex-col gap-2 px-2">
            <h2 className="font-semibold text-foreground text-base">
              History
            </h2>
            <SidebarHistory
              user={session.user}
              searchQuery=""
            />
          </div>
        </SheetContent>
      </Sheet>

      <div
        className={expanded
          ? 'fixed inset-0 z-40 flex flex-col border-l bg-background'
          : 'flex h-full min-h-0 shrink-0 flex-col border-l bg-background overflow-hidden'}
        style={expanded ? undefined : { width: CHAT_PANEL_WIDTH }}
      >
        {showError && (
          <div className="flex flex-1 items-center justify-center p-4 text-center text-muted-foreground text-sm">
            {error}
          </div>
        )}
        {showLoading && !showError && (
          <div className="flex flex-1 items-center justify-center p-4 text-muted-foreground text-sm">
            Loading chat...
          </div>
        )}
        {!showLoading && !showError && (
          <Chat
            key={chatId}
            id={chatId}
            initialMessages={
              isExistingChat && chatData
                ? chatData.messages
                : []
            }
            initialChatModel={modelId}
            initialVisibilityType={
              isExistingChat && chatData
                ? chatData.chat.visibility
                : 'private'
            }
            isReadonly={false}
            session={session}
            initialLastContext={
              isExistingChat && chatData
                ? fromV3Usage(chatData.chat.lastContext)
                : undefined
            }
            panelHeaderProps={{
              onNewChat,
              onHistory: () => setHistoryOpen(true),
              expanded,
              onExpand: () => setExpanded((e) => !e),
              onClose: handleClose,
            }}
          />
        )}
      </div>
    </>
  );
}
