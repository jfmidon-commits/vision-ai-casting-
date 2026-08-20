"use client";

import Link from "next/link";
import { Brain, Camera, LayoutDashboard, Users } from "lucide-react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";

const mobileNavigation = [
  { href: "/dashboard", label: "Início", icon: LayoutDashboard },
  { href: "/profiles", label: "Perfis", icon: Users },
  { href: "/photoshoots", label: "Ensaios", icon: Camera },
  { href: "/analyses", label: "Análises", icon: Brain },
];

export function DashboardShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-background">
      <div className="hidden md:block">
        <Sidebar />
      </div>
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto p-4 pb-24 sm:p-6 sm:pb-24 md:pb-6">{children}</main>
      </div>
      <nav className="fixed inset-x-0 bottom-0 z-50 grid grid-cols-4 border-t bg-card/95 px-2 py-2 backdrop-blur md:hidden">
        {mobileNavigation.map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href} className="flex flex-col items-center gap-1 py-1 text-[11px] text-muted-foreground">
              <Icon className="h-5 w-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
