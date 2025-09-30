#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "transformers",
# ]
# ///
"""
文件 token 统计工具
使用 DeepSeek tokenizer 统计文件的 token 数量
"""

import argparse
import os
import sys
from pathlib import Path
from transformers import AutoTokenizer


def count_tokens_in_file(file_path, tokenizer, encoding="utf-8"):
    """
    统计单个文件的 token 数量

    Args:
        file_path: 文件路径
        tokenizer: tokenizer 实例
        encoding: 文件编码

    Returns:
        token_count: token 数量
    """
    try:
        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()

        # 使用 tokenizer 编码文本
        tokens = tokenizer.encode(content)
        return len(tokens)

    except FileNotFoundError:
        raise FileNotFoundError(f"文件不存在: {file_path}")
    except UnicodeDecodeError:
        raise UnicodeDecodeError(f"无法使用编码 {encoding} 读取文件: {file_path}")
    except Exception as e:
        raise Exception(f"处理文件时出错: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="使用 DeepSeek tokenizer 统计文件的 token 数量",
        usage="python count_tokens.py FILE [FILE ...] [--encoding ENCODING]",
    )

    # 必需参数 - 文件路径
    parser.add_argument("files", nargs="+", help="要统计 token 数量的文件路径")

    # 可选参数 - 编码
    parser.add_argument("--encoding", default="utf-8", help="文件编码 (默认: utf-8)")

    args = parser.parse_args()

    # 检查文件是否存在
    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"错误: 文件不存在 {file_path}")
            sys.exit(1)

    try:
        # 加载 tokenizer
        print("正在加载 tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(Path(__file__).parent, trust_remote_code=True)
        print("tokenizer 加载成功")
    except Exception as e:
        print(f"错误: 无法加载 tokenizer: {e}")
        sys.exit(1)

    # 统计每个文件的 token 数量
    total_tokens = 0
    successful_files = 0

    for file_path in args.files:
        try:
            token_count = count_tokens_in_file(file_path, tokenizer, args.encoding)
            print(f"{file_path}: {token_count} tokens")
            total_tokens += token_count
            successful_files += 1
        except Exception as e:
            print(f"错误: {e}")

    # 输出总计（如果处理了多个文件）
    if successful_files > 1:
        print(f"总计: {total_tokens} tokens")

    if successful_files == 0:
        print("错误: 没有成功处理任何文件")
        sys.exit(1)


if __name__ == "__main__":
    main()
