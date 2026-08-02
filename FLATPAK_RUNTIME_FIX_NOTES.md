# Steam Flatpak runtime fix

Fixes `AttributeError: 'GameRuntime' object has no attribute 'instance'` after a Steam Flatpak game was successfully detected.

`GameRuntime` stores the sandbox identifier as `flatpak_instance`. The trainer launcher now passes that identifier explicitly to the Flatpak command builder instead of passing the full runtime object and expecting an `instance` attribute.
