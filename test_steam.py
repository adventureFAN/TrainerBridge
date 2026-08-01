from core.steam import get_steam_info


info = get_steam_info()


print("=== Steam Diagnose ===")
print()

print("Installationspfad:")
print(info["install_path"])

print()

print("Bibliotheken:")

for lib in info["libraries"]:

    print("-", lib)
