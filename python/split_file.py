import hashlib
import argparse
from pathlib import Path


def calculate_md5(file_path):
    """计算文件的 MD5 值"""
    md5_hash = hashlib.md5()
    with file_path.open('rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def split_file(file_path, chunk_size, output_dir):
    """
    将文件按指定大小分割，并在指定输出目录生成分割文件和 MD5 校验文件
    :param file_path: 源文件路径 (Path 对象)
    :param chunk_size: 每个分块的大小（以字节为单位）
    :param output_dir: 输出文件夹路径 (Path 对象)
    """
    if not file_path.exists():
        print(f"文件 {file_path} 不存在")
        return

    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)

    part_files = []
    base_name = file_path.name

    # 分割文件
    with file_path.open('rb') as f:
        part_number = 1
        while chunk := f.read(chunk_size):
            part_file_name = output_dir / f"{base_name}.part{part_number:02}"
            with part_file_name.open('wb') as part_file:
                part_file.write(chunk)
            part_files.append(part_file_name)
            part_number += 1

    # 生成分割文件的 MD5 校验文件
    md5_file_path = output_dir / f"{base_name}.md5"
    with md5_file_path.open('w') as md5_file:
        for part_file in part_files:
            part_md5 = calculate_md5(part_file)
            md5_file.write(f"{part_md5}  {part_file.name}\n")

    # 生成原始文件的 MD5 校验文件
    original_md5 = calculate_md5(file_path)
    original_md5_file_path = output_dir / "original.md5"
    with original_md5_file_path.open('w') as original_md5_file:
        original_md5_file.write(f"{original_md5}  {base_name}\n")

    print(f"文件已分割为 {len(part_files)} 个部分，文件输出到: {output_dir}")
    print(f"分块文件的 MD5 校验文件: {md5_file_path}")
    print(f"原始文件的 MD5 校验值保存为: {original_md5_file_path}")


def main():
    parser = argparse.ArgumentParser(description="将大文件按指定大小分割，并生成 MD5 校验文件")
    parser.add_argument("file", type=Path, help="要分割的文件路径")
    parser.add_argument("chunk_size", type=int, help="每个分块的大小（单位：字节）")
    parser.add_argument("output_dir", type=Path, help="输出文件夹路径")
    args = parser.parse_args()

    split_file(args.file, args.chunk_size, args.output_dir)


if __name__ == "__main__":
    main()
