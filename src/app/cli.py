import argparse
from pathlib import Path
from .app import AutoMotionsApp
from .interface import CLIInterface
from .types import TournamentTagList

def main():
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--url", "-u", type=str, help="The URL of tabbycat tournament page", required=True)
    parent.add_argument("--year", "-y", type=int, help="The year of the tournament", required=True)
    parent.add_argument("--id", "-i", type=str, help="The ID of the tournament visible in tokyodebate/motions repository", required=True)
    parent.add_argument("--slug", type=str, help="Tournament slug visible in tabbycat")
    parent.add_argument("--type", type=str, help="The type of the tournament", choices=["NA", "Asian", "BP"])
    parent.add_argument("--dir", type=lambda x: Path(x).resolve(), help="The path of the motions directory", default=".")
    
    parser = argparse.ArgumentParser(description="Automatically fetches motion statistics data from tabbycat")
    subparsers = parser.add_subparsers(dest="create_or_update")
    # Create tournament
    create_parser = subparsers.add_parser("create", parents=[parent])
    create_parser.add_argument("--name", type=str, help="The name of the tournament", required=True)
    create_parser.add_argument("--short", type=str, help="The short name of the tournament")
    create_parser.add_argument("--tag", type=str, help="The tag of the tournament", required=True, choices=TournamentTagList, nargs="+")
    create_parser.add_argument("--path", type=str, help="The path of the tournament file", required=True)
    # Update tournament
    update_parser =subparsers.add_parser("update", parents=[parent])
    update_parser.add_argument("--location", type=int, help="The save position of the tournament", nargs=2, default=[0, 0])
    args = parser.parse_args()
    interface: CLIInterface
    if args.create_or_update == "create":
        interface = CLIInterface(
            args.url,
            args.year,
            args.id,
            "create",
            tabbycat_tournament_slug=args.slug,
            tournament_type=args.type,
            output_path=args.dir,
            new_name=args.name,
            new_short=args.short,
            new_tag=args.tag,
            new_url=args.path,
            save_pos=(0, 0),
        )
    else:
        interface = CLIInterface(
            args.url,
            args.year,
            args.id,
            "update",
            tabbycat_tournament_slug=args.slug,
            tournament_type=args.type,
            output_path=args.dir,
            save_pos=tuple(args.location),
        )
    
    app = AutoMotionsApp(interface)
    app.run()

if __name__ == "__main__":
    main()