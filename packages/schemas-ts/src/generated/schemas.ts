/* Fichier généré par packages/schemas-ts/scripts/gen.mjs depuis schemas/. Ne pas éditer. */

export interface AllSchemas {
  chunk?: Chunk;
  election_config?: ElectionConfig;
  evidence?: Evidence;
  manifest?: Manifest;
  measures?: MeasuresFile;
  pca_model?: PcaModel;
  positions?: PositionsFile;
  retrieve_request?: RetrieveRequest;
  retrieve_response?: RetrieveResponse;
  review?: Review;
  statements?: StatementsFile;
}
/**
 * Extrait d'un document officiel du corpus, unité d'indexation et de citation du chat RAG (SPEC § 4.5). Produit par `pipeline chunk`, une ligne JSON par extrait.
 */
export interface Chunk {
  /**
   * 12 premiers caractères du sha256 du document, puis rang de l'extrait dans le document.
   */
  id: string;
  election_id: string;
  candidate_id: string;
  document_title: string;
  source_url: string;
  document_sha256: string;
  /**
   * Numéro de page du PDF (celui affiché par un lecteur PDF) où commence l'extrait ; 1 pour un document HTML ou Markdown.
   */
  page_number: number;
  page_end: number;
  /**
   * Titre de section du premier passage propre à l'extrait (hors recouvrement repris de l'extrait précédent) ; null si le document n'a pas encore de titre à cet endroit.
   */
  section_title: string | null;
  /**
   * Thème attribué à l'indexation (PLAN D16) ; null si non attribué ou ambigu.
   */
  theme: string | null;
  text: string;
  /**
   * Nombre de tokens (tokenizer XLM-RoBERTa, PLAN D17).
   */
  token_count: number;
  /**
   * Empreinte des documents (sha256), des paramètres de découpage, du tokenizer et du contenu des extraits (texte et métadonnées) : change dès qu'un extrait change.
   */
  corpus_version: string;
}
/**
 * Configuration d'une élection : axes, thèmes (dans l'ordre d'affichage), candidats, corpus officiel.
 */
export interface ElectionConfig {
  id: string;
  name: string;
  country: string;
  date_first_round: string;
  /**
   * Vrai pour une élection de démonstration aux candidats inventés.
   */
  fictional?: boolean;
  axes: {
    x: Axis;
    y: Axis;
  };
  quadrants: {
    tl: string;
    tr: string;
    bl: string;
    br: string;
  };
  /**
   * L'ordre du tableau est l'ordre d'affichage du questionnaire.
   *
   * @minItems 1
   */
  themes: Theme[];
  /**
   * @minItems 2
   */
  candidates: Candidate[];
  corpus: CorpusDocument[];
}
export interface Axis {
  label: string;
  /**
   * Libellé du pôle -10.
   */
  min_label: string;
  /**
   * Libellé du pôle +10.
   */
  max_label: string;
}
export interface Theme {
  id: string;
  label: string;
  /**
   * Courte description du périmètre du thème, utilisée pour classer les extraits du corpus (PLAN D16).
   */
  description?: string;
}
/**
 * Aucune coordonnée (x, y) ici : elles sont calculées, jamais saisies.
 */
export interface Candidate {
  id: string;
  name: string;
  party: string;
  color: string;
  photo?: string | null;
  program_url: string;
  blind_alias: string;
}
export interface CorpusDocument {
  candidate_id: string;
  document_title: string;
  type: "pdf" | "html" | "markdown";
  source_url: string;
  local_path: string;
  sha256: string;
  retrieved_at: string;
}
/**
 * Citation extraite d'un document officiel du corpus, justifiant une position ou une mesure.
 */
export interface Evidence {
  /**
   * Citation exacte (sous-chaîne du document).
   */
  quote: string;
  document_title: string;
  page?: number | null;
  chunk_id?: string | null;
}
/**
 * Sortie de pipeline build : versions et empreintes des fichiers servis au front.
 */
