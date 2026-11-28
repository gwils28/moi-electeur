# Accessibilité de Moi Électeur

Référentiel : RGAA 4.1 (WCAG 2.1 niveau AA). Ce document tient lieu de **déclaration
d'accessibilité** et de compte rendu d'audit (PLAN D46).

## État de conformité

**Auto-évaluation, non certifiée.** L'audit ci-dessous a été conduit en interne (agent de
développement, 2026-11-27), pas par un auditeur indépendant : il ne permet pas d'afficher un
taux de conformité au sens réglementaire. Aucune non-conformité connue n'est ouverte à la date
de l'audit ; la déclaration sera mise à jour après un audit externe.

Pages évaluées : boussole (`/`), comparateur (`/comparateur`), positions (`/positions`, ajoutée
le 28/11 : tests automatisés et clavier, sans nouvel audit manuel), interrogatoire (`/interrogatoire`, ex-`/explorer`),
méthodologie (`/methodologie`).

## Méthode

- **Automatique, à chaque modification (CI)** : axe-core (règles WCAG 2.0 / 2.1 A et AA) sur
  chaque page et chaque état important (questionnaire, résultats, panneau, mode aveugle,
  comparateur, détail du radar, réponse du chat), sur ordinateur et sur mobile (360 px).
- **Tests e2e dédiés** (`apps/web/e2e/accessibilite.spec.ts`) : lien d'évitement premier au
  clavier et focus déplacé sur le contenu, page courante signalée dans la navigation, titre de
  page et `h1` uniques, contenu redistribué à 320 px (zoom 400 %) sans défilement horizontal.
- **Manuelle** : parcours complet au clavier, lecture de la structure (titres, régions, noms
  accessibles), zoom, mode sombre, réduction des animations.

## Grille par thème RGAA

| Thème | Critères vérifiés | Résultat |
|---|---|---|
| 1. Images | l'échiquier (SVG) a un nom accessible et une alternative complète : tableau trié des proximités et coordonnées, description textuelle de la position ; pictogrammes du radar `aria-hidden`, doublés d'un libellé texte | conforme |
| 2. Cadres | aucun cadre | non applicable |
| 3. Couleurs | aucune information portée par la seule couleur (formes sur l'échiquier, libellés du radar) ; contrastes vérifiés par axe, en mode clair et sombre | conforme |
| 4. Multimédia | aucun média temporel | non applicable |
| 5. Tableaux | tableaux de données avec `caption`, en-têtes `th` et `scope` (proximités, face-à-face, radar) ; tableaux défilants rendus focalisables et nommés | conforme |
| 6. Liens | intitulés explicites (navigation, sources des citations, documents) | conforme |
| 7. Scripts | composants interactifs au clavier (questionnaire, curseurs de poids, « Et si », cellules du radar avec `aria-expanded`) ; messages d'état annoncés (`role="status"`, `aria-live`) ; réponse du chat annoncée à la fin (`aria-busy`) | conforme |
| 8. Éléments obligatoires | langue `fr`, titre de page unique par page, code valide généré par React | conforme |
| 9. Structuration | un seul `h1` par page, hiérarchie des titres, régions `main` et `nav`, listes | conforme |
| 10. Présentation | focus toujours visible (`:focus-visible`, contour de 3 px) ; contenu redistribué à 320 px ; aucune information donnée par la seule forme ou position ; animations coupées si « réduire les animations » | conforme après correction (voir plus bas) |
| 11. Formulaires | chaque champ a une étiquette ; groupes de réponses en `fieldset` / `legend` ; la seule saisie libre (question du chat) indique sa limite et son mode d'envoi | conforme |
| 12. Navigation | lien d'évitement « Aller au contenu » ; navigation principale identique sur toutes les pages ; page courante signalée (`aria-current`) | conforme après correction |
| 13. Consultation | aucune limite de temps ; aucun contenu clignotant ; les documents sources (PDF des programmes) sont ceux des candidats et ne relèvent pas du site | conforme (documents tiers hors périmètre) |

## Écarts trouvés par l'audit et corrigés

- Absence de lien d'évitement (12.7) : ajouté, premier élément atteint au clavier.
- Page courante non signalée dans la navigation : `aria-current="page"` et mise en gras.
- Focus visible laissé au style par défaut du navigateur, variable selon les composants (10.7) :
  contour explicite et uniforme.
- Défilement horizontal à 320 px sur la boussole et le comparateur (10.11), causé par le
  sélecteur d'élection : largeur contrainte.
- Tableaux défilants du comparateur non atteignables au clavier (relevé par axe en M3d) :
  conteneurs focalisables et nommés.

## Limites connues

- Les réponses du chat sont générées : leur structure (titres par candidat, paragraphes, liste
  de citations) est contrôlée par l'application, mais leur formulation ne l'est pas.
- Les PDF des programmes, fournis par les candidats, ne sont pas tous accessibles.
- Aucun test avec un lecteur d'écran réel (NVDA, VoiceOver) n'a encore été mené : prévu lors de
  l'audit externe.

## Contact

Signaler un défaut d'accessibilité : ouvrir un ticket sur le dépôt du projet
(<https://github.com/gwils28/moi-electeur/issues>). Recours : le Défenseur des droits
(<https://www.defenseurdesdroits.fr>).
