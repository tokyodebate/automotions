from typing import TypedDict, Literal

TournamentTagList = ["Australasian", "BP", "Asian", "NA", "rookie", "open", "proam", "region:Domestic", "region:World", "region:Asia", "region:Europe", "region:Oceania", "region:America"]
TournamentTag = Literal["Australasian", "BP", "Asian", "NA", "rookie", "open", "proam", "region:Domestic", "region:World", "region:Asia", "region:Europe", "region:Oceania", "region:America"]

class TournamentData(TypedDict):
    id: str
    name: str
    short: str
    latest: int
    tag: list[TournamentTag]
    url: str

class Motion(TypedDict):
    url: str
    text: str
    reference: str
    info_slide: str
    info_slide_plain: str

class MotionStats(TypedDict):
    type_: str
    value: list[int]

class RoundMotion(TypedDict):
    motion: Motion
    seq: int
    stats: list[MotionStats]

class Round(TypedDict):
    url: str
    seq: int
    motions: list[RoundMotion]
    name: str
    pretty_name: str

class TournamentYear(TypedDict):
    name: str
    rounds: list[Round]

class TournamentGroup(TypedDict):
    name: str
    tournaments: list[TournamentYear]