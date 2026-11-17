/** Graine d'ordre aléatoire, tirée une fois par chargement de page, jamais persistée. */
export function sessionSeed(): number {
  const buf = new Uint32Array(1);
  globalThis.crypto.getRandomValues(buf);
  return buf[0]!;
}

const STORAGE_KEY = "moi-electeur:reponses";

/** Sauvegarde locale explicite (désactivée par défaut, SPEC § 5.1). Jamais envoyée au réseau. */
export function saveLocal(code: string | null): void {
  try {
    if (code === null) localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, code);
  } catch {
    // stockage indisponible (navigation privée) : on ignore
  }
}

export function loadLocal(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}
