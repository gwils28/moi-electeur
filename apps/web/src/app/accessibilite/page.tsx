import type { Metadata } from "next";
import { DocPage } from "@/components/DocPage";
import { fr } from "@/i18n/fr";

export const metadata: Metadata = { title: `${fr.footer.accessibility} · ${fr.appName}` };

export default function AccessibilityPage() {
  return <DocPage name="accessibilite" />;
}
