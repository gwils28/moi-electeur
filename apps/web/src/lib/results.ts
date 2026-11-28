/**
 * Ordre des résultats de la boussole (PLAN D59) : score ajusté de proximité décroissant, avec
 * les réponses de l'utilisateur ; égalités départagées par l'ordre aléatoire de session (tri
 * stable sur l'ordre reçu) ; candidats sans affirmation commune en dernier.
 */
export function orderByAdjusted<T extends { prox: { adjusted: number } | null }>(
  rows: readonly T[],
): T[] {
  return [...rows].sort((a, b) => {
    if (a.prox === null || b.prox === null) {
      return (a.prox === null ? 1 : 0) - (b.prox === null ? 1 : 0);
    }
    return b.prox.adjusted - a.prox.adjusted;
  });
}
