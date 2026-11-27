/* Fichier généré par packages/schemas-ts/scripts/gen.mjs depuis schemas/. Ne pas éditer. */

/**
 * Événement du flux SSE de POST /api/ask (PLAN § 4.5). Chaque événement SSE porte `event: <type>` et `data: <JSON conforme à ce schéma>`. Ordre : un `meta`, puis des `delta` et `citation`, puis un `done` ou un `error`.
 */
export type AskEvent =
  AskMetaEvent | AskDeltaEvent | AskCitationEvent | AskDoneEvent | AskErrorEvent;

export interface AllSchemas {
  ask_event?: AskEvent;
  ask_request?: AskRequest;
  chunk?: Chunk;
  election_config?: ElectionConfig;
  evidence?: Evidence;
  manifest?: Manifest;
  measure_extraction?: MeasureExtraction;
  measures?: MeasuresFile;
  pca_model?: PcaModel;
  position_extraction?: PositionExtraction;
  positions?: PositionsFile;
  proposal?: Proposal;
  retrieve_request?: RetrieveRequest;
  retrieve_response?: RetrieveResponse;
  review?: Review;
  statements?: StatementsFile;
}
export interface AskMetaEvent {
  type: "meta";
  election_id: string;
  corpus_version: string;
  prompt_version: string;
  /**
   * Modèle Claude qui a produit la réponse.
   */
  model: string;
  /**
   * Mode demandé (AskRequest.mode), qui a déterminé le modèle.
   */
  mode: "rapide" | "approfondi";
  /**
   * Réponse re-streamée depuis le cache mémoire (SPEC § 6.2 bis).
   */
  cached: boolean;
  /**
   * Ordre de présentation tiré au sort côté serveur ; le jeton {{cN}} désigne candidates[N-1].
   */
  candidates: AskCandidate[];
}
export interface AskCandidate {
  token: string;
  candidate_id: string;
  /**
   * Faux si aucun extrait n'a été trouvé pour ce candidat (filtre de thème).
   */
  has_excerpts: boolean;
}
export interface AskDeltaEvent {
  type: "delta";
  /**
   * Index du bloc de texte de la réponse.
   */
  block: number;
  text: string;
}
export interface AskCitationEvent {
  type: "citation";
  /**
   * Bloc de texte (événements `delta`) appuyé par cette citation.
   */
  block: number;
  /**
   * Vrai si `cited_text` est une sous-chaîne (espaces normalisés) de l'extrait renvoyé par /retrieve ; sinon la citation est « non vérifiée ».
   */
  verified: boolean;
  cited_text: string;
  chunk_id: string | null;
  candidate_id: string | null;
  document_title: string | null;
  source_url: string | null;
  page_number: number | null;
  page_end: number | null;
}
export interface AskDoneEvent {
  type: "done";
  /**
   * `end_turn` attendu ; `max_tokens` : réponse tronquée ; `refusal` : refus du modèle.
   */
  stop_reason: string | null;
  unverified_citations: number;
  /**
   * Formulations de classement repérées dans la réponse complète (liste prompts/forbidden_words.json) : signalées, jamais réécrites.
   */
  neutrality_flags: string[];
}
export interface AskErrorEvent {
  type: "error";
  /**
   * Erreur survenue après le début du flux.
   */
  code: "llm_unavailable" | "llm_error" | "internal";
  message: string;
}
/**
 * Corps de POST /api/ask (PLAN § 4.5). Ne jamais journaliser `question` ni `history` (donnée d'opinion, RGPD art. 9).
 */
