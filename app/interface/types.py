from abc import ABC, abstractmethod
from typing import TypedDict, Literal
from pathlib import Path

from app.types import TournamentData, TournamentYear

class TabbycatContext(TypedDict):
    base_url: str
    tournament_slug: str|None
    tournament_name: str|None
    tournament_type: Literal["NA", "Asian", "BP"]|None

class BaseInterface(ABC):
    @abstractmethod
    def get_context(self) -> TabbycatContext:
        pass
    
    @abstractmethod
    def get_output_format(self) -> list[Literal["clipboard_text", "clipboard_table", "git"]]:
        pass
    
    @abstractmethod
    def get_git_repository(self, ctx: TabbycatContext) -> Path:
        pass

    @abstractmethod
    def handle_git(self, ctx: TabbycatContext, repository_path: Path, tournament_data: TournamentYear):
        pass