import sys
import traceback
import pyperclip
from yaspin import yaspin
import pandas as pd
from .interface import BaseInterface, TabbycatContext
from .motions import MotionManager
from .utils import tournament_year_to_lines, parse_round_table, parse_motion, parse_info

class AutoMotionsApp:
    def __init__(self, interface: BaseInterface):
        self.interface = interface
    
    def run(self):
        try:
            ctx = self.interface.get_context()
            motion_manager = MotionManager(ctx)
            data_year = motion_manager.get_data()
            output_formats = self.interface.get_output_format()
            if "clipboard_text" in output_formats:
                with yaspin(text="Copying to clipboard...", color="blue") as spinner:
                    try:
                        pyperclip.copy("\n".join(tournament_year_to_lines(data_year)))
                        spinner.text = "Copied to clipboard"
                        spinner.color = "green"
                        spinner.ok("✓")
                    except Exception as e:
                        spinner.text = "Failed to copy to clipboard"
                        spinner.color = "red"
                        spinner.fail("✗")
            if "clipboard_table" in output_formats:
                with yaspin(text="Copying to clipboard...", color="blue") as spinner:
                    try:
                        dt = [[None, None, None, data_year["name"], parse_round_table(round["pretty_name"]), None, None, parse_motion(motion["motion"]["text"]), parse_info(motion["motion"]["info_slide_plain"]) or None] for round in data_year["rounds"] for motion in round["motions"]]
                        df = pd.DataFrame(dt)
                        pyperclip.copy(df.to_csv(index=False, header=False, sep="\t"))
                        spinner.text = "Copied to clipboard"
                        spinner.color = "green"
                        spinner.ok("✓")
                    except Exception as e:
                        spinner.text = "Failed to copy to clipboard"
                        spinner.color = "red"
            if "git" in output_formats:
                path_repo = self.interface.get_git_repository(ctx)
                self.interface.handle_git(ctx, path_repo, data_year)
            
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            print("Terminating application...")
            sys.exit(1)
    
