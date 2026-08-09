import os
import signal
import time


def _process_group_exists(process_group):
    if process_group is None:
        return False

    try:
        os.killpg(int(process_group), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, ValueError):
        return False

    return True


def trainer_process_is_running(process, process_group=None):
    """Return True while the trainer wrapper or its process group is alive."""
    if process is None:
        return False

    if process.poll() is None:
        return True

    return _process_group_exists(process_group)


def request_trainer_process_stop(
    process,
    process_group=None,
    force=False,
):
    """Request trainer shutdown without waiting for it to finish.

    TrainerBridge launches trainers in their own Unix session/process group.
    Stopping the whole group prevents a Proton wrapper from exiting while the
    actual Wine trainer process remains behind.
    """
    if not trainer_process_is_running(process, process_group):
        return False

    signal_to_send = signal.SIGKILL if force else signal.SIGTERM

    if process_group is not None:
        try:
            os.killpg(int(process_group), signal_to_send)
            return True
        except ProcessLookupError:
            return False
        except (PermissionError, OSError, ValueError):
            pass

    try:
        if force:
            process.kill()
        else:
            process.terminate()
    except ProcessLookupError:
        return False

    return True


def stop_trainer_process(
    process,
    process_group=None,
    timeout=3.0,
):
    """Stop a trainer process group, escalating to SIGKILL if necessary.

    This blocking helper is intended for worker-thread cleanup paths. GUI
    lifecycle monitoring uses request_trainer_process_stop() instead.
    """
    if not trainer_process_is_running(process, process_group):
        return True

    request_trainer_process_stop(
        process,
        process_group=process_group,
        force=False,
    )

    deadline = time.monotonic() + max(0.0, float(timeout))

    while trainer_process_is_running(process, process_group):
        if time.monotonic() >= deadline:
            break
        time.sleep(0.05)

    if trainer_process_is_running(process, process_group):
        request_trainer_process_stop(
            process,
            process_group=process_group,
            force=True,
        )

        force_deadline = time.monotonic() + 1.0

        while trainer_process_is_running(process, process_group):
            if time.monotonic() >= force_deadline:
                break
            time.sleep(0.05)

    return not trainer_process_is_running(process, process_group)
