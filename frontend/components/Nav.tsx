"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Map" },
  { href: "/factory", label: "Factory" },
  { href: "/inventory", label: "Inventory" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-1">
      {LINKS.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`rounded-md px-2 py-1 text-xs font-medium ${
              active
                ? "bg-forge-border/60 text-slate-100"
                : "text-slate-300 hover:bg-forge-border/50 hover:text-slate-100"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
