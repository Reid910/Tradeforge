"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import FormField, { inputClass } from "@/components/FormField";
import { api, ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");

  const magicLinkMutation = useMutation({
    mutationFn: () => api.requestMagicLink(email),
  });

  const guestMutation = useMutation({
    mutationFn: () => api.guestLogin(),
    onSuccess: (user) => {
      queryClient.setQueryData(["me"], user);
      router.push("/");
    },
  });

  const sentLink = magicLinkMutation.data;

  return (
    <div className="flex h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-lg border border-forge-border bg-forge-panel p-6">
        <h1 className="text-lg font-semibold text-slate-100">Sign in to Tradeforge</h1>
        <p className="mt-1 text-xs text-slate-500">No password needed — we&apos;ll email you a sign-in link.</p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            magicLinkMutation.mutate();
          }}
          className="mt-4 space-y-3"
        >
          <FormField label="Email">
            <input
              className={inputClass}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </FormField>

          {magicLinkMutation.isError && (
            <p className="text-xs text-red-400">
              {magicLinkMutation.error instanceof ApiError ? magicLinkMutation.error.message : "Something went wrong"}
            </p>
          )}

          <button
            type="submit"
            disabled={magicLinkMutation.isPending || !!sentLink}
            className="w-full rounded-md bg-forge-accent py-2 text-sm font-medium text-forge-bg disabled:opacity-50"
          >
            {magicLinkMutation.isPending ? "Sending…" : "Send sign-in link"}
          </button>
        </form>

        {sentLink && (
          <div className="mt-4 rounded-md border border-forge-border bg-forge-bg p-3 text-xs">
            <p className="text-slate-300">{sentLink.message}</p>
            {sentLink.dev_magic_link && (
              <a href={sentLink.dev_magic_link} className="mt-2 block break-all text-forge-accent hover:underline">
                {sentLink.dev_magic_link}
              </a>
            )}
          </div>
        )}

        <div className="my-4 flex items-center gap-3 text-[10px] uppercase tracking-wide text-slate-600">
          <span className="h-px flex-1 bg-forge-border" />
          or
          <span className="h-px flex-1 bg-forge-border" />
        </div>

        <button
          onClick={() => guestMutation.mutate()}
          disabled={guestMutation.isPending}
          className="w-full rounded-md border border-forge-border py-2 text-sm font-medium text-slate-300 hover:border-forge-accent/60 hover:text-slate-100 disabled:opacity-50"
        >
          {guestMutation.isPending ? "Creating guest session…" : "Continue as guest"}
        </button>
        {guestMutation.isError && <p className="mt-2 text-xs text-red-400">Couldn&apos;t start a guest session</p>}
      </div>
    </div>
  );
}
