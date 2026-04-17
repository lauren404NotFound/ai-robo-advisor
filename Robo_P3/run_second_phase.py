import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORTFOLIOS_DIR = ROOT / "portfolios"

if not PORTFOLIOS_DIR.is_dir():
    raise FileNotFoundError(f"[run_second_phase] 'portfolios' folder not found at: {PORTFOLIOS_DIR}")

SECOND_PHASE_SCRIPTS = [
    "special_portfolios.py",
    "diq_mvo.py",
    "diq_mvo_performance.py",
    "diq_hyperparameters.py",
    "dynamic_special_weights.py",
]

def main() -> int:
    print(f"[run_second_phase] Using portfolios dir: {PORTFOLIOS_DIR}")
    print(f"[run_second_phase] Project root        : {ROOT}")
    print("[run_second_phase] Starting second-phase pipeline...\\n")

    for script in SECOND_PHASE_SCRIPTS:
        path = ROOT / script
        if not path.is_file():
            print(f"[run_second_phase] WARNING: {script} not found at {path}. Skipping.")
            continue

        print(f"[run_second_phase] Running {script} ...")
        try:
            subprocess.run([sys.executable, str(path)], check=True)
            print(f"[run_second_phase] {script} completed.\\n")
        except subprocess.CalledProcessError as e:
            print(f"[run_second_phase] {script} failed with exit code {e.returncode}. Aborting.")
            return e.returncode

    print("[run_second_phase] All second-phase scripts completed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
