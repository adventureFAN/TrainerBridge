from core.games import find_games
from core.steam import get_steam_libraries
from core.proton import apply_proton_info
from core.trainer_manager import apply_trainer_info

from launcher import build_trainer_command

import os


games = find_games(get_steam_libraries())


for game in games:

    apply_proton_info(game)
    apply_trainer_info(game)

    if game.name == "Metaphor: ReFantazio":

        command = build_trainer_command(game)

        print(command)

        os.system(command)

        break
