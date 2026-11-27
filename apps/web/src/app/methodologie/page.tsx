import type { Metadata } from "next";
import { DocPage } from "@/components/DocPage";
import { fr } from "@/i18n/fr";

export const metadata: Metadata = { title: `${fr.nav.methodology} · ${fr.appName}` };

export default function MethodologyPage() {
  return <DocPage name="methodologie" />;
}
