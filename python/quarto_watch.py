#!/usr/bin/env python3
"""
Quarto QMD 文件监控脚本
监控指定 qmd 文件，检测到修改后自动运行 quarto render
"""

import argparse
import hashlib
import logging
import subprocess
import sys
import time
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_file_hash(filepath: Path) -> str:
    """计算文件的 MD5 哈希值"""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        md5.update(f.read())
    return md5.hexdigest()


def run_quarto_render(qmd_path: Path) -> bool:
    """运行 quarto render 命令"""
    try:
        logger.info(f"开始渲染 {qmd_path.name} ...")
        result = subprocess.run(
            ['quarto', 'render', str(qmd_path)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("渲染完成")
            return True
        else:
            logger.error("渲染失败")
            logger.error(f"错误输出: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"执行出错: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='监控 qmd 文件，修改后自动运行 quarto render'
    )
    parser.add_argument(
        'qmd_file',
        type=Path,
        help='要监控的 qmd 文件路径'
    )
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=5,
        help='检查间隔（秒），默认 5 秒'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='静默模式，仅在检测到修改时输出'
    )

    args = parser.parse_args()

    qmd_path = args.qmd_file.resolve()

    # 检查文件是否存在
    if not qmd_path.exists():
        logger.error(f"文件不存在: {qmd_path}")
        sys.exit(1)

    if not qmd_path.suffix == '.qmd':
        logger.warning(f"文件扩展名不是 .qmd")

    if not args.quiet:
        logger.info(f"监控文件: {qmd_path}")
        logger.info(f"检查间隔: {args.interval} 秒")
        logger.info(f"按 Ctrl+C 停止监控")

    # 记录初始哈希值
    last_hash = get_file_hash(qmd_path)

    try:
        while True:
            time.sleep(args.interval)

            # 检查文件是否存在
            if not qmd_path.exists():
                logger.warning("文件已被删除，停止监控")
                break

            # 计算当前哈希值
            current_hash = get_file_hash(qmd_path)

            if current_hash != last_hash:
                logger.info("检测到文件已修改")
                last_hash = current_hash
                run_quarto_render(qmd_path)

    except KeyboardInterrupt:
        logger.info("监控已停止")


if __name__ == '__main__':
    main()
