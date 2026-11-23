"""Run the B7a fixture on a Linux session with X11 and Wayland."""
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

from PIL import Image, ImageChops

probe = str(Path(sys.argv[1]).resolve())
out = Path(sys.argv[2]).resolve()
out.mkdir(exist_ok=True)
base = dict(os.environ, RUST_LOG="warn,gpui_wgpu=info", SEED="0")
base.pop("ZED_HEADLESS", None)
x11 = {k: v for k, v in base.items() if k != "WAYLAND_DISPLAY"}
wayland = {k: v for k, v in base.items() if k != "DISPLAY"}
restricted = ["bwrap", "--die-with-parent", "--ro-bind", "/", "/", "--dev",
              "/dev", "--proc", "/proc", "--"]
disabled = {"VK_DRIVER_FILES": "/dev/null", "__EGL_VENDOR_LIBRARY_FILENAMES": "/dev/null"}


def run(name, args, env):
    result = subprocess.run(
        ["timeout", "-k", "2s", "7s", *args], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    (out / f"{name}.log").write_text(result.stdout)
    lines = result.stdout.splitlines()
    frames = [int(line.split()[-1]) for line in lines if line.startswith("FRAME ")]
    summary = [line for line in lines if line.startswith(("HOST ", "OPEN_", "SCALE ", "OFFSCREEN_", "CAPTURE_"))]
    print(name, "exit", result.returncode, *summary, flush=True)
    if len(frames) > 1:
        deltas = [(b - a) / 1000 for a, b in zip(frames, frames[1:])]
        p95 = statistics.quantiles(deltas, n=20, method="inclusive")[18]
        print(len(frames), "callbacks, ms min/p50/p95/max:",
              *(round(x, 3) for x in (min(deltas), statistics.median(deltas), p95, max(deltas))), flush=True)
    if name.endswith("-idle"):
        print("root render calls:", lines.count("DRAW"), flush=True)
    return result.returncode


run("gpu-control", [probe, "offscreen"], base)
run("blocked-offscreen", [*restricted, probe, "offscreen"], base | disabled)
run("blocked-x11", [*restricted, probe, "open"], x11 | disabled)
run("blocked-wayland", [*restricted, probe, "open"], wayland | disabled)
run("blocked-headless-window", [*restricted, probe, "open"],
    base | disabled | {"ZED_HEADLESS": "1"})
run("software-egl-offscreen", [*restricted, probe, "offscreen"], base | disabled | {
    "__EGL_VENDOR_LIBRARY_FILENAMES": "/usr/share/glvnd/egl_vendor.d/50_mesa.json",
    "LIBGL_ALWAYS_SOFTWARE": "1",
})

headless = out / "headless.png"
screen = out / "x11.png"
headless_ok = run("paired-headless", [probe, "capture", str(headless)], base) == 0
screen_ok = False
with (out / "paired-x11.log").open("w") as log:
    capture_env = x11 | {"GPUI_X11_SCALE_FACTOR": "2"}
    proc = subprocess.Popen(
        [probe, "capture-live"], env=capture_env, stdout=log, stderr=subprocess.STDOUT,
    )
    try:
        found = subprocess.run(
            ["xdotool", "search", "--sync", "--onlyvisible", "--all", "--pid",
             str(proc.pid), "--name", "^GPUI B7a probe$"],
            env=x11, capture_output=True, text=True, timeout=3, check=True,
        )
        wid = found.stdout.splitlines()[0]
        time.sleep(0.3)
        subprocess.run(["import", "-window", wid, str(screen)], env=x11, timeout=3, check=True)
        screen_ok = True
    except (subprocess.SubprocessError, IndexError) as error:
        print("paired-x11 capture unavailable:", error, flush=True)
    finally:
        try:
            print("paired-x11 exit", proc.wait(timeout=8), flush=True)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            print("paired-x11 timeout", flush=True)

if headless_ok and screen_ok:
    # Exact RGB comparison; platform capture does not establish alpha parity.
    a = Image.open(headless).convert("RGB")
    b = Image.open(screen).convert("RGB")
    print("paired dimensions", a.size, b.size, flush=True)
    if a.size == b.size:
        diff = ImageChops.difference(a, b)
        pixels = sum(pixel != (0, 0, 0) for pixel in diff.get_flattened_data())
        print("RGB differing pixels", pixels, "of", a.width * a.height,
              "max channel delta", max(x[1] for x in diff.getextrema()), flush=True)
        print("control colors, headless vs X11:", *(f"{a.getpixel(p)} / {b.getpixel(p)}"
              for p in ((5, 5), (100, 100))), flush=True)

for backend, env in (("x11", x11), ("wayland", wayland)):
    for mode in ("idle", "cadence", "loaded"):
        run(f"{backend}-{mode}", [probe, mode], env)
