import type { HTMLAttributes, ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

const ICONS: Record<NoticeVariant, IconName> = { info: "info", warn: "alert", error: "alert" };

export type NoticeVariant = "info" | "warn" | "error";

/**
 * Encart unique (information, attention, erreur) : icône décorative + titre facultatif + texte.
 * Le rôle ARIA (`status`, `alert`) et les `data-testid` sont portés par l'appelant via `rest`.
 */
export function Notice({
  variant = "info",
  title,
  children,
  className = "",
  ...rest
}: {
  variant?: NoticeVariant;
  title?: ReactNode;
  children?: ReactNode;
  className?: string;
} & Omit<HTMLAttributes<HTMLDivElement>, "title">) {
  return (
    <div className={`notice notice-${variant} ${className}`} {...rest}>
      <span className="mt-0.5">
        <Icon name={ICONS[variant]} />
      </span>
      <div className="min-w-0 space-y-1">
        {title && <p className="font-semibold">{title}</p>}
        {children}
      </div>
    </div>
  );
}
