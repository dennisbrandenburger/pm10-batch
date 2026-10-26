"""Measure one Docker Compose run. Requires only the host Python standard library."""

import datetime
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = root / "evidence"
out.mkdir(exist_ok=True)
name = "pm10-measure-" + uuid.uuid4().hex[:10]
compose = ["docker", "compose"]
if subprocess.run(compose + ["version"], capture_output=True).returncode:
    compose = ["docker-compose"]
started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
if shutil.disk_usage(root).free < 2 * 1024**3:
    raise SystemExit("At least 2 GiB free host disk required before this measured run")
started = time.monotonic()
stop_reason = None
samples = []
with (out / "full-run.log").open("w") as log:
    process = subprocess.Popen(
        compose + ["run", "--name", name, "transform", "run", "--year", "2024"],
        cwd=root,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    while process.poll() is None:
        if shutil.disk_usage(root).free < 1024**3:
            stop_reason = "Host disk reserve below 1 GiB; stopped before further processing"
            subprocess.run(["docker", "stop", "--timeout", "3", name], capture_output=True)
            break
        stat = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}", name],
            capture_output=True,
            text=True,
        )
        if stat.returncode == 0 and stat.stdout.strip():
            samples.append(
                {
                    "elapsed_s": round(time.monotonic() - started, 1),
                    "host_free_bytes": shutil.disk_usage(root).free,
                    "container": json.loads(stat.stdout),
                }
            )
        time.sleep(2)
    code = process.wait()
inspection = subprocess.run(
    ["docker", "inspect", name, "--format", "{{json .State}}"],
    capture_output=True,
    text=True,
)
state = json.loads(inspection.stdout) if inspection.returncode == 0 else None
result = {
    "started_at": started_at,
    "stop_reason": stop_reason,
    "exit_code": code,
    "elapsed_seconds": round(time.monotonic() - started, 2),
    "sampling_note": "Docker stats approximately every 3 seconds; sampled usage is not an exact peak.",
    "container_state": state,
    "samples": samples,
}
(out / "resources.json").write_text(json.dumps(result, indent=2) + "\n")
subprocess.run(["docker", "rm", name], check=False, capture_output=True)
print(json.dumps({k: v for k, v in result.items() if k != "samples"}, indent=2))
raise SystemExit(code)
