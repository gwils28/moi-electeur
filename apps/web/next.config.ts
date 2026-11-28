import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Le moteur est livré en sources TS, compilé dans le bundle client (SPEC § 15.5).
  transpilePackages: ["@moi-electeur/engine"],
  poweredByHeader: false,
  // Sinon `next dev` lancé par un agent écrit apps/web/AGENTS.md (texte de Next, avec des tirets
  // cadratins refusés par check:hygiene). Les consignes de l'agent sont dans CLAUDE.md.
  agentRules: false,
  // L'interrogatoire est la page d'accueil (PLAN D54, D56) : anciennes adresses conservées.
  async redirects() {
    return [
      { source: "/explorer", destination: "/", permanent: true },
      { source: "/interrogatoire", destination: "/", permanent: true },
      // Le comparateur est un sous-onglet de Positions (PLAN D55).
      { source: "/comparateur", destination: "/positions/comparateur", permanent: true },
    ];
  },
};

export default nextConfig;