export interface AskRequest {
  election_id: string;
  /**
   * Sans caractère de contrôle ; tabulation et retours à la ligne admis.
   */
  question: string;
  /**
   * Restreint la réponse à ces candidats ; absent ou null : tous les candidats indexés.
   *
   * @minItems 1
   * @maxItems 30
   */
  candidate_ids?: string[] | null;
  /**
   * Modèle choisi par l'utilisateur : « rapide » (modèle économique, défaut) ou « approfondi » (modèle avec réflexion, plus lent et plus coûteux, plafonné à part). Les deux répondent sur les mêmes extraits.
   */
  mode?: "rapide" | "approfondi";
  /**
   * Restreint aux extraits classés dans ce thème.
   */
  theme?: string | null;
  /**
   * Tours précédents de la conversation, conservés côté client uniquement (SPEC § 6.2). Le cache ne s'applique qu'à une requête sans historique.
   *
   * @maxItems 3
   */
  history?: AskTurn[];
}
export interface AskTurn {
  /**
   * Sans caractère de contrôle ; tabulation et retours à la ligne admis.
   */
  question: string;
  /**
   * Réponse telle que reçue, avec les jetons {{cN}} (jamais les noms affichés).
   */
  answer: string;
  /**
   * Identifiants des candidats dans l'ordre des jetons de cette réponse : candidates[0] correspond à {{c1}} (événement `meta` reçu).
   *
   * @minItems 1
   * @maxItems 30
   */
  candidates: string[];
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
/**
 * Sortie structurée demandée au modèle pour un couple (candidat, thème), PLAN D26. Compatible avec output_config.format : le nombre de mesures et les montants sont vérifiés par le pipeline.
 */
export interface MeasureExtraction {
  measures: ExtractedMeasure[];
}
export interface ExtractedMeasure {
  title: string;
  summary: string;
  costing: ExtractedCosting;
  quotes: ExtractedQuote[];
}
export interface ExtractedCosting {
  status: "chiffre" | "partiel" | "intention";
  amount_eur: number | null;
  period: string | null;
  quote: string | null;
}
export interface ExtractedQuote {
  /**
   * Numéro de l'extrait (1 = premier).
   */
  extrait: number;
  /**
   * Passage recopié mot pour mot.
   */
  text: string;
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
  proposed?: ProposedMeasure;
  review: Review;
}
export interface Costing {
  status: "chiffre" | "partiel" | "intention";
  amount_eur?: number | null;
  period?: string | null;
  quote?: string | null;
}
/**
 * Contenu proposé par l'extraction, conservé quand la revue le corrige (statut corrected seulement).
 */
export interface ProposedMeasure {
  title?: string;
  summary?: string;
  costing?: Costing;
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
/**
 * Sortie structurée demandée au modèle pour un couple (candidat, affirmation), PLAN D24-D25. Compatible avec output_config.format : aucune contrainte numérique ni de longueur (vérifiées par le pipeline).
 */
export interface PositionExtraction {
  /**
   * Accord des extraits avec l'affirmation (-2 à +2) ; null si les extraits ne traitent pas le sujet.
   */
  value: (-2 | -1 | 0 | 1 | 2) | null;
  confidence: "high" | "medium" | "low";
  /**
   * Passages exacts qui justifient la valeur ; au moins un si la valeur n'est pas null.
   */
  quotes: ExtractedQuote1[];
  /**
   * Une ou deux phrases neutres pour la personne qui relit.
   */
  rationale: string;
}
export interface ExtractedQuote1 {
  /**
   * Numéro de l'extrait (1 = premier).
   */
  extrait: number;
  /**
   * Passage recopié mot pour mot.
   */
  text: string;
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
  /**
   * Valeur proposée par l'extraction, conservée quand la revue la corrige (statut corrected seulement).
   */
  proposed_value?: number | null;
  review: Review;
}
/**
 * Une ligne de proposals/{positions,measures}.jsonl (PLAN D29) : requête, sortie du modèle, vérifications et coût. Aucun texte d'extrait n'y est copié (seulement les identifiants et les citations).
 */
export interface Proposal {
  kind: "position" | "measure";
  custom_id: string;
  election_id: string;
  candidate_id: string;
  /**
   * Affirmation (position) ou thème (mesure).
   */
  target: string;
  model: string;
  prompt_version: number;
  mode: "direct" | "batch";
  batch_id: string | null;
  corpus_version: string | null;
  /**
   * Extraits fournis, dans l'ordre (extrait 1 = premier).
   */
  chunk_ids: string[];
  /**
   * ok : sortie exploitable ; invalid : sortie conforme mais refusée par les vérifications ; error : pas de sortie exploitable (refus, troncature, erreur), redemandée au prochain lancement.
   */
  status: "ok" | "invalid" | "error";
  stop_reason: string | null;
  /**
   * Sortie du modèle (PositionExtraction ou MeasureExtraction).
   */
  output: {} | null;
  error: string | null;
  flags: (
    | "citation_non_retrouvee"
    | "extrait_inconnu"
    | "valeur_sans_citation"
    | "confiance_faible"
    | "trop_de_mesures"
    | "mesure_sans_citation"
    | "montant_non_retrouve"
    | "chiffrage_incoherent"
  )[];
  /**
   * Citations de la sortie et résultat de leur vérification. `measure` : index de la mesure (null pour une position) ; `role` : justification ou passage du chiffrage.
   */
  quotes: CheckedQuote[];
  usage: ProposalUsage;
  cost_usd: number;
  created_at: string;
}
export interface CheckedQuote {
  measure: number | null;
  role: "evidence" | "costing";
  chunk_id: string | null;
  text: string;
  verified: boolean;
}
export interface ProposalUsage {
  input_tokens: number;
  output_tokens: number;
  cache_creation_input_tokens: number;
  cache_read_input_tokens: number;
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
