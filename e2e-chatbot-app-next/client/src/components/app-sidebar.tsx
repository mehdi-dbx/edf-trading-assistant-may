import { useState } from 'react';

import { SidebarHistory } from '@/components/sidebar-history';
import {
  Sidebar,
  SidebarContent,
} from '@/components/ui/sidebar';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';
import type { ClientSession } from '@chat-template/auth';

export function AppSidebar({
  user,
  preferredUsername: _preferredUsername,
}: {
  user: ClientSession['user'] | undefined;
  preferredUsername: string | null;
}) {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <Sidebar className="group-data-[side=left]:border-r-0">
      <SidebarContent className="gap-2 px-2 pt-2">
        <h2 className="px-2 font-semibold text-sidebar-foreground text-base">
          History
        </h2>
        <div className="relative px-2">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search your chats here"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 pl-8 bg-background text-sm"
          />
        </div>
        <SidebarHistory user={user} searchQuery={searchQuery} />
      </SidebarContent>
    </Sidebar>
  );
}
