// Chaînes de l'interface. Vérifiées par scripts/check-forbidden-words.py (aucun texte ne classe un candidat).
export const fr = {
  appName: "Moi Électeur",
  tagline:
    "Interrogatoire des programmes officiels, boussole électorale et positions des candidats.",
  status: "Version en construction : données de démonstration fictives.",
  privacy: "Vos réponses restent dans votre navigateur. Aucun cookie, aucun suivi.",
  fictional: "Élection fictive : candidats, partis et citations sont inventés.",
  start: "Commencer le questionnaire",
  themeProgress: (i: number, n: number) => `Thème ${i} sur ${n}`,
  answered: (k: number, n: number) => `${k} réponse(s) sur ${n}`,
  likert: [
    { value: -2, label: "Pas du tout d'accord" },
    { value: -1, label: "Plutôt pas d'accord" },
    { value: 0, label: "Neutre" },
    { value: 1, label: "Plutôt d'accord" },
    { value: 2, label: "Tout à fait d'accord" },
  ],
  noOpinion: "Sans avis",
  likertEnds: { min: "Désaccord", max: "Accord" },
  weight: "Importance de ce thème",
  weightLabels: { 1: "Normale (×1)", 2: "Importante (×2)", 3: "Très importante (×3)" },
  previous: "Thème précédent",
  next: "Thème suivant",
  seeResults: "Voir les résultats",
  results: "Vos résultats",
  orderNote:
    "Les candidats sont présentés par score de proximité décroissant avec vos réponses (à égalité, dans un ordre tiré au sort). Ce score porte sur toutes vos réponses : quand un programme ne se prononce pas, la réponse compte pour 40 %. Il mesure une proximité de réponses, pas une préférence.",
  proximity: "Proximité",
  commonScore: (pct: number) => `${pct} % sur les seuls points communs`,
  commonCol: "Sur les points communs",
  coverage: (pct: number) => `couverture ${pct} %`,
  coverageDetail: (n: number, answered: number) => `calculée sur ${n} de vos ${answered} réponses`,
  coverageNote:
    "Sous chaque nom, la proximité « sur les seuls points communs » ne compte que les affirmations où le programme se prononce ; le score de proximité, lui, tient compte de toutes vos réponses. Vérifiez aussi la couverture.",
  lowCoverage: "Le programme ne se prononce pas sur plus de la moitié de vos réponses.",
  lowCoverageBadge: "Couverture faible",
  dialLegend:
    "Arc extérieur : score de proximité sur toutes vos réponses (0 à 100 %), les silences du programme comptant pour 40 %. Anneau intérieur : part de vos réponses sur lesquelles le programme se prononce (couverture). Arc hachuré : couverture inférieure à 50 %, score peu fiable.",
  noCommon: "Aucune affirmation commune : proximité non calculable.",
  mode: "Mode de projection",
  modeA: "Axes thématiques (A)",
  modeB: "Analyse factorielle (B)",
  modeBNote: (x: number, y: number) =>
    `Axes calculés par ACP : ils expliquent ${x} % et ${y} % de la variance des positions.`,
  modeBAxis: (i: number) => `Composante ${i}, affirmations les plus contributives :`,
  modeBNoTheme: "Le filtre par thème s'applique au mode A uniquement.",
  clamped: "Votre point dépasse le cadre et a été ramené au bord.",
  themeFilter: "Filtrer par thème",
  allThemes: "Tous les thèmes",
  blind: "Mode aveugle",
  blindOn: "Noms et partis masqués.",
  reveal: "Révéler les candidats",
  quoteHidden: "Citation masquée en mode aveugle (elle pourrait révéler le candidat).",
  you: "Vous",
  chessboardLabel: "Échiquier politique",
  proximityMapLabel: "Carte de proximité",
  mapView: "Vue de la carte",
  mapViewProximity: "Proximité avec vous",
  mapViewPositions: "Positions politiques",
  mapInfoLabel: "Comment lire la carte ?",
  mapInfoProximity:
    "Proximité avec vous : vous êtes au centre. Plus le score de proximité d'un candidat est élevé, plus il est près de vous : la distance est proportionnelle à 100 % moins son score (cercles à 75 et 50 %, bord à 25 % ou moins). Sa direction est celle qu'il a par rapport à vous sur la carte politique.",
  mapInfoPositions:
    "Positions politiques : chaque point est la position du programme sur les deux axes, calculée à partir de ses réponses aux affirmations. La distance entre deux points n'est pas le score de proximité.",
  proximityMapNote:
    "Distance à votre point proportionnelle à 100 % moins le score de proximité (bord : 25 % ou moins) ; direction : celle de la carte politique.",
  scoreTitle: "Score de proximité",
  scoreInfoLabel: "Comment est calculé ce score ?",
  scoreInfo: [
    "Le score porte sur toutes vos réponses, pondérées par l'importance que vous donnez à chaque thème.",
    "Quand le programme se prononce : 100 % si sa position est identique à votre réponse, 0 % si elle est opposée (écart de 4 crans), entre les deux sinon.",
    "Quand le programme ne se prononce pas : la réponse compte pour 40 %.",
    "On ajoute 5 affirmations fictives à 50 %, pour qu'un score ne repose jamais sur trop peu de réponses.",
    "Le score mesure une proximité de réponses, pas une préférence. Détails dans la méthodologie.",
  ],
  tableCaption: "Proximité et coordonnées de chaque candidat",
  candidateCol: "Candidat",
  coverageCol: "Couverture",
  ringsNote:
    "Cercles pointillés : distance de 2,5, 5 et 7,5 autour de votre point sur la carte (indicatif ; le score de proximité est calculé sur les réponses, pas sur la carte).",
  description: (x: string, y: string) =>
    `Votre position : ${x} sur l'axe horizontal, ${y} sur l'axe vertical.`,
  panelTitle: (label: string) => `Comparaison avec ${label}`,
  close: "Fermer",
  agreements: "Accords (écart de 0 ou 1)",
  partial: "Écarts modérés (écart de 2)",
  disagreements: "Désaccords (écart de 3 ou 4)",
  silences: "Silences du programme",
  none: "Aucune",
  whatIf: "Et si… ?",
  whatIfHelp:
    "Modifiez une réponse ou un poids : les résultats se recalculent et votre point se déplace.",
  delta: (d: string) => `variation ${d} pts`,
  share: "Partager ou reprendre plus tard",
  shareHelp:
    "Ce lien contient vos réponses dans la partie après #, qui n'est jamais envoyée au serveur.",
  copyLink: "Copier le lien",
  copied: "Lien copié",
  saveLocal: "Sauvegarder mes réponses sur cet appareil",
  restart: "Recommencer",
  editAnswers: "Modifier mes réponses",
  invalidCode: "Le lien de réponses est invalide ou incomplet ; questionnaire vierge.",
  missingData: "Données introuvables : lancer `uv run pipeline build`.",
  skipToContent: "Aller au contenu",
  header: {
    logoAlt: "Moi Électeur, accueil",
  },
  nav: {
    label: "Navigation principale",
    compass: "Boussole",
    positions: "Positions",
    ask: "Interrogatoire",
  },
  compass: {
    title: "Boussole électorale",
    intro:
      "Donnez votre avis sur une trentaine d'affirmations : la boussole calcule votre proximité avec chaque programme et vous situe sur la carte politique, directement dans votre navigateur.",
    facts: [
      "Une trentaine d'affirmations, environ 5 minutes",
      "Calcul fait dans votre navigateur : rien n'est envoyé",
      "Candidats affichés dans un ordre tiré au sort",
    ],
  },
  footer: {
    label: "Informations sur le site",
    methodology: "Méthodologie",
    accessibility: "Accessibilité",
    source: "Code source et données",
    license: "Code sous licence AGPL-3.0, données sous licence CC BY-SA 4.0.",
  },
  election: "Élection",
  pastElection: (date: string) =>
    `Élection passée : positions tirées des programmes officiels du premier tour (${date}).`,
  noCompass: "Aucune boussole n'est encore publiée.",
  positionsTabs: {
    label: "Vues des positions",
    matrix: "Tableau complet",
    comparator: "Comparateur",
  },
  positions: {
    title: "Positions des candidats",
    intro:
      "Pour chacune des affirmations de la boussole, la position que prend chaque programme, de « s'engage contre » (-2) à « s'engage pour » (+2), ou son silence. Sélectionnez une cellule pour lire les passages cités.",
    method:
      "Positions proposées par un modèle de langue à partir des programmes officiels, puis revues par le mainteneur : elles peuvent contenir des erreurs. La méthode et ses limites sont décrites dans la méthodologie.",
    methodTitle: "Comment ces positions sont établies",
    methodLink: "Lire la méthodologie",
    orderNote:
      "Les candidats sont affichés dans un ordre aléatoire, tiré à chaque visite. Aucun total ni classement : chaque cellule décrit un programme.",
    scrollHint: (candidates: number) =>
      `Le tableau défile horizontalement (${candidates} candidats).`,
    themeFilter: "Thème affiché",
    allThemes: "Tous les thèmes",
    candidateFilter: "Candidats affichés",
    allCandidates: "Tous",
    noCandidates: "Aucun",
    pickOne: "Choisissez au moins un candidat pour afficher le tableau.",
    shownCount: (shown: number, total: number) =>
      shown === total
        ? `Tous les candidats affichés (${total}).`
        : shown === 1
          ? `1 candidat affiché sur ${total}.`
          : `${shown} candidats affichés sur ${total}.`,
    caption: "Position de chaque programme sur les affirmations de la boussole, par thème",
    statement: "Affirmation",
    legend: "Lecture des cellules",
    short: {
      "2": "+2",
      "1": "+1",
      "0": "0",
      "-1": "-1",
      "-2": "-2",
    } as Record<string, string>,
    silenceShort: "silence",
    cellBefore: (candidate: string) => `${candidate} : `,
    cellAfter: (position: string) => `, ${position}. Afficher les citations.`,
    details: (candidate: string) => `Position de ${candidate}`,
    confidence: "Confiance de l'extraction",
    confidenceLevels: { high: "élevée", medium: "moyenne", low: "faible" } as Record<
      string,
      string
    >,
    corrected: (proposed: string) => `Corrigée à la revue (valeur proposée : ${proposed}).`,
    noEvidence: "Aucun passage cité.",
    close: "Fermer le détail",
  },
  comparator: {
    title: "Comparateur des programmes",
    intro:
      "Choisissez deux ou trois candidats : leurs mesures phares et leurs chiffrages s'affichent thème par thème, avec les affirmations sur lesquelles leurs programmes s'opposent.",
    orderNote:
      "Les candidats sont affichés dans un ordre aléatoire, tiré à chaque visite. Aucun total ni classement : chaque cellule décrit un programme.",
    pick: "Candidats comparés (deux ou trois)",
    pickMore: "Choisissez au moins deux candidats.",
    pickLimit: "Trois candidats au plus : retirez-en un pour en choisir un autre.",
    faceToFace: "Face-à-face",
    faceCaption: "Mesures phares et chiffrage annoncé, par thème",
    theme: "Thème",
    noMeasure: "Aucune mesure retenue",
    divergences: "Divergences (écart de 3 ou 4 entre deux programmes)",
    divergencesHelp:
      "Affirmations de la boussole sur lesquelles au moins deux des programmes choisis prennent des positions opposées.",
    noDivergence: "Aucune divergence de cette ampleur entre ces programmes.",
    positionLabels: {
      "2": "S'engage pour (+2)",
      "1": "Plutôt pour (+1)",
      "0": "Position intermédiaire (0)",
      "-1": "Plutôt contre (-1)",
      "-2": "S'engage contre (-2)",
    } as Record<string, string>,
    silence: "Pas de position retenue (silence du programme ou proposition écartée à la revue)",
    noMeasures: "Aucune mesure n'est publiée pour cette élection : radar indisponible.",
    radar: "Radar des chiffrages",
    radarHelp:
      "Pour chaque thème, le statut le plus précis des mesures relevées : chiffré si au moins une mesure annonce un montant, partiel si un coût ou un financement est évoqué sans montant complet, intention sinon, silence si aucune mesure n'est retenue. Sélectionnez une cellule pour voir les mesures et leurs citations.",
    radarCaption: "Statut des chiffrages par thème et par candidat",
    status: {
      chiffre: "chiffré",
      partiel: "partiel",
      intention: "intention",
      silence: "silence",
    },
    cellLabel: (candidate: string, theme: string, status: string) =>
      `${candidate}, ${theme} : ${status}. Afficher les mesures.`,
    details: (candidate: string, theme: string) => `Mesures de ${candidate} : ${theme}`,
    costingQuote: "Passage du chiffrage",
    citations: "Citations",
  },
  explorer: {
    title: "Interrogatoire des programmes",
    intro:
      "Posez vos questions, précises ou larges : la réponse résume, candidat par candidat, ce que disent leurs documents officiels, avec les passages cités.",
    disclaimer:
      "Réponses générées automatiquement à partir des seuls programmes officiels : elles peuvent contenir des erreurs. Vérifiez toujours la source citée.",
    privacy:
      "Votre question est envoyée au serveur pour produire la réponse, sans être enregistrée. L'historique de la conversation reste dans cet onglet.",
    election: "Élection",
    noElection: "Aucune élection n'est disponible pour l'interrogatoire.",
    mode: "Type de réponse",
    modeFast: "Réponse rapide",
    modeFastHelp: "Modèle économique, adapté à la plupart des questions.",
    modeDeep: "Réponse détaillée",
    modeDeepHelp:
      "Modèle avec réflexion, plus coûteux : nombre de questions limité. Les deux répondent à partir des mêmes passages.",
    settings: "Réglages de la question",
    candidates: "Candidats inclus",
    includedCount: (n: number, total: number) => `${n} sur ${total}`,
    allCandidates: "Tous",
    noCandidates: "Aucun",
    theme: "Thème",
    allThemes: "Tous les thèmes",
    question: "Votre question",
    questionHelp:
      "500 caractères au plus. Entrée pour envoyer, Maj + Entrée pour aller à la ligne.",
    placeholder: "Ex. : Que proposent les candidats sur les retraites ?",
    send: "Envoyer",
    stop: "Arrêter",
    newConversation: "Nouvelle conversation",
    you: "Votre question",
    answer: "Réponse",
    streaming: "Réponse en cours de rédaction…",
    stopped: "Réponse interrompue.",
    incomplete: "La réponse s'est interrompue avant la fin : elle peut être incomplète.",
    sources: "Passages cités",
    unverified: "non vérifiée",
    unverifiedHelp:
      "Le passage cité n'a pas été retrouvé tel quel dans le document : à vérifier à la source.",
    unverifiedCount: (n: number) =>
      `${n} citation(s) non vérifiée(s) dans cette réponse : à vérifier à la source.`,
    neutralityFlag:
      "Le contrôle automatique de neutralité a repéré dans cette réponse une formulation qui pourrait sembler hiérarchiser les candidats.",
    truncated: "La réponse a été tronquée (longueur maximale atteinte).",
    citation: (n: number) => `Citation ${n}`,
    openSource: "ouvrir le document",
    page: "page",
    unknownSource: "Source inconnue",
    switchToFast: "Reposer la question en réponse rapide",
    networkError: "Le service ne répond pas. Réessayez dans un instant.",
    rateLimited: "Trop de questions en peu de temps : réessayez dans quelques minutes.",
    blindNote:
      "Mode aveugle : sources et passages cités masqués, ils pourraient révéler le candidat.",
    historyNote: (n: number) =>
      `Contexte de la question suivante : ${n} échange(s) précédent(s), 3 au plus.`,
  },
} as const;