export interface Manifest {
  election_id: string;
  built_at: string;
  corpus_version: string;
  files: ManifestFile[];
}
export interface ManifestFile {
  path: string;
  sha256: string;
}
export interface MeasuresFile {
  election_id: string;
  measures: Measure[];
}
export interface Measure {
  id: string;
  candidate_id: string;
  theme: string;
  title: string;
  summary: string;
  costing: Costing;
  evidence: Evidence[];
  review: Review;
}
export interface Costing {
  status: "chiffre" | "partiel" | "intention";
  amount_eur?: number | null;
  period?: string | null;
  quote?: string | null;
}
/**
 * Décision de revue humaine. Seuls validated et corrected sont chargés par le front.
 */
export interface Review {
  status: "pending" | "validated" | "corrected" | "rejected";
  reviewer?: string | null;
  date?: string | null;
  note?: string | null;
}
/**
 * Chargements ACP précalculés par le pipeline (mode B). La projection reste calculée côté client.
 */
export interface PcaModel {
  election_id: string;
  /**
   * @minItems 2
   */
  statement_ids: string[];
  mean: number[];
  /**
   * Composantes 1 et 2, orientées selon les axes x et y du mode A (décision D3).
   *
   * @minItems 2
   * @maxItems 2
   */
  components: number[][];
  /**
   * @minItems 2
   * @maxItems 2
   */
  explained_variance_ratio: number[];
  /**
   * Facteurs tels que max |coord candidat| = 9 (décision D4).
   *
   * @minItems 2
   * @maxItems 2
   */
  scale: number[];
  /**
   * Affirmations les plus contributives par composante, pour l'interprétation des axes.
   *
   * @minItems 2
   * @maxItems 2
   */
  top_statements: string[][];
}
export interface PositionsFile {
  election_id: string;
  positions: Position[];
}
export interface Position {
  candidate_id: string;
  statement_id: string;
  /**
   * null = silence du programme.
   */
  value: number | null;
  confidence: "high" | "medium" | "low";
  evidence: Evidence[];
  proposed_by: string;
  review: Review;
}
/**
 * Requête POST /retrieve du service RAG (PLAN § 4.4). Ne jamais journaliser `question` (donnée d'opinion, RGPD art. 9).
 */
export interface RetrieveRequest {
  election_id: string;
  /**
   * Sans caractère de contrôle (PostgreSQL refuse U+0000) ; tabulation et retours à la ligne admis.
   */
  question: string;
  /**
   * Restreint la recherche à ces candidats ; absent ou null : tous les candidats indexés.
   *
   * @minItems 1
   */
  candidate_ids?: string[] | null;
  /**
   * Restreint aux extraits classés dans ce thème.
   */
  theme?: string | null;
  /**
   * Nombre d'extraits gardés par candidat après fusion RRF.
   */
  k?: number;
}
/**
 * Réponse de POST /retrieve : extraits par candidat, triés par score RRF décroissant (PLAN § 4.4). Candidats triés par identifiant : l'ordre affiché est tiré au sort par l'appelant.
 */
export interface RetrieveResponse {
  election_id: string;
  corpus_version: string;
  /**
   * Modèle d'embedding utilisé.
   */
  model: string;
  candidates: CandidateResults[];
}
export interface CandidateResults {
  candidate_id: string;
  chunks: RetrievedChunk[];
}
export interface RetrievedChunk {
  chunk: Chunk;
  /**
   * Score RRF : somme des 1 / (60 + rang).
   */
  score: number;
  semantic_rank: number | null;
  lexical_rank: number | null;
}
export interface StatementsFile {
  election_id: string;
  /**
   * @minItems 25
   * @maxItems 35
   */
  statements: Statement[];
}
export interface Statement {
  id: string;
  theme: string;
  text: string;
  axis: "x" | "y";
  /**
   * +1 si « d'accord » pousse vers +10 sur l'axe.
   */
  direction: -1 | 1;
  weight_in_axis: number;
}
