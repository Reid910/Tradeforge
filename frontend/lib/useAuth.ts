"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useAuth() {
  const query = useQuery({ queryKey: ["me"], queryFn: api.me, retry: false });
  return {
    user: query.data ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
