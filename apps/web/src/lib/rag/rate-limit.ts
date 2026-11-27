import { createHmac, randomBytes } from "node:crypto";

/**
 * Limite de débit par IP, fenêtre glissante, compteur en mémoire (SPEC § 10). L'IP n'est jamais
 * conservée en clair : la clé est un HMAC avec un sel aléatoire propre au processus, perdu au
 * redémarrage (aucune correspondance IP ↔ clé n'est reconstituable).
 */
export class RateLimiter {
  private readonly limit: number;
  private readonly windowMs: number;
  private readonly now: () => number;
  private readonly salt = randomBytes(32);
  private readonly hits = new Map<string, number[]>();
  private lastPrune = 0;

  /** Nombre maximal de clés suivies : au-delà, purge forcée puis éviction des plus anciennes. */
  private readonly maxKeys: number;

  constructor(opts: { limit: number; windowMs: number; now?: () => number; maxKeys?: number }) {
    this.maxKeys = opts.maxKeys ?? 50_000;
    this.limit = opts.limit;
    this.windowMs = opts.windowMs;
    this.now = opts.now ?? Date.now;
  }

  hit(ip: string): { ok: boolean; retryAfterS: number } {
    const t = this.now();
    this.prune(t);
    const key = createHmac("sha256", this.salt).update(ip).digest("base64url");
    const recent = (this.hits.get(key) ?? []).filter((h) => h > t - this.windowMs);
    if (recent.length >= this.limit) {
      this.hits.set(key, recent);
      const retryAfterS = Math.max(1, Math.ceil((recent[0]! + this.windowMs - t) / 1000));
      return { ok: false, retryAfterS };
    }
    recent.push(t);
    this.hits.delete(key);
    this.hits.set(key, recent); // ordre d'insertion = activité la plus récente en dernier
    if (this.hits.size > this.maxKeys) {
      this.lastPrune = 0;
      this.prune(t);
      for (const k of this.hits.keys()) {
        if (this.hits.size <= this.maxKeys) break;
        this.hits.delete(k);
      }
    }
    return { ok: true, retryAfterS: 0 };
  }

  /** Clés actuellement suivies (empreintes, jamais d'IP). */
  keys(): string[] {
    return [...this.hits.keys()];
  }

  private prune(t: number): void {
    if (t - this.lastPrune < this.windowMs) return;
    this.lastPrune = t;
    for (const [key, list] of this.hits) {
      if (list.every((h) => h <= t - this.windowMs)) this.hits.delete(key);
    }
  }
}

/**
 * Adresse du client. Derrière le proxy (Caddy en prod, M5), c'est la dernière adresse de
 * `X-Forwarded-For` (celle ajoutée par notre proxy ; les précédentes sont fournies par le client
 * et falsifiables). Sans en-tête (dev, accès direct), toutes les requêtes partagent une clé.
 * Prérequis de sécurité : le service web n'est jamais exposé sans ce proxy (port lié à
 * 127.0.0.1 en dev, réseau interne en prod), sinon l'en-tête est entièrement choisi par le client.
 */
export function clientIp(req: Request): string {
  const xff = req.headers.get("x-forwarded-for");
  if (xff) {
    const last = xff.split(",").at(-1)!.trim();
    if (last) return last;
  }
  return req.headers.get("x-real-ip")?.trim() || "inconnue";
}
