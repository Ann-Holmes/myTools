#!/usr/bin/env python3
"""
Convert delimited text file to Markdown table format

Usage:
    uv run tsv2md.py input.tsv [output.md]
    uv run tsv2md.py input.csv output.md -d ","
    uv run tsv2md.py input.txt output.md -d " "

# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""

import argparse
import csv
import sys
from pathlib import Path


def to_markdown_table(input_file, output_file=None, delimiter="\t"):
    """Convert delimited file to Markdown table"""
    input_path = Path(input_file)

    if not input_path.exists():
        print(f"Error: File '{input_file}' not found", file=sys.stderr)
        sys.exit(1)

    # 读取文件
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            # 使用 csv 库读取
            reader = csv.reader(f, delimiter=delimiter)
            rows = list(reader)

        if not rows:
            print("Error: File is empty", file=sys.stderr)
            sys.exit(1)

        # 获取表头
        headers = rows[0]
        num_cols = len(headers)

        # 生成 Markdown 表格
        markdown_lines = []

        # 表头
        markdown_lines.append("| " + " | ".join(headers) + " |")

        # 分隔符
        markdown_lines.append("| " + " | ".join(["---"] * num_cols) + " |")

        # 数据行
        for row in rows[1:]:
            if row:  # 跳过空行
                # 确保列数一致
                while len(row) < num_cols:
                    row.append("")
                markdown_lines.append("| " + " | ".join(str(cell) for cell in row) + " |")

        markdown_content = "\n".join(markdown_lines)

        # 输出
        if output_file:
            output_path = Path(output_file)
            output_path.write_text(markdown_content, encoding="utf-8")
            print(f"Markdown table written to: {output_file}", file=sys.stderr)
        else:
            print(markdown_content)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Convert delimited text file to Markdown table format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s input.tsv                                    # TSV 文件，输出到 stdout
  %(prog)s input.tsv output.md                          # TSV 文件，输出到文件
  %(prog)s input.csv output.md -d ","                   # CSV 文件
  %(prog)s input.txt output.md -d " "                   # 空格分隔
  %(prog)s data.txt output.md -d "|"                    # 管道符分隔
        """,
    )

    parser.add_argument("input", help="Input file (TSV, CSV, or any delimited text file)")

    parser.add_argument(
        "output",
        nargs="?",
        help="Output Markdown file (optional, prints to stdout if not specified)",
    )

    parser.add_argument(
        "-d",
        "--delimiter",
        default="\t",
        help='Delimiter character (default: "\\t" for TSV). Use "," for CSV, " " for space-separated, etc.',
    )

    args = parser.parse_args()

    to_markdown_table(args.input, args.output, args.delimiter)


if __name__ == "__main__":
    main()
