#!/usr/bin/env python3
"""Replace website videos with generated orbit videos.

The website keeps videos in a curated category/level directory structure.
This script preserves those destination paths and filenames, replacing the
file contents when a source task video has a matching website video. A small
set of newer tasks is mapped explicitly because those files were not present
in the original website tree.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


DEFAULT_SOURCE = Path("/mnt/gck/maniladder_dataset_orbit_all")
DEFAULT_DESTINATION = Path(__file__).resolve().parent / "videos"

EXTRA_DESTINATIONS = {
    "dualarmpickcup-v1": Path("rigid_body/level_1/dual_arm_dexterous/DualArmPickCup-v1.mp4"),
    "dualarmthrowblock-v1": Path("rigid_body/level_2/dual_arm_dexterous/DualArmThrowBlock-v1.mp4"),
    "mazeblockpush-v1": Path("rigid_body/level_3/single_arm_gripper/MazeBlockPush-v1.mp4"),
    "stack6blocks-v1": Path("rigid_body/level_3/single_arm_gripper/Stack6Blocks-v1.mp4"),
}


def normalized_task_name(path: Path) -> str:
    return path.stem.lower()


def collect_source_videos(source_root: Path) -> dict[str, Path]:
    videos: dict[str, Path] = {}
    for video in sorted(source_root.glob("*/videos/*.mp4")):
        task_name = video.parent.parent.name.lower()
        if task_name in videos:
            raise ValueError(f"multiple source videos found for task {task_name!r}")
        videos[task_name] = video
    return videos


def collect_destination_videos(destination_root: Path) -> dict[str, Path]:
    videos: dict[str, Path] = {}
    for video in sorted(destination_root.rglob("*.mp4")):
        key = normalized_task_name(video)
        if key in videos:
            raise ValueError(f"multiple destination videos match task {key!r}")
        videos[key] = video
    return videos


def replace_videos(source_root: Path, destination_root: Path, dry_run: bool) -> tuple[int, list[str]]:
    source_videos = collect_source_videos(source_root)
    destination_videos = collect_destination_videos(destination_root)

    replaced = 0
    missing: list[str] = []

    for task_name, source_video in source_videos.items():
        destination_video = destination_videos.get(task_name)
        if destination_video is None:
            extra_destination = EXTRA_DESTINATIONS.get(task_name)
            if extra_destination is None:
                missing.append(source_video.parent.parent.name)
                continue
            destination_video = destination_root / extra_destination

        print(f"{source_video} -> {destination_video}")
        if not dry_run:
            destination_video.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_video, destination_video)
        replaced += 1

    return replaced, missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--dry-run", action="store_true", help="show replacements without copying")
    args = parser.parse_args()

    source_root = args.source.expanduser().resolve()
    destination_root = args.destination.expanduser().resolve()

    if not source_root.is_dir():
        raise SystemExit(f"source directory does not exist: {source_root}")
    if not destination_root.is_dir():
        raise SystemExit(f"destination directory does not exist: {destination_root}")

    replaced, missing = replace_videos(source_root, destination_root, args.dry_run)

    action = "would replace" if args.dry_run else "replaced"
    print(f"\n{action} {replaced} video(s)")
    if missing:
        print(f"missing destination video(s): {len(missing)}")
        for task_name in missing:
            print(f"  {task_name}")


if __name__ == "__main__":
    main()
