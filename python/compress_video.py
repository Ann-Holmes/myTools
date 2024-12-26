from pathlib import Path
from subprocess import run

"""
input_files: 输出的视频文件列表
output_files: 输出的视频文件列表

请在下面编写代码来获取这两个文件列表
"""
video_dir = Path("/Users/ender/work/PRJZ/videos")
input_files = sorted(video_dir.glob("2024-1*.mov"))
output_files = [video_dir / f"{f.stem}_compressed.mp4" for f in input_files]

for input_file, output_file in zip(input_files, output_files):
    print(f"Precossing {input_file} to {output_file}")
    run([
        "ffmpeg",
        "-i", str(input_file),
        "-vcodec", "libx264",
        "-crf", "23",
        "-preset", "medium",
        "-acodec", "aac",
        "-b:a", "192k",
        "-c:s", "copy",
        "-map", "0",
        # "-map", "0:s:3",
        # "-map", "0:s:4",
        str(output_file)
    ])
