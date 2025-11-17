from functools import cache
import re
from .types import TournamentYear

SUBSTRINGS_MOTION = [
    (r"\s{2,}", " "),
    (r"this house", "TH"),
    (r"th believes that", "THBT"),
    (r"th would", "THW"),
    (r"th supports", "THS"),
    (r"th opposes", "THO"),
    (r"th prefers", "THP"),
    (r"th regrets", "THR"),
    (r"\.$", ""),
    (r"“", '"'),
    (r"”", '"'),
    (r"‘", "'"),
    (r"’", "'"),
    (r"(?<=\S)\(", " ("),
    (r" \)", ")"),
    (r"\&amp;", "&"),
    (r"\&nbsp;", " "),
]

SUBSTRINGS_INFO = [
    (r"(\r*\n)+", "\n"),
    (r" {2,}", " "),
    (r"(?<=\S)\(", " ("),
    (r" \)", ")"),
    (r"“", '"'),
    (r"”", '"'),
    (r"\&amp;", "&"),
    (r"\&quot;", '"'),
    (r"<.*?>", ""),
    (r"\&nbsp;", " ")
]

SUBSTRINGS_ROUND = [
    (r"オープン", "Open "),
    (r"部門", ""),
    (r"準々々々々決勝", "TF"),
    (r"準々々々決勝", "OF"),
    (r"準々決勝", "QF"),
    (r"準決勝", "SF"),
    (r"決勝", "GF"),
    (r"ラウンド", "R"),
    (r"round ?", "R"),
    (r"novice", "Novice"),
    (r"high school", "HS"),
    (r"open", ""),
    (r"grand[ |-]?finals?", "GF"),
    (r"semi[ |-]?finals?", "SF"),
    (r"semis", "SF"),
    (r"double[ |-]quarter[ |-]?finals?", "OF"),
    (r"quarter[ |-]?finals?", "QF"),
    (r"quarters?", "QF"),
    (r"double[ |-]octo[ |-]?finals?", "DO"),
    (r"octo[ |-]?finals?", "OF"),
    (r"octos", "OF"),
    (r"finals?", "GF"),
    (r"partial[ |-]", "P"),
    (r"pre[ |-]", "Pre ")
]

def tournament_year_to_lines(tournament_year: TournamentYear) -> list[str]:
    lines: list[str] = []
    if not tournament_year["rounds"]:
        return []
    lines.append(f"\t{tournament_year['name']}")
    for round in tournament_year["rounds"]:
        if not round["motions"]:
            continue
        lines.append(f"\t\t{parse_round(round['pretty_name'])}")
        for motion in round["motions"]:
            lines.append(f"\t\t\t{parse_motion(motion['motion']['text'])}")
            for stats in motion["stats"]:
                lines.append(f"\t\t\t\t{stats['type_']} $stats {", ".join(str(value) for value in stats['value'])}")
            if motion["motion"]["info_slide_plain"]:
                for line in parse_info(motion["motion"]["info_slide_plain"]).split("\n"):
                    lines.append(f"\t\t\t\t{line}")
    return lines

def parse_motion(motion: str) -> str:
    for sub in SUBSTRINGS_MOTION:
        motion = re.sub(sub[0], sub[1], motion, flags=re.IGNORECASE)
    return motion.strip()

def parse_info(info: str) -> str:
    for sub in SUBSTRINGS_INFO:
        info = re.sub(sub[0], sub[1], info, flags=re.IGNORECASE)
    return info.strip()

@cache
def parse_round(round: str) -> str:
    for sub in SUBSTRINGS_ROUND:
        round = re.sub(sub[0], sub[1], round, flags=re.IGNORECASE)
    return round.strip()

@cache
def parse_round_table(round: str) -> str:
    round = round.split(":")[0].strip()
    parsed = parse_round(round)
    match = re.match(r"R(\d+)", parsed)
    if match:
        return match.group(1)
    return parsed
        