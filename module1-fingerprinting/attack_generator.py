# attack_generator.py — Generate 8 attacked versions of a source video for demo testing.
#
# Usage:
#   python attack_generator.py <source_video>
#   e.g. python attack_generator.py demo_videos/match1.mp4
#
# Output: demo_videos/attacks/<stem>_attack_<name>.mp4

import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], label: str) -> None:
    print(f"  [{label}] running...")
    result = subprocess.run(cmd, capture_output=True, shell=False)
    if result.returncode != 0:
        print(f"  [{label}] FAILED: {result.stderr.decode(errors='replace')[:200]}")
    else:
        print(f"  [{label}] done")


def generate_attacks(source: str) -> None:
    src = Path(source)
    if not src.exists():
        print(f"ERROR: file not found: {source}")
        sys.exit(1)

    out_dir = src.parent / "attacks"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = src.stem

    def out(name: str) -> str:
        return str(out_dir / f"{stem}_attack_{name}.mp4")

    print(f"Generating attacks for: {src.name}")
    print(f"Output dir: {out_dir}")

    # 1. Horizontal mirror
    run([
        "ffmpeg", "-i", str(src),
        "-vf", "hflip",
        "-c:a", "copy",
        out("mirror"), "-y", "-loglevel", "error"
    ], "mirror")

    # 2. Center crop 70%
    run([
        "ffmpeg", "-i", str(src),
        "-vf", "crop=iw*0.7:ih*0.7,scale=iw/0.7:ih/0.7",
        "-c:a", "copy",
        out("crop70"), "-y", "-loglevel", "error"
    ], "crop70")

    # 3. Hue rotation + saturation boost
    run([
        "ffmpeg", "-i", str(src),
        "-vf", "hue=h=45:s=1.5",
        "-c:a", "copy",
        out("recolor"), "-y", "-loglevel", "error"
    ], "recolor")

    # 4. 1.25x speed-up (video + audio)
    run([
        "ffmpeg", "-i", str(src),
        "-filter_complex", "[0:v]setpts=0.8*PTS[v];[0:a]atempo=1.25[a]",
        "-map", "[v]", "-map", "[a]",
        out("speedup125"), "-y", "-loglevel", "error"
    ], "speedup125")

    # 5. Muted (strip audio)
    run([
        "ffmpeg", "-i", str(src),
        "-an",
        "-c:v", "copy",
        out("muted"), "-y", "-loglevel", "error"
    ], "muted")

    # 6. Trimmed to first 15 seconds
    run([
        "ffmpeg", "-i", str(src),
        "-t", "15",
        "-c", "copy",
        out("trim15s"), "-y", "-loglevel", "error"
    ], "trim15s")

    # 7. Low-bitrate re-encode (simulate heavy compression)
    run([
        "ffmpeg", "-i", str(src),
        "-b:v", "200k", "-b:a", "64k",
        out("lowbitrate"), "-y", "-loglevel", "error"
    ], "lowbitrate")

    # 8. "PIRATE TV" text overlay
    run([
        "ffmpeg", "-i", str(src),
        "-vf", "drawtext=text='PIRATE TV':fontsize=36:fontcolor=white:x=10:y=10:box=1:boxcolor=black@0.5",
        "-c:a", "copy",
        out("logo"), "-y", "-loglevel", "error"
    ], "logo")

    print("\nAll attacks generated.")
    print(f"Files are in: {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python attack_generator.py <source_video>")
        sys.exit(1)
    generate_attacks(sys.argv[1])
