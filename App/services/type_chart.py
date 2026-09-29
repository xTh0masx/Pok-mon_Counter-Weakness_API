"""Modern (generation VI+) incoming type relations; no moves or abilities.

Each row: double_damage_from, half_damage_from, no_damage_from.
The fallback intentionally contains no invented Pokemon records.
"""

TYPE_CHART = {
    "normal": ("fighting", "", "ghost"),
    "fire": ("water ground rock", "fire grass ice bug steel fairy", ""),
    "water": ("electric grass", "fire water ice steel", ""),
    "electric": ("ground", "electric flying steel", ""),
    "grass": ("fire ice poison flying bug", "water electric grass ground", ""),
    "ice": ("fire fighting rock steel", "ice", ""),
    "fighting": ("flying psychic fairy", "bug rock dark", ""),
    "poison": ("ground psychic", "grass fighting poison bug fairy", ""),
    "ground": ("water grass ice", "poison rock", "electric"),
    "flying": ("electric ice rock", "grass fighting bug", "ground"),
    "psychic": ("bug ghost dark", "fighting psychic", ""),
    "bug": ("fire flying rock", "grass fighting ground", ""),
    "rock": ("water grass fighting ground steel", "normal fire poison flying", ""),
    "ghost": ("ghost dark", "poison bug", "normal fighting"),
    "dragon": ("ice dragon fairy", "fire water electric grass", ""),
    "dark": ("fighting bug fairy", "ghost dark", "psychic"),
    "steel": ("fire fighting ground", "normal grass ice flying psychic bug rock dragon steel fairy", "poison"),
    "fairy": ("poison steel", "fighting bug dark", "dragon"),
}


def fallback_type(name: str) -> dict:
    return {
        "name": name,
        "damage_relations": {
            key: [{"name": item} for item in group.split()]
            for key, group in zip(
                ("double_damage_from", "half_damage_from", "no_damage_from"), TYPE_CHART[name]
            )
        },
        "pokemon": [],
    }
