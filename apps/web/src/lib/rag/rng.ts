import { randomBytes } from "node:crypto";

/** Réel uniforme de [0, 1) tiré par le générateur cryptographique (48 bits). */
export function secureRandom(): number {
  return randomBytes(6).readUIntBE(0, 6) / 2 ** 48;
}
