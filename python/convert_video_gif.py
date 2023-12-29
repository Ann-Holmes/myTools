#!/usr/bin/env python3
"""
This script is used to convert a video to a gif by using ffmpeg.
In addition, it can crop and cut the video before converting it to a gif.
"""
from typing import Tuple, List
import subprocess
import argparse
import json


def parse_coordinates(coordinates: str) -> Tuple[float]:
    return tuple(map(lambda x: float(x.strip()), coordinates.split(",")))


def parse_args():
    parser = argparse.ArgumentParser(
        description='Crop video with ffmpeg by the top left corner and the bottom right corner'
    )
    parser.add_argument(
        "-i", "--input", type=str, required=True,
        help="input video path"
    )
    parser.add_argument(
        "-o", "--output", type=str, required=True,
        help="output video path"
    )
    parser.add_argument(
        "--top_left", type=parse_coordinates, required=False, default="0.0,0.0",
        help="the coordinates of the top left corner of the crop area, "
             "separated by comma, e.g. 100,200."
             "If the value is from 0 to 1, it will be treated as a percentage of the video size."
             "Default: 0.0,0.0"
    )
    parser.add_argument(
        "--bottom_right", type=parse_coordinates, required=False, default="1.0,1.0",
        help="the coordinates of the bottom right corner of the crop area, "
             "separated by comma, e.g. 100,200. "
             "If the value is from 0 to 1, it will be treated as a percentage of the video size."
             "Default: 1.0,1.0"
    )
    parser.add_argument(
        "--ffmpeg", required=False, default="ffmpeg",
        help="ffmpeg path"
    )
    parser.add_argument(
        "--fps", required=False, default=10, type=int,
        help="fps of the output gif"
    )

    args = parser.parse_args()

    return args


def calculate_crop_parameters(
        top_left: Tuple[float], bottom_right: Tuple[float],
        video_size: Tuple[int], fps: int
) -> List[str]:
    if top_left[0] > bottom_right[0] or top_left[1] > bottom_right[1]:
        raise ValueError("top_left should be smaller than bottom_right")

    if int(top_left[0]) <= 1 and int(top_left[1]) <= 1:
        top_left = (top_left[0] * video_size[0], top_left[1] * video_size[1])
    if int(bottom_right[0]) <= 1 and int(bottom_right[1]) <= 1:
        bottom_right = (bottom_right[0] * video_size[0], bottom_right[1] * video_size[1])

    # ffmpeg crop filter requires the width:height:x:y format
    # where x and y are the coordinates of the top left corner of the crop area
    # and width and height are the width and height of the crop area
    w = int(bottom_right[0] - top_left[0])
    h = int(bottom_right[1] - top_left[1])
    x = int(top_left[0])
    y = int(top_left[1])
    return ["-vf", f"fps={fps},crop={w}:{h}:{x}:{y}"]


def get_video_size(ffmpeg: str, video_path: str) -> Tuple[int]:
    ffprobe = ffmpeg.split("ffmpeg")[0] + "ffprobe"

    cmd = [
        ffprobe,
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'json',
        video_path
    ]
    output = subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode("utf-8")

    video_info = json.loads(output)
    width = video_info["streams"][0]["width"]
    height = video_info["streams"][0]["height"]

    return width, height


def main():
    args = parse_args()

    video_size = get_video_size(args.ffmpeg, args.input)

    crop_parameters = calculate_crop_parameters(
        args.top_left, args.bottom_right, video_size, args.fps
    )

    cmd = [
        args.ffmpeg,
        "-i", args.input,
        *crop_parameters,
        "-c:v", "gif",
        args.output
    ]

    subprocess.run(cmd)


if __name__ == "__main__":
    main()
