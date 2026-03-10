#!/usr/bin/env python3
"""
Convert UMI matrix to MTX format by sample.

This script converts a tab-separated UMI count matrix into MTX format,
splitting the data by sample. It uses a two-step approach:

1. **Split Phase**: Use the `cut` command to efficiently extract columns
   for each sample and compress them with gzip. This is fast and
   memory-efficient as it streams the file.

2. **Convert Phase**: Convert each sample file to MTX format in parallel
   using multiprocessing. Each sample gets:
   - matrix.mtx.gz: Sparse count matrix (Matrix Market format)
   - features.tsv.gz: Gene/feature names
   - barcodes.tsv.gz: Cell barcodes

The output format is compatible with Scanpy, Seurat, and other
single-cell analysis tools.

Example:
    python src/convert_to_mtx.py \\
        -i data/rawdata/GSE131907_Lung_Cancer_raw_UMI_matrix.txt \\
        -o data/processed/mtx \\
        -j 8
"""

from __future__ import annotations

import subprocess
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from scipy.io import mmwrite
from scipy.sparse import csr_matrix


def extract_sample_from_barcode(barcode: str) -> str:
    """
    Extract sample ID from a cell barcode.

    The barcode format is assumed to be: PREFIX_SAMPLE_SUFFIX
    where the sample is the last two underscore-separated parts.

    Args:
        barcode: Cell barcode string (e.g., "AAACCTGAGAAACCGC_LN_05")

    Returns:
        Sample ID (e.g., "LN_05")

    Examples:
        >>> extract_sample_from_barcode("AAACCTGAGAAACCGC_LN_05")
        'LN_05'
        >>> extract_sample_from_barcode("SIMPLE")
        'SIMPLE'
    """
    parts = barcode.split("_")
    if len(parts) >= 2:
        return "_".join(parts[-2:])
    return barcode


