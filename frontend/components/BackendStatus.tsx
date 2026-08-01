"use client";

import { useEffect, useState } from "react";

type Status = "checking" | "online" | "offline";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let cancelled = false;

    fetch(`${API_URL}/api/health`)
      .then((res) => {
        if (!cancelled) setStatus(res.ok ? "online" : "offline");
      })
      .catch(() => {
        if (!cancelled) setStatus("offline");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const dotClass =
    status === "online" ? "bg-emerald-400" : status === "offline" ? "bg-red-500" : "bg-slate-500";

  return (
    <span className="flex items-center gap-1.5 text-xs text-slate-400">
      <span className={`h-2 w-2 rounded-full ${dotClass}`} />
      API {status}
    </span>
  );
}
