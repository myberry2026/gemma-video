#!/usr/bin/env python3
"""
Pulls each app's 20 raw frames from the phone, sends them to host LM Studio
(Gemma-4-E2B) for narrative curation (20 -> 7 + summary), and writes the
result JSON back to the phone's metadata/ directory so the Storyboard tab
renders the Gemma-curated view.
"""
import base64
import io
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

from PIL import Image
import requests

DEVICE = sys.argv[1] if len(sys.argv) > 1 else "ZA2232T6XT"
RAW_DIR_DEVICE = "/sdcard/AetherLens/raw"
META_DIR_DEVICE = "/sdcard/AetherLens/metadata"
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL_ID = "google/gemma-4-e2b"
WORK = Path("/tmp/gemma_demo_curate")
WORK.mkdir(exist_ok=True, parents=True)


def adb(*args, capture=True):
    cmd = ["adb", "-s", DEVICE, *args]
    if capture:
        return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    subprocess.run(cmd, check=True)


def list_raw_by_app():
    out = adb("shell", f"ls {RAW_DIR_DEVICE}").strip().splitlines()
    by_app = defaultdict(list)
    for name in out:
        name = name.strip()
        if not name.endswith(".png"):
            continue
        # <pkg>_<YYYYMMDD>_<HHMMSS>.png
        m = re.match(r"^(.+)_(\d{8})_(\d{6})\.png$", name)
        if not m:
            continue
        pkg = m.group(1)
        by_app[pkg].append(name)
    for pkg in by_app:
        by_app[pkg].sort()
    return by_app


def pull_app_frames(pkg, names, max_frames=20):
    """Pull last N frames from phone to local, downscaled JPEG for the API."""
    chosen = names[-max_frames:]
    local_paths = []
    for n in chosen:
        local = WORK / f"{pkg}_{n}"
        if not local.exists():
            adb("pull", f"{RAW_DIR_DEVICE}/{n}", str(local), capture=False)
        local_paths.append(local)
    return chosen, local_paths


def to_b64_jpeg(path, max_dim=512, quality=75):
    img = Image.open(path).convert("RGB")
    img.thumbnail((max_dim, max_dim))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode()


PROMPT = """\
You are curating a daily-recap storyboard for app "{app}".
Below are {n} sequential screenshots (indices 0..{nm1}).

Pick the 7 most representative and DIVERSE frames that tell the story of what
happened in this session. Avoid near-duplicates.

Respond ONLY with one JSON object:
{{"selected_indices":[i1,i2,i3,i4,i5,i6,i7],"summary":"<one concise sentence in english>"}}
"""


def curate_app(pkg, names, local_paths):
    parts = [{"type": "text", "text": PROMPT.format(app=pkg, n=len(local_paths), nm1=len(local_paths)-1)}]
    for i, p in enumerate(local_paths):
        parts.append({"type": "text", "text": f"Frame {i}:"})
        parts.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + to_b64_jpeg(p)}})

    payload = {
        "model": MODEL_ID,
        "messages": [{"role": "user", "content": parts}],
        "temperature": 0.2,
        "max_tokens": 3500,
    }

    t0 = time.time()
    r = requests.post(LM_STUDIO_URL, json=payload, timeout=300)
    r.raise_for_status()
    res = r.json()
    msg = res["choices"][0]["message"]
    body = (msg.get("content") or "") + "\n" + (msg.get("reasoning_content") or "")

    # Extract the last balanced JSON object that contains selected_indices
    parsed = None
    for m in re.finditer(r"\{[^{}]*\"selected_indices\"[^{}]*\}", body, re.DOTALL):
        try:
            parsed = json.loads(m.group(0))
        except Exception:
            continue
    if parsed is None:
        # Looser: find first {...} block at end
        last = re.findall(r"\{.*?\}", body, re.DOTALL)
        for m in reversed(last):
            try:
                parsed = json.loads(m)
                if "selected_indices" in parsed:
                    break
            except Exception:
                parsed = None

    elapsed = time.time() - t0
    if not parsed or "selected_indices" not in parsed:
        # Fallback: even sampling
        step = max(1, len(local_paths) // 7)
        parsed = {
            "selected_indices": list(range(0, len(local_paths), step))[:7],
            "summary": f"Activity captured in {pkg}.",
            "fallback": True,
        }
    parsed.setdefault("summary", f"Activity captured in {pkg}.")
    parsed["selected_indices"] = parsed["selected_indices"][:7]
    parsed["curated_at"] = int(time.time())
    parsed["latency_sec"] = round(elapsed, 1)
    return parsed


def push_metadata(pkg, recap):
    local = WORK / f"{pkg}_recap.json"
    local.write_text(json.dumps(recap, ensure_ascii=False, indent=2))
    adb("shell", f"mkdir -p {META_DIR_DEVICE}", capture=False)
    adb("push", str(local), f"{META_DIR_DEVICE}/{pkg}_recap.json", capture=False)


def main():
    by_app = list_raw_by_app()
    if not by_app:
        print("No raw frames found on device. Run ./stage_demo.sh first.")
        sys.exit(1)

    # Skip the meta noise even if it shows up
    noise = {"com.gemma.videomemory", "com.motorola.launcher3", "unknown",
             "com.google.android.googlequicksearchbox"}
    targets = sorted(p for p in by_app if p not in noise)

    print(f"Curating {len(targets)} apps via {LM_STUDIO_URL}")
    for i, pkg in enumerate(targets, 1):
        names = by_app[pkg]
        chosen_names, local_paths = pull_app_frames(pkg, names)
        print(f"[{i}/{len(targets)}] {pkg}  ({len(local_paths)} frames)... ", end="", flush=True)
        try:
            recap = curate_app(pkg, chosen_names, local_paths)
            push_metadata(pkg, recap)
            tag = "fallback" if recap.get("fallback") else "Gemma"
            print(f"{tag} ✓ {recap['latency_sec']}s")
            print(f"    summary: {recap['summary'][:90]}")
            print(f"    indices: {recap['selected_indices']}")
        except Exception as e:
            print(f"FAIL: {e}")

    print("\nDone. Storyboard tab should now show Gemma-curated views per app.")


if __name__ == "__main__":
    main()
