export const inputClass =
  "w-full rounded-md border border-forge-border bg-forge-bg px-3 py-2 text-sm text-slate-100 outline-none focus:border-forge-accent";

export default function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-xs text-slate-400">
      {label}
      <div className="mt-1">{children}</div>
    </label>
  );
}
