"use client";

import { Suspense, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";

function ConfirmContent() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const attempted = useRef(false);

  const mutation = useMutation({
    mutationFn: (t: string) => api.confirmMagicLink(t),
    onSuccess: (user) => {
      queryClient.setQueryData(["me"], user);
      router.push("/");
    },
  });

  useEffect(() => {
    if (token && !attempted.current) {
      attempted.current = true;
      mutation.mutate(token);
    }
  }, [token, mutation]);

  return (
    <div className="flex h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-lg border border-forge-border bg-forge-panel p-6 text-center text-sm">
        {!token && <p className="text-red-400">No sign-in token found in this link.</p>}
        {token && mutation.isPending && <p className="text-slate-400">Confirming sign-in…</p>}
        {token && mutation.isError && (
          <>
            <p className="text-red-400">
              {mutation.error instanceof ApiError ? mutation.error.message : "This link is invalid or expired."}
            </p>
            <Link href="/login" className="mt-3 inline-block text-forge-accent hover:underline">
              Back to sign in
            </Link>
          </>
        )}
      </div>
    </div>
  );
}

export default function ConfirmPage() {
  return (
    <Suspense
      fallback={<div className="flex h-screen items-center justify-center text-sm text-slate-500">Loading…</div>}
    >
      <ConfirmContent />
    </Suspense>
  );
}
