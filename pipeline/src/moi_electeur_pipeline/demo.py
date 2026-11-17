"""Génération déterministe de l'élection de démonstration `demo-fictive` (PLAN D9).

Candidats, partis et citations sont **inventés**. Chaque candidat fictif a un profil
idéologique (ex, ey) dans [-1, 1] ; ses positions (-2..+2) en sont dérivées avec un bruit
seedé, ce qui donne des données plausibles et reproductibles. Les coordonnées (x, y)
affichées ne sont pas ce profil : elles seront recalculées par le moteur depuis les positions.

Le notebook `notebooks/m0_01_donnees_demo.py` explique et contrôle cette construction.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

ELECTION_ID = "demo-fictive"
SEED = 2027
NOISE_SD = 0.5
REVIEW_DATE = "2026-11-17"

THEMES = [
    ("economie", "Économie"),
    ("social", "Social"),
    ("ecologie", "Écologie"),
    ("europe_international", "Europe & international"),
    ("regalien_immigration", "Régalien & immigration"),
    ("institutions", "Institutions"),
]

# (id, thème, texte, axe, sens). Sens +1 : « d'accord » pousse vers +10 sur l'axe.
STATEMENTS: list[tuple[str, str, str, str, int]] = [
    (
        "s01",
        "economie",
        "Il faut baisser l'impôt sur les sociétés pour renforcer la compétitivité des entreprises.",
        "x",
        1,
    ),
    (
        "s02",
        "economie",
        "L'État doit augmenter les impôts sur les plus hauts patrimoines.",
        "x",
        -1,
    ),
    (
        "s03",
        "economie",
        "Les dépenses publiques doivent être réduites pour revenir à l'équilibre budgétaire.",
        "x",
        1,
    ),
    (
        "s04",
        "economie",
        "L'État doit pouvoir nationaliser des entreprises jugées stratégiques.",
        "x",
        -1,
    ),
    (
        "s05",
        "economie",
        "Il faut assouplir le droit du travail pour faciliter les embauches.",
        "x",
        1,
    ),
    ("s06", "social", "Le salaire minimum doit être fortement augmenté.", "x", -1),
    ("s07", "social", "L'âge légal de départ à la retraite doit être reculé.", "x", 1),
    (
        "s08",
        "social",
        "Les allocations chômage doivent être réduites pour encourager le retour à l'emploi.",
        "x",
        1,
    ),
    ("s09", "social", "Les soins à l'hôpital public doivent être entièrement gratuits.", "x", -1),
    (
        "s10",
        "social",
        "Les aides sociales doivent être réservées en priorité aux nationaux.",
        "y",
        1,
    ),
    (
        "s11",
        "ecologie",
        "La fiscalité doit taxer davantage les activités les plus polluantes.",
        "x",
        -1,
    ),
    (
        "s12",
        "ecologie",
        "Les normes environnementales imposées aux entreprises doivent être allégées.",
        "x",
        1,
    ),
    (
        "s13",
        "ecologie",
        "Les énergies renouvelables doivent être financées en priorité par l'argent public.",
        "x",
        -1,
    ),
    (
        "s14",
        "ecologie",
        "L'agriculture doit être libérée des contraintes environnementales européennes.",
        "y",
        1,
    ),
    (
        "s15",
        "ecologie",
        "L'État doit réglementer plus strictement les véhicules polluants.",
        "x",
        -1,
    ),
    (
        "s16",
        "europe_international",
        "La France doit renforcer l'intégration européenne, y compris en matière de défense.",
        "y",
        -1,
    ),
    ("s17", "europe_international", "Le droit national doit primer sur le droit européen.", "y", 1),
    (
        "s18",
        "europe_international",
        "La France doit quitter le commandement intégré de l'OTAN.",
        "y",
        1,
    ),
    (
        "s19",
        "europe_international",
        "Les décisions européennes doivent pouvoir être prises à la majorité, sans veto national.",
        "y",
        -1,
    ),
    (
        "s20",
        "europe_international",
        "Il faut rétablir des contrôles permanents aux frontières nationales.",
        "y",
        1,
    ),
    ("s21", "regalien_immigration", "L'immigration de travail doit être réduite.", "y", 1),
    (
        "s22",
        "regalien_immigration",
        "Les étrangers en situation régulière doivent pouvoir voter aux élections locales.",
        "y",
        -1,
    ),
    (
        "s23",
        "regalien_immigration",
        "Des peines de prison minimales doivent être instaurées pour certains délits.",
        "y",
        1,
    ),
    (
        "s24",
        "regalien_immigration",
        "La consommation de cannabis doit être légalisée et encadrée.",
        "y",
        -1,
    ),
    (
        "s25",
        "regalien_immigration",
        "Les effectifs de police doivent être fortement augmentés.",
        "y",
        1,
    ),
    (
        "s26",
        "institutions",
        "La proportionnelle doit être introduite aux élections législatives.",
        "y",
        -1,
    ),
    ("s27", "institutions", "Le nombre de parlementaires doit être réduit.", "y", 1),
    ("s28", "institutions", "Le droit de vote doit être ouvert dès 16 ans.", "y", -1),
    (
        "s29",
        "institutions",
        "Le président de la République doit recourir davantage au référendum.",
        "y",
        1,
    ),
    (
        "s30",
        "institutions",
        "Les collectivités locales doivent disposer d'une plus grande autonomie fiscale.",
        "x",
        1,
    ),
]

# (id, nom, parti, couleur, alias, profil (ex, ey)). Tous fictifs.
CANDIDATES: list[tuple[str, str, str, str, str, tuple[float, float]]] = [
    (
        "c1",
        "Amandine Vérac",
        "Mouvement des Communs (fictif)",
        "#b2182b",
        "Candidat·e A",
        (-0.9, -0.6),
    ),
    ("c2", "Bastien Morel", "Alliance sociale (fictif)", "#ef8a62", "Candidat·e B", (-0.5, -0.2)),
    ("c3", "Claire Duvallon", "Renouveau central (fictif)", "#e6ab02", "Candidat·e C", (0.4, -0.7)),
    (
        "c4",
        "Damien Arkhel",
        "Parti de l'entreprise (fictif)",
        "#1b7837",
        "Candidat·e D",
        (0.9, 0.2),
    ),
    (
        "c5",
        "Élise Fontanes",
        "Rassemblement souverain (fictif)",
        "#2166ac",
        "Candidat·e E",
        (-0.1, 0.9),
    ),
    (
        "c6",
        "François Lemarcq",
        "Droite républicaine (fictif)",
        "#542788",
        "Candidat·e F",
        (0.6, 0.6),
    ),
]

# Cas particuliers volontaires pour tester le filtrage et les silences (PLAN § 2.4).
SILENCES = {("c3", "s18")}
REJECTED = {("c5", "s07"), ("c2", "s12")}

MEASURES: list[tuple[str, str, str, str, str, int | None]] = [
    (
        "c1",
        "social",
        "Revalorisation du salaire minimum",
        "Hausse du salaire minimum en deux étapes.",
        "chiffre",
        9_000_000_000,
    ),
    (
        "c2",
        "ecologie",
        "Plan de rénovation thermique",
        "Aide à la rénovation des logements anciens.",
        "partiel",
        4_000_000_000,
    ),
    (
        "c3",
        "europe_international",
        "Défense européenne commune",
        "Fonds européen d'investissement de défense.",
        "intention",
        None,
    ),
    (
        "c4",
        "economie",
        "Baisse de l'impôt sur les sociétés",
        "Taux ramené progressivement à 20 %.",
        "chiffre",
        12_000_000_000,
    ),
    (
        "c5",
        "regalien_immigration",
        "Contrôles aux frontières",
        "Recrutement de douaniers supplémentaires.",
        "partiel",
        1_500_000_000,
    ),
    (
        "c6",
        "institutions",
        "Réduction du nombre de parlementaires",
        "Diminution d'un tiers des sièges.",
        "intention",
        None,
    ),
]


def _value(rng: random.Random, profile: tuple[float, float], axis: str, direction: int) -> int:
    lean = profile[0] if axis == "x" else profile[1]
    raw = 2 * direction * lean + rng.gauss(0, NOISE_SD)
    return max(-2, min(2, round(raw)))


def build_demo() -> dict[str, Any]:
    """Construit les quatre documents de l'élection de démo (déterministe)."""
    rng = random.Random(SEED)
    config = {
        "id": ELECTION_ID,
        "name": "Élection de démonstration (candidats fictifs)",
        "country": "FR",
        "date_first_round": "2027-04-11",
        "fictional": True,
        "axes": {
            "x": {
                "label": "Économie",
                "min_label": "Interventionnisme / Redistribution",
                "max_label": "Libéralisme / Baisse de la fiscalité",
            },
            "y": {
                "label": "Société & souveraineté",
                "min_label": "Progressisme / Intégration européenne",
                "max_label": "Conservatisme / Autorité / Souverainisme",
            },
        },
        "quadrants": {
            "tl": "Interventionniste et conservateur",
            "tr": "Libéral et conservateur",
            "bl": "Interventionniste et progressiste",
            "br": "Libéral et progressiste",
        },
        "themes": [{"id": i, "label": label} for i, label in THEMES],
        "candidates": [
            {
                "id": cid,
                "name": name,
                "party": party,
                "color": color,
                "photo": None,
                "program_url": f"https://example.org/demo-fictive/{cid}",
                "blind_alias": alias,
            }
            for cid, name, party, color, alias, _ in CANDIDATES
        ],
        "corpus": [],
    }
    statements = {
        "election_id": ELECTION_ID,
        "statements": [
            {
                "id": sid,
                "theme": theme,
                "text": text,
                "axis": axis,
                "direction": d,
                "weight_in_axis": 1.0,
            }
            for sid, theme, text, axis, d in STATEMENTS
        ],
    }
    positions = []
    for cid, name, _party, _c, _a, profile in CANDIDATES:
        for sid, _theme, text, axis, d in STATEMENTS:
            value = _value(rng, profile, axis, d)
            silent = (cid, sid) in SILENCES
            rejected = (cid, sid) in REJECTED
            positions.append(
                {
                    "candidate_id": cid,
                    "statement_id": sid,
                    "value": None if silent else value,
                    "confidence": "high" if abs(value) == 2 else "medium",
                    "evidence": []
                    if silent
                    else [
                        {
                            "quote": f"Extrait fictif : position {value:+d} sur « {text} »",
                            "document_title": f"Programme fictif de {name}",
                            "page": int(sid[1:]),
                            "chunk_id": None,
                        }
                    ],
                    "proposed_by": "demo-generator",
                    "review": {
                        "status": "rejected" if rejected else "validated",
                        "reviewer": "demo",
                        "date": REVIEW_DATE,
                        "note": "Rejet volontaire (test du filtrage)." if rejected else None,
                    },
                }
            )
    measures = {
        "election_id": ELECTION_ID,
        "measures": [
            {
                "id": f"m{i:03d}",
                "candidate_id": cid,
                "theme": theme,
                "title": title,
                "summary": summary,
                "costing": {
                    "status": status,
                    "amount_eur": amount,
                    "period": "par an" if amount else None,
                    "quote": None,
                },
                "evidence": [
                    {
                        "quote": f"Extrait fictif : {summary}",
                        "document_title": "Programme fictif",
                        "page": 1,
                        "chunk_id": None,
                    }
                ],
                "review": {
                    "status": "validated",
                    "reviewer": "demo",
                    "date": REVIEW_DATE,
                    "note": None,
                },
            }
            for i, (cid, theme, title, summary, status, amount) in enumerate(MEASURES, 1)
        ],
    }
    return {
        "election_config.json": config,
        "statements.json": statements,
        "positions.json": {"election_id": ELECTION_ID, "positions": positions},
        "measures.json": measures,
    }


def write_demo(target: Path) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for name, doc in build_demo().items():
        path = target / name
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written
