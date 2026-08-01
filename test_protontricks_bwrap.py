from core.protontricks import ProtontricksManager


APPID = "1086940"


print("=== TrainerBridge Protontricks bwrap fallback test ===")
print()

manager = ProtontricksManager.detect()

if not manager:
    raise SystemExit("Protontricks was not found.")

print("Detected installation:")
print(manager.installation.display_name)
print()

print("Reading installed components for Baldur's Gate 3...")

installed = manager.list_installed(APPID)

print()
print("Command succeeded.")
print("Used --no-bwrap fallback:", manager.used_no_bwrap_fallback)
print("Recorded components:", len(installed))

if installed:
    print()
    for component in sorted(installed):
        print("-", component)
