"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const [authReady, setAuthReady] = useState(false);

  useEffect(() => {
    let active = true;

    const validateSession = async () => {
      if (!token && !refreshToken) {
        router.replace("/login");
        return;
      }

      try {
        await authApi.me();
        if (active) setAuthReady(true);
      } catch {
        if (active) router.replace("/login");
      }
    };

    validateSession();

    return () => {
      active = false;
    };
  }, [refreshToken, router, token]);

  if (!authReady) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-sm text-muted-foreground">
        Validando sessão...
      </div>
    );
  }

  return (
    <div className="flex min-h-screen w-full bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto p-4 pb-24 md:p-6 md:pb-6">{children}</main>
      </div>
    </div>
  );
}
