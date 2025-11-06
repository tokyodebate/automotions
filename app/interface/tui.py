from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator
from InquirerPy.validator import NumberValidator
from pathlib import Path
import requests
from requests.models import stream_decode_response_unicode
from yaspin import yaspin
from urllib.parse import urlparse, urljoin
from typing import Literal
import json
import re

from .types import BaseInterface, TabbycatContext
from ..types import TournamentData, TournamentTag, TournamentYear
from ..reader import MotionFileReader

# pyright: reportPrivateImportUsage=false

class TUIInterface(BaseInterface):
    def get_context(self) -> TabbycatContext:
        def validate_url(url: str) -> bool:
            try:
                ctx = self._url_to_context(url)
                return True
            except Exception as e:
                return False
        
        answer: TabbycatContext = inquirer.text("Enter the URL of Tabbycat:", validate=validate_url, transformer=lambda x: self._url_to_context(x)["base_url"], filter=self._url_to_context).execute()
        # Check for API endpoint
        with yaspin(text="Fetching tournaments", color="blue") as spinner:
            try:
                response = requests.get(urljoin(answer["base_url"], "/api/v1/tournaments"))
                response.raise_for_status()
                tournaments = response.json()
                if answer["tournament_slug"] is not None: #Tournament slug is already provided within URL
                    tournament = next((tournament for tournament in tournaments if tournament["slug"] == answer["tournament_slug"]), None)
                    if tournament is None:
                        raise ValueError(f"Tournament {answer['tournament_slug']} not found")
                    else:
                        answer["tournament_name"] = tournament["name"]
                        spinner.write(f"Tournament {tournament['name']} found")
                else:
                    if not tournaments:
                        raise ValueError("No tournaments found.")
                    spinner.write(f"Found {len(tournaments)} tournaments")
            except requests.exceptions.HTTPError as e:
                spinner.write(f"HTTP Status Code {e.response.status_code}")
                spinner.color = "red"
                spinner.fail("✗")
                raise e
            except Exception as e:
                spinner.write(str(e))
                spinner.color = "red"
                spinner.fail("✗")
                raise e
            spinner.color = "green"
            spinner.ok("✓")
        # Ask for tournament if not provided
        if answer["tournament_slug"] is None:
            tournament_select: dict = inquirer.select(
                "Select the tournament to load:",
                choices=[Choice(name=tournament["name"], value=tournament) for tournament in tournaments]
            ).execute()
            answer["tournament_slug"] = tournament_select["slug"]
            answer["tournament_name"] = tournament_select["name"]
        # Ask for tournament type
        tournament_type: Literal["NA", "Asian", "BP"]|None = inquirer.select(
            "Select the tournament type:",
            choices=[Choice(name="Automatic", value=None), Choice(name="North American", value="NA"), Choice(name="Asian Parliamentary", value="Asian"), Choice(name="British Parliamentary", value="BP")]
        ).execute()
        answer["tournament_type"] = tournament_type
        return answer
    
    def get_output_format(self) -> list[Literal["clipboard_text", "clipboard_table", "git"]]:
        answer: list[Literal["clipboard_text", "clipboard_table", "git"]] = inquirer.checkbox(
            "Select the output formats:",
            choices=[
                Choice(name="Copy text data to clipboard", value="clipboard_text", enabled=False),
                Choice(name="Copy table data to clipboard", value="clipboard_table", enabled=True),
                Choice(name="Save to tokyodebate/motions repository", value="git", enabled=True),
            ]
        ).execute()
        return answer
    
    def get_git_repository(self, ctx: TabbycatContext) -> Path:
        # Select the git repository
        def validate_git_folder(path: str) -> bool:
            dir = Path(path).expanduser()
            if not dir.is_dir():
                return False
            if not (dir/"Javascript"/"TournamentList.json").exists():
                return False
            return True
        folder_path: Path = inquirer.filepath(
            "Enter path of git repository:",
            only_directories=True,
            validate=validate_git_folder,
            transformer=lambda x: str(Path(x).resolve()),
            filter=lambda x: Path(x).resolve()
        ).execute()
        return folder_path
        
    def handle_git(self, ctx: TabbycatContext, repository_path: Path, tournament_data: TournamentYear):
        # Load tournament list
        tournament_list_file: Path = repository_path/"Javascript"/"TournamentList.json"
        tournament_list: list[TournamentData] = json.loads(tournament_list_file.read_text())
        def get_name(tournament: TournamentData) -> str:
            if tournament["short"]:
                return f"{tournament['name']} ({tournament['short']})"
            else:
                return tournament["name"]
        # Search for tournament
        default = " ".join(part for part in ctx["tournament_name"].split(" ") if part.isalpha()) if ctx["tournament_name"] else None
        tournament_select: TournamentData|Literal["new"] = inquirer.fuzzy(
            "Select the tournament to load:",
            long_instruction="Type \"New tournament\" to create a new tournament",
            choices=[Choice(name=get_name(tournament), value=f"id:{tournament['id']}") for tournament in tournament_list] + [Choice(name="New tournament", value="new")],
            default=default,
            validate=lambda x: x is not None,
            filter=lambda x: next(t for t in tournament_list if t["id"] == x[3:]) if x.startswith("id:") else x
        ).execute()
        # Create new tournament & add to list
        if tournament_select == "new":
            tournament_select = self._get_new_tournament_data(repository_path, tournament_list)
            with yaspin(text=f"Creating {tournament_select['url']}", color="blue") as spinner:
                with open(repository_path/tournament_select["url"], "w") as f:
                    f.write(tournament_select["name"])
            tournament_list.append(tournament_select)
        # Prompt for where to save in the tournament file
        motion_file_reader = MotionFileReader(repository_path/tournament_select["url"])
        tournament_groups = motion_file_reader.get_tournament_groups()
        choices = []
        for i, tg in enumerate(tournament_groups):
            if i > 0:
                choices.append(Separator())
            choices.append(Separator(tg["name"]))
            for j, ty in enumerate(tg["tournaments"]):
                choices.append(Choice(name="  Insert here", value=(i, j)))
                choices.append(Separator(f"  {ty["name"]}"))
            choices.append(Choice(name="  Insert here", value=(i, len(tg["tournaments"]))))
        insert_position: tuple[int, int] = inquirer.select(
            "Select the position to insert the tournament:",
            choices=choices
        ).execute()
        tournament_groups[insert_position[0]]["tournaments"].insert(insert_position[1], tournament_data)
        # Refresh tournament list
        default = match.group() if ctx["tournament_name"] and (match := re.search(r"\d{4}", ctx["tournament_name"])) else ""
        year: int = inquirer.text(
            "Enter the year of the tournament:",
            validate=NumberValidator(),
            filter=int,
            default=default
        ).execute()
        tournament_select["latest"] = year
        with yaspin(text=f"Writing to {str(motion_file_reader.path)}", color="blue") as spinner:
            motion_file_reader.write_to_file(motion_file_reader.tournament_groups_to_lines(tournament_groups))
            spinner.text = f"Written to {str(motion_file_reader.path)}"
            spinner.color = "green"
            spinner.ok("✓")
        with yaspin(text="Updating tournament list", color="blue") as spinner:
            tournament_list_file.write_text(json.dumps(tournament_list, indent=4))
            spinner.text = "Updated tournament list"
            spinner.color = "green"
            spinner.ok("✓")
        

    
    @staticmethod
    def _get_new_tournament_data(folder_path: Path, tournament_list: list[TournamentData]) -> TournamentData:
        tournament_id: str = inquirer.text("Enter the ID of the new tournament (e.g. jbp):", validate=lambda x: x and all(tournament["id"] != x for tournament in tournament_list)).execute()
        tournament_name: str = inquirer.text("Enter the name of the new tournament (e.g. Japan BP):", validate=lambda x: bool(x)).execute()
        tournament_short: str = inquirer.text("Enter the abbreviation of the new tournament (e.g. JBP):").execute()
        tournament_tag: list[TournamentTag] = inquirer.checkbox(
            "Select the tags for the new tournament:",
            choices=[
                Choice("Australasian"),
                Choice("BP"),
                Choice("Asian"),
                Choice("NA"),
                Separator(),
                Choice("rookie", "Rookie Tournament"),
                Choice("open", "Open Tournament"),
                Choice("proam", "Pro-Am Tournament"),
                Separator(),
                Choice("region:Domestic", "Domestic Tournament"),
                Choice("region:World", "World Tournament"),
                Choice("region:Asia", "Asia Tournament"),
                Choice("region:Europe", "European Tournament"),
                Choice("region:Oceania", "Oceania Tournament"),
                Choice("region:America", "America Tournament")
            ]
        ).execute()
        is_international: bool = any(tag in tournament_tag for tag in {"region:World", "region:Asia", "region:Europe", "region:Oceania", "region:America"})
        def validate_tournament_file(path: str) -> bool:
            file = Path(path).resolve()
            if file.exists() or not file.is_relative_to(folder_path) or file.suffix != ".txt":
                return False
            return True
        tournament_file: str = inquirer.filepath(
            "Enter the path of the new tournament file:",
            validate=validate_tournament_file,
            default=str(folder_path/"International")+"/" if is_international else str(folder_path),
            invalid_message="Invalid path. Make sure the file is a .txt file and does not exist.",
            transformer=lambda x: str(Path(x).resolve().relative_to(folder_path)),
            filter=lambda x: str(Path(x).resolve().relative_to(folder_path))
        ).execute()
        return {
            "id": tournament_id,
            "name": tournament_name,
            "short": tournament_short,
            "latest": 0,
            "tag": tournament_tag,
            "url": tournament_file,
        }
    
    @staticmethod
    def _url_to_context(url: str) -> TabbycatContext:
        base_url = urljoin(url, "/")
        assert base_url != "/", "Invalid URL"
        tournament_slug = urlparse(url).path.lstrip("/").split("/")[0]
        tournament_slug = tournament_slug if tournament_slug not in {"", "accounts", "api", "archive", "create", "database", "notifications"} else None
        return TabbycatContext(base_url=base_url, tournament_slug=tournament_slug, tournament_type=None,tournament_name=None)