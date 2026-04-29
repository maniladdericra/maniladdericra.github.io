#!/usr/bin/env python3
"""Replace website videos with generated orbit videos.

The website keeps videos in a curated category/level directory structure.
This script preserves those destination paths and filenames, replacing the
file contents when a source task video has a matching website video. If a
matching file does not already exist, the destination path is derived from
index.html's VIDEO_DATA so tasks that previously showed "No Video" can be
populated without hand-maintaining a second task map.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


DEFAULT_SOURCE = Path("/mnt/gck/maniladder_dataset_orbit_all")
DEFAULT_DESTINATION = Path(__file__).resolve().parent / "videos"
INDEX_HTML = Path(__file__).resolve().parent / "index.html"

TASK_RE = re.compile(r'"([^"]+)"')


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


def collect_video_data_destinations(destination_root: Path, index_html: Path) -> dict[str, Path]:
    videos: dict[str, Path] = {}
    current_type: str | None = None
    current_category: str | None = None
    in_video_data = False

    for line in index_html.read_text().splitlines():
        if line.startswith("const VIDEO_DATA = {"):
            in_video_data = True
            continue
        if in_video_data and line.startswith("};"):
            break
        if not in_video_data:
            continue

        type_match = re.match(r"^    (rigid_body|deformable_object): \{$", line)
        if type_match:
            current_type = type_match.group(1)
            continue

        category_match = re.match(
            r"^        (single_arm_gripper|single_arm_dexterous|dual_arm_gripper|dual_arm_dexterous): \{$",
            line,
        )
        if category_match:
            current_category = category_match.group(1)
            continue

        level_match = re.match(r"^            ([1-4]): \[(.*)\],?$", line)
        if not level_match or current_type is None or current_category is None:
            continue

        level = level_match.group(1)
        for task in TASK_RE.findall(level_match.group(2)):
            rel_path = Path(current_type) / f"level_{level}" / current_category / f"{task}.mp4"
            videos[task.lower()] = destination_root / rel_path

    return videos


def replace_videos(source_root: Path, destination_root: Path, dry_run: bool) -> tuple[int, list[str]]:
    source_videos = collect_source_videos(source_root)
    destination_videos = collect_destination_videos(destination_root)
    video_data_destinations = collect_video_data_destinations(destination_root, INDEX_HTML)

    replaced = 0
    missing: list[str] = []

    for task_name, source_video in source_videos.items():
        destination_video = destination_videos.get(task_name)
        if destination_video is None:
            destination_video = video_data_destinations.get(task_name)
            if destination_video is None:
                missing.append(source_video.parent.parent.name)
                continue

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
