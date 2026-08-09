import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(PROJECT_ROOT)
)

from core.single_instance import (  # noqa: E402
    SingleInstanceLock
)


class SingleInstanceLockTests(unittest.TestCase):

    def setUp(self):

        self.tempdir = tempfile.TemporaryDirectory()
        self.lock_path = (
            Path(self.tempdir.name)
            / "trainerbridge-test.lock"
        )


    def tearDown(self):

        self.tempdir.cleanup()


    def test_first_instance_acquires_lock(self):

        lock = SingleInstanceLock(
            self.lock_path
        )

        try:

            self.assertTrue(
                lock.acquire()
            )

            self.assertTrue(
                lock.acquired
            )

            self.assertEqual(
                self.lock_path.read_text(
                    encoding="ascii"
                ),
                str(os.getpid())
            )

        finally:

            lock.release()


    def test_second_instance_is_rejected_while_lock_is_held(self):

        first = SingleInstanceLock(
            self.lock_path
        )
        second = SingleInstanceLock(
            self.lock_path
        )

        try:

            self.assertTrue(
                first.acquire()
            )

            self.assertFalse(
                second.acquire()
            )

            self.assertFalse(
                second.acquired
            )

        finally:

            second.release()
            first.release()


    def test_lock_can_be_acquired_after_clean_release(self):

        first = SingleInstanceLock(
            self.lock_path
        )
        second = SingleInstanceLock(
            self.lock_path
        )

        self.assertTrue(
            first.acquire()
        )

        first.release()

        try:

            self.assertTrue(
                second.acquire()
            )

        finally:

            second.release()


    def test_release_is_idempotent(self):

        lock = SingleInstanceLock(
            self.lock_path
        )

        self.assertTrue(
            lock.acquire()
        )

        lock.release()
        lock.release()

        self.assertFalse(
            lock.acquired
        )


    def test_kernel_releases_lock_when_holder_process_exits(self):

        holder_code = textwrap.dedent(
            """
            import sys
            import time
            from core.single_instance import SingleInstanceLock

            lock = SingleInstanceLock(sys.argv[1])

            if not lock.acquire():
                raise SystemExit(2)

            print("LOCKED", flush=True)
            time.sleep(60)
            """
        )

        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                holder_code,
                str(self.lock_path)
            ],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        try:

            self.assertEqual(
                process.stdout.readline().strip(),
                "LOCKED"
            )

            contender = SingleInstanceLock(
                self.lock_path
            )

            self.assertFalse(
                contender.acquire()
            )

            process.terminate()
            process.wait(timeout=5)

            recovered = SingleInstanceLock(
                self.lock_path
            )

            try:

                self.assertTrue(
                    recovered.acquire()
                )

            finally:

                recovered.release()

        finally:

            if process.poll() is None:

                process.kill()
                process.wait(timeout=5)

            if process.stdout is not None:
                process.stdout.close()

            if process.stderr is not None:
                process.stderr.close()


class SingleInstanceStartupTests(unittest.TestCase):

    def test_main_gates_normal_start_before_logging_and_main_window(self):

        source = (
            PROJECT_ROOT
            / "main.py"
        ).read_text(
            encoding="utf-8"
        )

        main_start = source.index(
            "def main():"
        )
        main_source = source[
            main_start:
        ]

        self_test_position = main_source.index(
            'if "--self-test" in sys.argv:'
        )
        lock_position = main_source.index(
            "instance_lock = SingleInstanceLock()"
        )
        acquire_position = main_source.index(
            "if not instance_lock.acquire():"
        )
        logging_position = main_source.index(
            "setup_logging()"
        )
        window_position = main_source.index(
            "window = MainWindow()"
        )

        self.assertLess(
            self_test_position,
            lock_position
        )
        self.assertLess(
            lock_position,
            acquire_position
        )
        self.assertLess(
            acquire_position,
            logging_position
        )
        self.assertLess(
            logging_position,
            window_position
        )


    def test_second_instance_path_never_constructs_main_window(self):

        source = (
            PROJECT_ROOT
            / "main.py"
        ).read_text(
            encoding="utf-8"
        )

        gate_start = source.index(
            "if not instance_lock.acquire():"
        )
        try_start = source.index(
            "    try:",
            gate_start
        )

        rejected_path = source[
            gate_start:try_start
        ]

        self.assertIn(
            "TrainerBridge is already running",
            rejected_path
        )

        self.assertNotIn(
            "MainWindow()",
            rejected_path
        )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )
