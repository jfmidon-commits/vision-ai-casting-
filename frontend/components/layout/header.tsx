"use client";

import { Bell, Brain, Search, User } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";

export function Header() {
  const user = useAuthStore((state) => state.user);

  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-4 sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex items-center gap-2 md:hidden">
          <Brain className="h-5 w-5 text-primary" />
          <span className="font-bold">Vision AI</span>
        </div>
        <div className="relative hidden sm:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Buscar..."
            className="h-9 w-52 rounded-md border bg-background pl-9 pr-4 text-sm outline-none focus:ring-2 focus:ring-primary lg:w-64"
          />
        </div>
      </div>
      <div className="flex items-center gap-2 sm:gap-4">
        <button className="relative rounded-full p-2 hover:bg-accent" aria-label="Notificações">
          <Bell className="h-5 w-5" />
          <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-destructive" />
        </button>
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <User className="h-4 w-4" />
          </div>
          <span className="hidden max-w-32 truncate text-sm font-medium sm:block">{user?.name || "Usuário"}</span>
        </div>
      </div>
    </header>
  );
}
