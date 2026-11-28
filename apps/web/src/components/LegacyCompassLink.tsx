"use client";

import { useEffect } from "react";

/**
 * Avant PLAN D56, la boussole était à l'accueil : ses liens de partage (`/#r=…`) y pointent
 * encore. Le fragment ne part jamais au serveur, d'où ce renvoi côté navigateur vers la boussole,
 * fragment conservé (les réponses restent dans le navigateur).
 */
export function LegacyCompassLink() {
  useEffect(() => {
    if (window.location.hash.startsWith("#r=")) {
      window.location.replace(`/boussole${window.location.hash}`);
    }
  }, []);
  return null;
}
