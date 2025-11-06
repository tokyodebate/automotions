from pathlib import Path
import re
from .types import TournamentGroup, TournamentYear, Round, RoundMotion
from .utils import tournament_year_to_lines

class MotionFileReader:
    def __init__(self, path: Path):
        self.path = path
        self.lines = self.path.read_text().split("\n")
    
    def get_tournament_groups(self) -> list[TournamentGroup]:
        res: list[TournamentGroup] = []
        tournament_group: TournamentGroup|None = None
        tournament_year: TournamentYear|None = None
        round: Round|None = None
        round_motion: RoundMotion|None = None
        
        for line in self.lines:
            indent_level, content = self._extract_line(line)
            if not content:
                continue
            match indent_level:
                case 0:
                    tournament_group = {
                        "name": content,
                        "tournaments": []
                    }
                    res.append(tournament_group)
                case 1:
                    assert tournament_group, "Tournament group not found"
                    tournament_year = {
                        "name": content,
                        "rounds": []
                    }
                    tournament_group["tournaments"].append(tournament_year)
                case 2:
                    assert tournament_year, "Tournament year not found"
                    round = {
                        "name": content,
                        "motions": [],
                        "seq": len(tournament_year["rounds"])+1,
                        "url": "",
                        "pretty_name": content
                    }
                    tournament_year["rounds"].append(round)
                case 3:
                    assert round, "Round not found"
                    round_motion = {
                        "motion": {
                            "text": content,
                            "info_slide": "",
                            "info_slide_plain": "",
                            "reference": "",
                            "url": ""
                        },
                        "seq": len(round["motions"])+1,
                        "stats": []
                    }
                    round["motions"].append(round_motion)
                case 4:
                    assert round_motion, "Round motion not found"
                    if "$stats" in content:
                        split = content.split("$stats")
                        assert len(split) == 2, "Expected 2 parts"
                        stat_type = split[0].strip()
                        stat_value = re.findall(r"\d+", split[1].strip())
                        assert stat_value, "Expected stat value"
                        round_motion["stats"].append({
                            "type_": stat_type,
                            "value": [int(value) for value in stat_value]
                        })
                    else:
                        round_motion["motion"]["info_slide_plain"] += ("\n" if round_motion["motion"]["info_slide_plain"] else "") + content
                case _:
                    raise ValueError(f"Invalid indent level: {indent_level}")
        return res
    
    def tournament_groups_to_lines(self, tournament_groups: list[TournamentGroup]) -> list[str]:
        lines: list[str] = []
        for tg in tournament_groups:
            lines.append(f"{tg['name']}")
            for ty in tg["tournaments"]:
                lines.extend(tournament_year_to_lines(ty))
        return lines
    
    def write_to_file(self, lines: list[str]):
        self.path.write_text("\n".join(lines))
    
    @staticmethod
    def _extract_line(line: str) -> tuple[int, str]:
        indent = re.match(r"^(?:\s{4}|\t)*", line).group() # type: ignore
        content = line.strip()
        indent_level = MotionFileReader._resolve_indent(indent)
        return indent_level, content
    
    @staticmethod
    def _resolve_indent(indent_str: str) -> int:
        def _iter(indent_str: str) -> int:
            if not indent_str:
                return 0
            if indent_str[0] == "\t":
                return 1 + _iter(indent_str[1:])
            assert indent_str.startswith("    "), "Invalid indent string"
            return 4 + _iter(indent_str[4:])
        return _iter(indent_str)