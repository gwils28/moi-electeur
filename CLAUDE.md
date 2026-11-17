# Moi Électeur

Boussole électorale + explorateur RAG des programmes officiels. Spécification : @SPEC.md. Plan en cours : `PLAN.md`. Notes d'implémentation : `docs/notes-implementation.md`.

## Règles non négociables
- Les réponses au questionnaire, les poids et (X_user, Y_user) ne quittent **jamais** le navigateur. Aucun appel réseau dans `lib/engine`.
- Ne jamais logguer le contenu des questions du chat (donnée d'opinion, RGPD art. 9).
- Le front ne charge que des positions/mesures au statut `validated` ou `corrected`.
- Aucun texte produit par l'app ne classe un candidat (« meilleur », « plus crédible »…). Ordre des candidats aléatoire.
- Les (x, y) des candidats sont **calculés**, jamais saisis à la main.
- Types de données : source unique = `schemas/*.schema.json`. Ne pas dupliquer à la main en TS/Pydantic.

## Façon de travailler
- Phases : explorer → lever les inconnues → plan (`PLAN.md`, annoté par l'humain) → implémenter avec tests → valider → l'humain commite.
- Le moteur de calcul s'écrit test d'abord ; ne pas modifier un test pour le faire passer sans le signaler.
- Consigner dans `docs/notes-implementation.md` tout écart au plan et tout choix conservateur.
- Ne pas commiter ni pousser : préparer le diff, lancer les contrôles, proposer un message Conventional Commits.
- Rien n'est « fini » sans preuve : sortie de test ou commande lancée.

## Commandes
_(à compléter au jalon M0)_

## Compaction
En cas de compaction, conserver : fichiers modifiés, commandes de test et leur dernier résultat, décisions de modélisation (formules, schémas), points ouverts de SPEC.md § 15.

Ligne témoin : terminer chaque réponse finale qui modifie du code par « 🧭 ».
