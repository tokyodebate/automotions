from typing import TypedDict, Literal
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup, Tag
from difflib import SequenceMatcher
from yaspin import yaspin
from .interface.types import TabbycatContext
from .types import Round, Motion, MotionStats, RoundMotion, TournamentYear
from .utils import parse_round

class MotionManager:
    ctx: TabbycatContext
    rounds: list[Round]
    def __init__(self, ctx: TabbycatContext):
        self.ctx = ctx
        self.rounds = []

    def get_data(self) -> TournamentYear:
        self._fetch_api()
        html = requests.get(urljoin(self.ctx["base_url"], f"/{self.ctx['tournament_slug']}/motions/statistics/")).text
        self._scrape_motion_statistics(BeautifulSoup(html, "html.parser"))
        assert self.ctx["tournament_name"], "Tournament name not found"
        return {
            "name": self.ctx["tournament_name"],
            "rounds": self.rounds
        }

    def _fetch_api(self):
        with yaspin(text="Fetching rounds", color="blue") as spinner:
            rounds = requests.get(urljoin(self.ctx["base_url"], f"/api/v1/tournaments/{self.ctx['tournament_slug']}/rounds")).json()
            for round_data in rounds:
                self.rounds.append(Round(url=round_data["url"], seq=round_data["seq"], name=round_data["name"], motions=[], pretty_name=parse_round(round_data["name"])))
            spinner.text = f"Fetched {len(rounds)} rounds"
            spinner.color = "green"
            spinner.ok("✓")
        with yaspin(text="Fetching motions", color="blue") as spinner:
            motions = requests.get(urljoin(self.ctx["base_url"], f"/api/v1/tournaments/{self.ctx['tournament_slug']}/motions")).json()
            for motion_data in motions:
                motion = Motion(url=motion_data["url"], text=motion_data["text"], reference=motion_data["reference"], info_slide=motion_data["info_slide"], info_slide_plain=self._prettify_info(motion_data["info_slide"]))
                for round_data in motion_data["rounds"]:
                    found_round = next((round for round in self.rounds if round["url"] == round_data["round"]), None)
                    if found_round is not None:
                        found_round["motions"].append(RoundMotion(motion=motion, seq=round_data["seq"], stats=[]))
            spinner.text = f"Fetched {len(motions)} motions"
            spinner.color = "green"
            spinner.ok("✓")
        self.rounds.sort(key=lambda x: x["seq"])
        for round in self.rounds:
            round["motions"].sort(key=lambda x: x["seq"])
    
    def _scrape_motion_statistics(self, soup: BeautifulSoup):
        round_tiles = soup.select("div.container-fluid > div:last-child > div.col > div.list-group.mt-3")
        for round_tile in round_tiles:
            # Round name
            round_name_element = round_tile.select_one("span.badge.badge-secondary")
            assert round_name_element, "Round name element not found"
            round_obj = next((round for round in self.rounds if round["name"] == round_name_element.text), None)
            assert round_obj, "Round object not found"
            # Motion tile
            motion_tiles = round_tile.select(":scope > div:not(:first-child)")
            for motion_tile in motion_tiles:
                # Matching motion
                motion_h4 = motion_tile.select_one("h4")
                assert motion_h4, "Motion h4 element not found"
                motion_text = ''.join(t for t in motion_h4.find_all(string=True, recursive=False)).strip()
                reference_element = motion_h4.select_one("small.text-muted")
                assert reference_element, "Reference element not found"
                reference = reference_element.text.strip()[1:-1] # Remove parenthesis
                #motion_obj = next((round_motion for round_motion in round_obj["motions"] if round_motion["motion"]["reference"] == reference), None)
                motion_obj = max(round_obj["motions"], key=lambda x: SequenceMatcher(None,motion_text, x["motion"]["text"]).ratio())
                assert motion_obj, "Motion object not found"
                assert motion_obj["motion"]["reference"] == reference, "Reference mismatch"
                assert SequenceMatcher(None, motion_text, motion_obj["motion"]["text"]).ratio() > 0.9, "Motion text mismatch"
                # Extract stats
                stats_element = motion_tile.select_one(":scope > div.row:last-child")
                assert stats_element, "Stats element not found"
                if self.ctx["tournament_type"] is None:
                    with yaspin(text="Inferring tournament type...", color="blue") as spinner:
                        self.ctx["tournament_type"] = self._infer_tournament_type(stats_element)
                        spinner.text = f"Tournament type inferred as {self.ctx['tournament_type']}"
                        spinner.color = "green"
                        spinner.ok("✓")
                match self.ctx["tournament_type"]:
                    case "NA":
                        motion_obj["stats"] = self._extract_na_stats(stats_element)
                    case "Asian":
                        motion_obj["stats"] = self._extract_asian_stats(stats_element)
                    case "BP":
                        motion_obj["stats"] = self._extract_bp_stats(stats_element)
                    case _:
                        raise ValueError("Invalid tournament type")
            if self.ctx["tournament_type"] == "Asian":
                # Fill missing (undisplayed) stats - rooms without any matches (may include vetoes, but stats are unknown)
                total_rooms = 0
                for round_motion in round_obj["motions"]:
                    stat_balance = next((stat for stat in round_motion["stats"] if stat["type_"] == "Balance"), None)
                    stat_veto = next((stat for stat in round_motion["stats"] if stat["type_"] == "Veto"), None)
                    if not stat_balance:
                        stat_balance = MotionStats(type_="Balance", value=[0, 0])
                        round_motion["stats"].insert(0, stat_balance)
                    total_rooms += stat_balance["value"][0] + stat_balance["value"][1]
                for round_motion in round_obj["motions"]:
                    assert round_motion["stats"][0]["type_"] == "Balance", "Expected Balance stat"
                    round_motion["stats"][0]["value"].append(total_rooms)
                    if len(round_motion["stats"]) == 2:
                        round_motion["stats"][1]["value"].append(total_rooms * 2)

    def _infer_tournament_type(self, row_element: Tag) -> Literal["NA", "Asian", "BP"]:
        match len(row_element.select(":scope > *")):
            case 1:
                match len(row_element.select(":scope > :first-child > *")):
                    case 2:
                        return "NA"
                    case 3:
                        return "BP"
                    case _:
                        pass
            case 2:
                return "Asian"
            case _:
                pass
        raise ValueError("Invalid row element")
    
    @staticmethod
    def _extract_na_stats(row_element: Tag) -> list[MotionStats]:
        aff_element = row_element.select_one("span.text-aff.pr-1.d-md-inline.d-block")
        neg_element = row_element.select_one("span.text-neg.pr-1.d-md-inline.d-block")
        assert aff_element, "Aff element not found"
        assert neg_element, "Neg element not found"
        return [MotionStats(type_="Balance", value=[int(aff_element.get_text().strip().split(" ")[0]), int(neg_element.text.strip().split(" ")[0])])]
    
    @staticmethod
    def _extract_asian_stats(row_element: Tag) -> list[MotionStats]:
        aff_wins = row_element.select_one(":scope > :first-child span.text-aff")
        neg_wins = row_element.select_one(":scope > :first-child span.text-neg")
        aff_vetoes = row_element.select_one(":scope > :last-child span.text-aff")
        neg_vetoes = row_element.select_one(":scope > :last-child span.text-neg")
        assert aff_wins, "Aff wins element not found"
        assert neg_wins, "Neg wins element not found"
        def get_count(span_element: Tag|None) -> int:
            return int(span_element.get_text().strip().split(" ")[0]) if span_element else 0
        return [MotionStats(type_="Balance", value=[get_count(aff_wins), get_count(neg_wins)]), MotionStats(type_="Veto", value=[get_count(aff_vetoes), get_count(neg_vetoes)])]
    
    @staticmethod
    def _extract_bp_stats(row_element: Tag) -> list[MotionStats]:
        bench_bars = row_element.select(":scope > :first-child > :last-child > * > div.progress")
        assert len(bench_bars) == 4, "Expected 4 bench bars"
        def get_count(rank_element: Tag) -> int:
            assert rank_element["title"], "Rank element data-original-title not found"
            return int(rank_element["title"].strip().split(" ")[0])
        return [MotionStats(type_=position, value=[get_count(rank_element) for rank_element in bench_bar.select(":scope > *")]) for position, bench_bar in zip(["OG", "OO", "CG", "CO"], bench_bars)]
    
    @staticmethod
    def _prettify_info(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        def handle_element(el, depth=0, in_list=False, list_type=None):
            text_parts = []

            for child in el.children:
                if child.name is None:
                    # It's a NavigableString
                    text_parts.append(child.strip())
                elif child.name == "br":
                    text_parts.append("\n")
                elif child.name == "p":
                    p_text = handle_element(child, depth)
                    if p_text.strip():
                        text_parts.append(p_text.strip() + "\n")
                elif child.name in ("ul", "ol"):
                    for i, li in enumerate(child.find_all("li", recursive=False), start=1):
                        bullet = f"{i}. " if child.name == "ol" else "- "
                        li_text = handle_element(li, depth + 1, True, child.name)
                        indent = "  " * depth
                        text_parts.append(f"{indent}{bullet}{li_text.strip()}\n")
                elif child.name == "li":
                    li_text = handle_element(child, depth)
                    text_parts.append(li_text.strip())
                else:
                    # Recurse for other tags
                    text_parts.append(handle_element(child, depth))

            return " ".join([t for t in text_parts if t]).strip().replace("\n ", "\n")

        result = handle_element(soup)
        return result.strip()