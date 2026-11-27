/**
 * Plafond de dépense quotidien du chat (`DAILY_BUDGET_USD`, SPEC § 10). Compteur en mémoire,
 * remis à zéro à minuit UTC (et au redémarrage du serveur : limite connue, consignée).
 *
 * Chaque requête réserve d'abord son coût maximal (entrée estimée par excès, `max_tokens` en
 * sortie) : des requêtes simultanées ne peuvent pas dépasser ensemble le plafond. La réservation
 * est ensuite remplacée par le coût réel calculé depuis l'`usage` renvoyé par l'API ; si le coût
 * réel est inconnu (erreur en cours de flux), le coût maximal reste imputé.
 */
export class DailyBudget {
  private readonly limitUsd: number;
  private readonly now: () => number;
  private day = "";
  private spentUsd = 0;
  private reservedUsd = 0;

  constructor(opts: { limitUsd: number; now?: () => number }) {
    this.limitUsd = opts.limitUsd;
    this.now = opts.now ?? Date.now;
  }

  private roll(): void {
    const day = new Date(this.now()).toISOString().slice(0, 10);
    if (day !== this.day) {
      this.day = day;
      this.spentUsd = 0;
      this.reservedUsd = 0;
    }
  }

  /** Dépense constatée du jour (hors réservations en cours). */
  spent(): number {
    this.roll();
    return this.spentUsd;
  }

  exhausted(): boolean {
    this.roll();
    return this.spentUsd + this.reservedUsd >= this.limitUsd;
  }

  /** Réserve `maxUsd` si le reste du budget le permet ; renvoie une fonction de règlement. */
  reserve(maxUsd: number): ((actualUsd: number | null) => void) | null {
    this.roll();
    if (this.spentUsd + this.reservedUsd + maxUsd > this.limitUsd) return null;
    const day = this.day;
    this.reservedUsd += maxUsd;
    let settled = false;
    return (actualUsd) => {
      if (settled) return;
      settled = true;
      this.roll();
      // Jour écoulé pendant la requête : la réservation a disparu avec la remise à zéro, la
      // dépense est imputée au nouveau jour (elle n'échappe ainsi à aucun plafond).
      if (this.day === day) this.reservedUsd -= maxUsd;
      this.spentUsd += actualUsd ?? maxUsd;
    };
  }

  /** Impute directement une dépense (tests, reprise manuelle). */
  record(usd: number): void {
    this.roll();
    this.spentUsd += usd;
  }
}
