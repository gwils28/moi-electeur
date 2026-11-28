import type { ReactNode } from "react";
import { PositionsTabs } from "@/components/PositionsTabs";

/** Positions : tableau complet et comparateur, réunis sous des sous-onglets (PLAN D55). */
export default function PositionsLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <div className="mx-auto max-w-6xl px-4 pt-4 sm:px-6">
        <PositionsTabs />
      </div>
      {children}
    </>
  );
}
