"use client";

import { useState } from "react";
import { Bell, Search, User } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";

export function Header() {
  const user = useAuthStore((state) => state.user);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-4 sm:px-6">
      <div className="flex min-w-0 items-center gap-4">
        <div className="relative hidden sm:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Buscar..."
            className="h-9 w-64 rounded-md border bg-background pl-9 pr-4 text-sm outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
      </div>
      <div className="flex items-center gap-3 sm:gap-4">
        <div className="relative">
          <button
            type="button"
            aria-label="Notificações"
            aria-expanded={notificationsOpen}
            onClick={() => setNotificationsOpen((open) => !open)}
            className="relative rounded-full p-2 hover:bg-accent focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <Bell className="h-5 w-5" />
          </button>

          {notificationsOpen && (
            <div className="absolute right-0 top-12 z-50 w-[min(20rem,calc(100vw-2rem))] rounded-lg border bg-popover p-4 text-popover-foreground shadow-lg">
              <p className="text-sm font-semibold">Notificações</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Você não tem novas notificações no momento.
              </p>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <User className="h-4 w-4" />
          </div>
          <span className="hidden text-sm font-medium sm:inline">{user?.name || "Usuário"}</span>
        </div>
      </div>
    </header>
  );
}
