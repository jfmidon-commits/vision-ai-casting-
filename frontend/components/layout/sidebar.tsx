"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Users,
  Camera,
  Brain,
  FileText,
  Settings,
  LogOut,
} from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Perfis", href: "/profiles", icon: Users },
  { name: "Ensaios", href: "/photoshoots", icon: Camera },
  { name: "Análises", href: "/analyses", icon: Brain },
  { name: "Relatórios", href: "/reports", icon: FileText },
  { name: "Configurações", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const logout = useAuthStore((state) => state.logout);

  const renderItems = (mobile = false) =>
    navigation.map((item) => {
      const Icon = item.icon;
      const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
      return (
        <Link
          key={item.name}
          href={item.href}
          className={cn(
            mobile
              ? "flex min-w-[72px] flex-col items-center justify-center gap-1 rounded-lg px-2 py-2 text-[11px] font-medium"
              : "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
            isActive
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          )}
        >
          <Icon className={mobile ? "h-5 w-5" : "h-5 w-5"} />
          {item.name}
        </Link>
      );
    });

  return (
    <>
      <aside className="hidden h-full w-64 shrink-0 flex-col border-r bg-card md:flex">
        <div className="flex h-16 items-center border-b px-6">
          <Link href="/dashboard" className="flex items-center gap-2">
            <Brain className="h-6 w-6 text-primary" />
            <span className="text-lg font-bold">Vision AI</span>
          </Link>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">{renderItems(false)}</nav>
        <div className="border-t p-3">
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            <LogOut className="h-5 w-5" />
            Sair
          </button>
        </div>
      </aside>

      <nav className="fixed inset-x-0 bottom-0 z-50 flex overflow-x-auto border-t bg-card/95 px-2 py-2 backdrop-blur md:hidden">
        <div className="flex min-w-max gap-1">{renderItems(true)}</div>
      </nav>
    </>
  );
}
