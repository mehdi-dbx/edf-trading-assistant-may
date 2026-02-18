import { useNavigate } from 'react-router-dom';
import { useWindowSize } from 'usehooks-ts';

import { SidebarToggle } from '@/components/sidebar-toggle';
import { Button } from '@/components/ui/button';
import { useSidebar } from './ui/sidebar';
import { PlusIcon, CloudOffIcon } from 'lucide-react';
import { useConfig } from '@/hooks/use-config';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

export function ChatHeader() {
  const navigate = useNavigate();
  const { open } = useSidebar();
  const { chatHistoryEnabled } = useConfig();

  const { width: windowWidth } = useWindowSize();

  const amadeusLogoUrl =
    'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Amadeus_Organization_logo_2024.svg/1280px-Amadeus_Organization_logo_2024.svg.png';

  return (
    <header className="sticky top-0 z-10 flex flex-col border-b bg-background">
      <div className="flex items-center gap-3 px-3 py-2">
        <img
          src={amadeusLogoUrl}
          alt="Amadeus"
          className="h-8 w-auto object-contain"
        />
        <h1 className="text-lg font-semibold tracking-tight text-foreground">
          Amadeus GARV Airops Assistant
        </h1>
      </div>
      <div className="flex items-center gap-2 bg-background px-2 py-1.5 md:px-2">
        <SidebarToggle />

        {(!open || windowWidth < 768) && (
          <Button
            variant="outline"
            className="order-2 ml-auto h-8 px-2 md:order-1 md:ml-0 md:h-fit md:px-2"
            onClick={() => {
              navigate('/');
            }}
          >
            <PlusIcon />
            <span className="md:sr-only">New Chat</span>
          </Button>
        )}

        {!chatHistoryEnabled && (
          <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="ml-auto flex items-center gap-1.5 rounded-full bg-muted px-2 py-1 text-muted-foreground text-xs">
                <CloudOffIcon className="h-3 w-3" />
                <span className="hidden sm:inline">Ephemeral</span>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>Chat history disabled - conversations are not saved</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
      </div>
    </header>
  );
}
