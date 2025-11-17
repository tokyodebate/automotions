from typing import Literal, Optional
from pathlib import Path
from urllib.parse import urlparse, urljoin
import requests
import json

from .types import BaseInterface, TabbycatContext
from ..types import TournamentData, TournamentTag, TournamentYear
from ..reader import MotionFileReader

class CLIInterface(BaseInterface):
    tabbycat_url: str
    tabbycat_tournament_slug: Optional[str]
    tournament_type: Optional[Literal["NA", "Asian", "BP"]]
    output_path: Optional[str]
    id: str
    latest: int
    save_pos: Optional[tuple[int, int]]
    update_or_create: Literal["update", "create"]
    new_name: Optional[str]
    new_short: Optional[str]
    new_tag: Optional[list[TournamentTag]]
    new_url: Optional[str]
    def __init__(
        self,
        tabbycat_url: str,
        latest: int,
        id: str,
        update_or_create: Literal["update", "create"] = "update",
        *,
        tabbycat_tournament_slug: Optional[str] = None,
        tournament_type: Optional[Literal["NA", "Asian", "BP"]] = None,
        output_path: Optional[str] = None,
        new_name: Optional[str] = None,
        new_short: Optional[str] = None,
        new_tag: Optional[list[TournamentTag]] = None,
        new_url: Optional[str] = None,
        save_pos: Optional[tuple[int, int]] = None,
    ):
        self.tabbycat_url = tabbycat_url
        self.tabbycat_tournament_slug = tabbycat_tournament_slug
        self.tournament_type = tournament_type
        self.output_path = output_path
        self.update_or_create = update_or_create
        self.id = id
        self.latest = latest
        self.save_pos = save_pos
        self.new_name = new_name
        self.new_short = new_short
        self.new_tag = new_tag or []
        self.new_url = new_url
        
    def _resolve_url(self, url: str, *, tournament_slug: Optional[str] = None, tournament_type: Optional[Literal["NA", "Asian", "BP"]] = None) -> TabbycatContext:
        base_url = urljoin(url, "/")
        assert base_url != "/", "Invalid URL"
        # If tournament_slug arg is not provided, extract it from URL
        if tournament_slug is None:
            tournament_slug = urlparse(url).path.lstrip("/").split("/")[0]
            tournament_slug = tournament_slug if tournament_slug not in {"", "accounts", "api", "archive", "create", "database", "notifications"} else None
        # If URL doesn't contain tournament slug, check if there is only one tournament
        if tournament_slug is None:
            response = requests.get(urljoin(base_url, "/api/v1/tournaments"))
            response.raise_for_status()
            tournaments: list[dict] = response.json()
            assert len(tournaments) == 1, f"Expected 1 tournament, got {len(tournaments)} tournaments. Include tournament slug in URL or specify tournament slug."
            tournament_slug = tournaments[0]["slug"]
            tournament_name = tournaments[0]["name"]
        else:
            response = requests.get(urljoin(base_url, f"/api/v1/tournaments/{tournament_slug}"))
            response.raise_for_status()
            tournament = response.json()
            tournament_name = tournament["name"]
        return TabbycatContext(base_url=base_url, tournament_slug=tournament_slug, tournament_type=tournament_type,tournament_name=tournament_name)

    def get_context(self) -> TabbycatContext:
        return self._resolve_url(self.tabbycat_url, tournament_slug=self.tabbycat_tournament_slug, tournament_type=self.tournament_type)
    
    def get_output_format(self) -> list[Literal["clipboard_text", "clipboard_table", "git"]]:
        return ["git"]
    
    def get_git_repository(self, ctx: TabbycatContext) -> Path:
        root = Path(".").resolve() if self.output_path is None else Path(self.output_path).resolve()
        if not (root/"Javascript"/"TournamentList.json").exists():
            raise ValueError("Tournament list file not found. Make sure tokyodebate/motions repository is cloned and is in the current directory.")
        return root
        
    def handle_git(self, ctx: TabbycatContext, repository_path: Path, tournament_data: TournamentYear):
        tournament_list_file: Path = repository_path/"Javascript"/"TournamentList.json"
        tournament_list: list[TournamentData] = json.loads(tournament_list_file.read_text())
        tournament_metadata: TournamentData
        match self.update_or_create:
            case "update":
                tournament_metadata = next(t for t in tournament_list if t["id"] == self.id)
                tournament_metadata["latest"] = self.latest
            case "create":
                assert self.new_name is not None, "New name is required for creating a new tournament"
                assert self.new_tag is not None, "New tag is required for creating a new tournament"
                assert self.new_url is not None, "New URL is required for creating a new tournament"
                assert all(d["id"] != self.id for d in tournament_list), "Tournament ID already exists"
                assert not (repository_path/self.new_url).exists(), f"Tournament file {self.new_url} already exists"
                with open(repository_path/self.new_url, "w") as f:
                    f.write(self.new_name)
                tournament_metadata = {
                    "id": self.id,
                    "name": self.new_name,
                    "short": self.new_short or "",
                    "latest": self.latest,
                    "tag": self.new_tag,
                    "url": self.new_url,
                }
                tournament_list.append(tournament_metadata)
        # Save tournament to file
        motion_file_reader = MotionFileReader(repository_path/tournament_metadata["url"])
        tournament_groups = motion_file_reader.get_tournament_groups()
        assert self.save_pos is not None, "Save position is required"
        tournament_groups[self.save_pos[0]]["tournaments"].insert(self.save_pos[1], tournament_data)
        motion_file_reader.write_to_file(motion_file_reader.tournament_groups_to_lines(tournament_groups))
        # Save tournament list
        tournament_list_file.write_text(json.dumps(tournament_list, indent=4))