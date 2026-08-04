"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import BackendStatus from "@/components/BackendStatus";
import Nav from "@/components/Nav";
import NodeMap from "@/components/NodeMap";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";

export default function Home() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isLoading, isError } = useAuth();

  useEffect(() => {
    if (!isLoading && (isError || !user)) {
      router.replace("/login");
    }
  }, [isLoading, isError, user, router]);

  if (isLoading || !user) {
    return <div className="flex h-screen items-center justify-center text-sm text-slate-500">Loading…</div>;
  }

  const handleLogout = async () => {
    await api.logout();
    queryClient.clear();
    router.replace("/login");
  };

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-forge-border bg-forge-panel px-4 py-3">
        <div className="flex items-center gap-4">
          <h1 className="text-sm font-semibold tracking-wide text-slate-100">
            TRADEFORGE <span className="text-slate-500">/ mining map</span>
          </h1>
          <Nav />
        </div>
        <div className="flex items-center gap-4">
          <BackendStatus />
          <span className="text-xs text-slate-400">
            {user.username}
            {user.is_guest && <span className="ml-1 text-slate-600">(guest)</span>}
          </span>
          <button onClick={handleLogout} className="text-xs text-slate-400 hover:text-slate-200">
            Log out
          </button>
        </div>
      </header>
      <main className="flex-1">
        <NodeMap />
      </main>
    </div>
  );
}
