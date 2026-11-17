/**
 * Moteur de calcul de Moi Électeur : fonctions pures, zéro dépendance, zéro I/O.
 * Les réponses, poids et coordonnées de l'utilisateur ne quittent jamais le navigateur.
 */
export const ENGINE_VERSION = "0.1.0";

export type * from "./types";
export { proximity } from "./proximity";
export { projectA, projectB } from "./projection";
export { compare, filterByTheme } from "./compare";
export { candidateAnswers, LOADED_STATUSES } from "./positions";
export { shuffleCandidates } from "./shuffle";
export { encodeAnswers, decodeAnswers } from "./code";
