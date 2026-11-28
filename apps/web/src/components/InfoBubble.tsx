"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Icon } from "./Icon";

/**
 * Bulle d'information : bouton (i) qui ouvre une explication courte. Bouton nommé par `label`
 * (texte réservé aux lecteurs d'écran, aucun texte visible), `aria-expanded`, Échap ou clic à
 * l'extérieur pour fermer, focus rendu au bouton.
 */
export function InfoBubble({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const root = useRef<HTMLSpanElement>(null);
  const button = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    const onClick = (e: MouseEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  return (
    <span ref={root} className="relative inline-flex align-middle">
      <button
        ref={button}
        type="button"
        className="inline-flex size-7 items-center justify-center rounded-full text-muted hover:bg-surface-2 hover:text-fg"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
      >
        <Icon name="info" size={18} />
        <span className="sr-only">{label}</span>
      </button>
      {open && (
        <span
          id={id}
          role="note"
          className="card absolute top-8 left-0 z-30 block w-[min(22rem,80vw)] space-y-2 text-left text-sm font-normal normal-case shadow-pop"
        >
          {children}
        </span>
      )}
    </span>
  );
}
