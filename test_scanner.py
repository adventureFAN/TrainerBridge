from core.scanner import scan_all_games


games = scan_all_games()


print()
print("=== Proton Trainer Manager Scan ===")
print()


for game in games:

    print(game.name)
    print("AppID:", game.appid)
    print("Status:", game.status)

    if game.proton_name:

        print(
            "Proton:",
            game.proton_name,
            "(",
            game.proton_version,
            ")"
        )

    else:

        print(
            "Proton: Nicht erkannt"
        )

    if game.trainer_path:

        print(
            "Trainer:",
            game.trainer_path
        )

    else:

        print(
            "Trainer: Keiner"
        )

    print("-" * 40)
