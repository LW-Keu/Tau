import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "tau_coding" / "scripts" / "start_scheduler.sh"


def _function_prefix():
    text = SCRIPT.read_text(encoding="utf-8")
    return text.split("#                    主流程", 1)[0]


def _run_functions(command):
    return subprocess.run(
        ["bash", "-c", f"{_function_prefix()}\n{command}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


class SchedulerScriptTests(unittest.TestCase):
    def test_extract_pids_reads_only_ss_users_pid_values(self):
        ss_output = (
            'tcp LISTEN 0 4096 pid=7 127.0.0.1:45762 0.0.0.0:* '
            'users:(("python3",pid=4242,fd=8),("python3",pid=4242,fd=9))'
        )

        result = _run_functions(f"extract_pids '{ss_output}'")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "4242")

    def test_pid_safety_rejects_reserved_and_unverified_processes(self):
        result = _run_functions(
            """
            for pid in 0 1 $$ $PPID; do
                if is_verified_scheduler_pid "$pid"; then exit 10; fi
            done
            sleep 30 & other=$!
            if is_verified_scheduler_pid "$other"; then kill "$other"; exit 11; fi
            kill "$other"
            wait "$other" 2>/dev/null || true
            """
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_identity_is_reverified_immediately_before_sigkill(self):
        result = _run_functions(
            """
            checks=0
            signals=""
            is_verified_scheduler_pid() {
                checks=$((checks + 1))
                [ "$checks" -eq 1 ]
            }
            kill() {
                [ "$1" = "-0" ] && return 0
                signals="${signals} $1"
            }
            sleep() { :; }
            info() { :; }
            warn() { :; }
            error() { :; }

            terminate_verified_scheduler_pid 4242
            printf '%s\n' "$checks|${signals# }"
            """
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "2|-15")


if __name__ == "__main__":
    unittest.main()