def read_header_columns(input_file: str | Path) -> List[str]:
    """
    Read the header line from a tab-separated file and extract column names.

    This uses Python's native file reading for efficiency and avoids
    shell command overhead.

    Args:
        input_file: Path to the input file.

    Returns:
        List of column names from the header line.

    Raises:
        FileNotFoundError: If the input file doesn't exist.
        ValueError: If the file is empty or has no valid header.
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    with input_path.open("r", encoding="utf-8") as f:
        first_line = f.readline().strip()

    if not first_line:
        raise ValueError(f"File is empty: {input_file}")

    columns = first_line.split("\t")
    return columns


def split_by_sample_awk(
    input_file: str | Path,
    output_dir: str | Path,
) -> Tuple[Path, List[str]]:
    """
    Split the input UMI matrix by sample using the `cut` command.

    This function performs Step 1 of the conversion pipeline:
    1. Reads the header to identify sample groups
    2. For each sample, extracts relevant columns using `cut`
    3. Compresses each sample file with gzip

    The `cut` command is used for efficiency as it streams the file
    and doesn't load it into memory.

    Args:
        input_file: Path to the input UMI matrix file (tab-separated).
        output_dir: Directory where temporary split files will be stored.

    Returns:
        A tuple of:
        - Path to the temporary split directory
        - List of sample names found

    Raises:
        FileNotFoundError: If input file doesn't exist.
        subprocess.CalledProcessError: If cut command fails.
    """
    output_path = Path(output_dir)
    temp_dir = output_path / "temp_split"

    temp_dir.mkdir(parents=True, exist_ok=True)

    print("Step 1: Splitting file by sample using cut...")

    # Read header using Python native method
    columns = read_header_columns(input_file)
    print(f"  Found {len(columns)} columns")

    # Build mapping: sample -> list of column indices (0-based)
    sample_to_cols: Dict[str, List[int]] = {}
    for idx, col in enumerate(columns):
        if col == "Index":
            continue
        sample = extract_sample_from_barcode(col)
        if sample not in sample_to_cols:
            sample_to_cols[sample] = []
        sample_to_cols[sample].append(idx)

    print(f"  Found {len(sample_to_cols)} unique samples")

    # Extract columns for each sample using cut command
    for sample, col_indices in sorted(sample_to_cols.items()):
        output_file = temp_dir / f"{sample}.txt.gz"

        if output_file.exists():
            print(f"  Skipping {sample} (already exists)")
            continue

        # Build column string for cut (1-based indexing)
        # Include column 1 (Index) plus sample columns
        cut_cols = [1] + [i + 1 for i in col_indices]
        col_str = ",".join(map(str, cut_cols))

        print(f"  Extracting {sample} ({len(col_indices)} columns)...")

        # Use cut command for efficient column extraction with gzip compression
        input_path = Path(input_file)
        cut_cmd = f"cut -f{col_str} '{input_path}' | gzip > '{output_file}'"
        subprocess.run(cut_cmd, shell=True, check=True)
        print(f"    Saved to {output_file}")

    print(f"  Splitting complete! Temporary files in: {temp_dir}")
    return temp_dir, sorted(sample_to_cols.keys())


def convert_sample_to_mtx(
    sample_file: str | Path,
    sample_name: str,
    output_dir: str | Path,
) -> Tuple[str, Tuple[int, int], int]:
    """
    Convert a single sample file to MTX format.

    This function performs the conversion for one sample:
    1. Reads the gzipped sample file
    2. Converts to sparse matrix format
    3. Writes MTX files (matrix, features, barcodes)
    4. Compresses all output files with gzip

    Args:
        sample_file: Path to the gzipped sample file.
        sample_name: Name of the sample (used for output directory).
        output_dir: Base directory for output files.

    Returns:
        A tuple of:
        - Sample name
        - Matrix shape (n_genes, n_cells)
        - Number of non-zero entries

    Raises:
        IOError: If file reading/writing fails.
    """
    output_path = Path(output_dir)
    sample_dir = output_path / sample_name
    sample_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Converting {sample_name} to MTX...")

    # Read the gzipped sample file
    df = pd.read_csv(sample_file, sep="\t", index_col=0, engine="pyarrow")

    # Convert to sparse matrix (CSR format)
    sparse_matrix = csr_matrix(df.values)

    # Define output file paths
    mtx_path = sample_dir / "matrix.mtx"
    features_path = sample_dir / "features.tsv"
    barcodes_path = sample_dir / "barcodes.tsv"

    # Write matrix in Matrix Market format
    mmwrite(str(mtx_path), sparse_matrix)

    # Write features file (gene names with ID and name columns)
    features_path.write_text(
        "".join(f"{gene}\t{gene}\n" for gene in df.index)
    )

    # Write barcodes file (extract just the barcode, remove sample suffix)
    barcodes_path.write_text(
        "".join(f"{barcode.split('_')[0]}\n" for barcode in df.columns)
    )

    # Compress all output files
    subprocess.run(f"gzip -f '{mtx_path}'", shell=True, check=True)
    subprocess.run(f"gzip -f '{features_path}'", shell=True, check=True)
    subprocess.run(f"gzip -f '{barcodes_path}'", shell=True, check=True)

    print(
        f"    {sample_name}: {df.shape[0]} genes x {df.shape[1]} cells, "
        f"{sparse_matrix.nnz} non-zero entries"
    )

    return sample_name, df.shape, sparse_matrix.nnz


def convert_samples_parallel(
    temp_dir: str | Path,
    samples: List[str],
    output_dir: str | Path,
    max_workers: int = 4,
) -> List[Tuple[str, Tuple[int, int], int]]:
    """
    Convert multiple sample files to MTX format in parallel.

    This function uses multiprocessing to convert samples concurrently,
    significantly speeding up the conversion process for large datasets.

    Args:
        temp_dir: Directory containing the temporary split files.
        samples: List of sample names to convert.
        output_dir: Base directory for output files.
        max_workers: Maximum number of parallel worker processes.

    Returns:
        List of conversion results, each containing:
        - Sample name
        - Matrix shape
        - Non-zero entry count
    """
    print(f"\nStep 2: Converting samples to MTX (using {max_workers} workers)...")

    temp_path = Path(temp_dir)
    sample_files = [str(temp_path / f"{s}.txt.gz") for s in samples]

    results: List[Tuple[str, Tuple[int, int], int]] = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all conversion jobs
        futures = {
            executor.submit(convert_sample_to_mtx, sf, s, output_dir): s
            for sf, s in zip(sample_files, samples)
        }

        # Collect results as they complete
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                sample = futures[future]
                print(f"  Error processing {sample}: {e}")

    return results


def main() -> int:
    """
    Main entry point for the UMI to MTX conversion script.

    This function orchestrates the two-step conversion process:
    1. Split the input file by sample
    2. Convert each sample to MTX format in parallel

    Returns:
        0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        description="Convert UMI matrix to sample-specific MTX format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-i",
        "--input",
        default="data/rawdata/GSE131907_Lung_Cancer_raw_UMI_matrix.txt",
        help="Input UMI matrix file (tab-separated)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="data/processed/mtx",
        help="Output directory for MTX files",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=4,
        help="Number of parallel jobs for conversion (default: 4)",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep temporary split files for debugging",
    )

    args = parser.parse_args()

    # Convert to Path objects and resolve to absolute paths
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    # Validate input file
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1

    try:
        # Step 1: Split by sample using cut
        temp_dir, samples = split_by_sample_awk(input_path, output_path)

        # Step 2: Convert to MTX in parallel
        results = convert_samples_parallel(
            temp_dir, samples, output_path, args.jobs
        )

        # Cleanup temporary files
        if not args.keep_temp:
            print("\nCleaning up temporary files...")
            # Remove temporary directory and all its contents
            for item in temp_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    for sub_item in item.iterdir():
                        sub_item.unlink()
                    item.rmdir()
            temp_dir.rmdir()

        print("\n✓ Conversion complete!")
        print(f"  Output directory: {output_path}")
        print(f"  Processed {len(results)} samples")

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
