import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_DIR = Path(__file__).parent
DATA_DIR = INTEGRATION_DIR / "data"
FEED_PATH = DATA_DIR / "test_feed_1.xml"
BACKUP_PATH = FEED_PATH.with_suffix(".xml.bak")
OUTPUT_DIR = INTEGRATION_DIR / "last_test_e2e_report"
HTTP_BASE = "http://localhost:8000/"

# 0. Ensure port 8000 is free
print("[INFO] Checking if port 8000 is in use...")
try:
    result = subprocess.run(["lsof", "-ti", ":8000"], capture_output=True, text=True)
    pids = result.stdout.strip().split("\n")
    for pid in pids:
        if pid:
            print(f"[INFO] Killing process {pid} using port 8000")
            os.kill(int(pid), signal.SIGTERM)
    if any(pid for pid in pids if pid):
        time.sleep(1)  # Give the OS a moment to release the port
except Exception as e:
    print(f"[WARN] Could not check/kill process on port 8000: {e}")

# Clean up: delete the test DB
DB_PATH = PROJECT_ROOT / "tests" / "integration" / "data" / "hex_machina_test.db"
if DB_PATH.exists():
    print(f"[INFO] Deleting test DB: {DB_PATH}")
    DB_PATH.unlink()
if OUTPUT_DIR.exists():
    print(f"[INFO] Deleting output directory: {OUTPUT_DIR}")
    shutil.rmtree(OUTPUT_DIR)
print("[INFO] Done.")

# 1. Start the HTTP server in the background
print("[INFO] Starting local HTTP server on port 8000...")
server_proc = subprocess.Popen(["python", "-m", "http.server", "8000"], cwd=DATA_DIR)

time.sleep(1)  # Give the server a moment to start

try:
    # 2. Run the ingestion pipeline with the test config
    print("[INFO] Running ingestion pipeline with integration_scraping_config.yaml...")
    result = subprocess.run(
        [
            "poetry",
            "run",
            "python",
            "-m",
            "src.hex_machina.ingestion.ingestion_script",
            "--config",
            str(INTEGRATION_DIR / "integration_scraping_config.yaml"),
            "--output-dir",
            str(OUTPUT_DIR),
        ],
        cwd=PROJECT_ROOT,
    )
    print(f"[INFO] Ingestion pipeline exited with code {result.returncode}")

    # 3. Run pytest to verify the ingested data
    print("[INFO] Running pytest to verify the ingested data...")
    pytest_result = subprocess.run(
        [
            "poetry",
            "run",
            "pytest",
            "-s",
            str(PROJECT_ROOT / "tests" / "ingestion" / "check_ingestion_pipeline.py"),
        ],
        cwd=PROJECT_ROOT,
    )
    print(f"[INFO] Pytest exited with code {pytest_result.returncode}")
finally:
    # 4. Shut down the HTTP server
    print("[INFO] Shutting down local HTTP server...")
    server_proc.terminate()
    try:
        server_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_proc.kill()
    # Clean up: delete the test DB
    if DB_PATH.exists():
        print(f"[INFO] Deleting test DB: {DB_PATH}")
        DB_PATH.unlink()
    print("[INFO] Done.")
