/** PRNG mulberry32 : déterministe, suffisant pour un ordre d'affichage (pas de cryptographie). */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Ordre aléatoire des candidats (Fisher-Yates seedé). La graine est tirée une fois par session
 * par l'appelant ; l'entrée n'est pas modifiée.
 */
export function shuffleCandidates<T>(ids: readonly T[], seed: number): T[] {
  const out = [...ids];
  const rand = mulberry32(seed);
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [out[i], out[j]] = [out[j]!, out[i]!];
  }
  return out;
}
