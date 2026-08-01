from core.process_monitor import ProcessMonitor


APPID = "2679460"


print("=== Echte Game-EXE-Erkennung ===")
print()

print(
    "Starte Metaphor jetzt normal über Steam."
)

print(
    "Der Trainer wird bei diesem Test nicht gestartet."
)

print()


monitor = ProcessMonitor()


runtime = monitor.wait_for_game(
    APPID,
    timeout=120,
    interval=0.5,
    stable_seconds=5
)


if not runtime:

    print()
    print(
        "Die echte Spiel-EXE wurde nicht erkannt."
    )

    raise SystemExit(1)


print()
print(
    "Echte Spiel-EXE wurde erkannt:"
)

print(runtime)

print()

print("Spiel-EXE:")
print(runtime.game_executable)

print()

print("Spiel-PID:")
print(runtime.game_pid)

print()

print("Steam-Start-PID:")
print(runtime.launch_pid)
