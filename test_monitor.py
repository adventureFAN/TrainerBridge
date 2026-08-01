from core.process_monitor import ProcessMonitor


monitor = ProcessMonitor()


print("Warte auf Spiel...")


runtime = monitor.wait_for_game("2679460")


if runtime:

    print()
    print("===================================")
    print("Spiel erkannt!")
    print()
    print(runtime)
    print()
    print("PID:", runtime.pid)
    print("AppID:", runtime.appid)
    print("===================================")


else:

    print()
    print("Timeout.")
