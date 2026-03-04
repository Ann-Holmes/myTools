#!/usr/bin/env python
"""
Single-cell data preprocessing tool.

This script provides command-line interface for preprocessing single-cell RNA-seq data,
including filtering cells and genes based on various quality control metrics.
"""

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import scanpy as sc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments for single-cell preprocessing."""
    parser = argparse.ArgumentParser(
        description="Single-cell data preprocessing tool for quality control and filtering."
    )

    parser.add_argument(
        "-i", "--input",
        type=str,
        nargs="+",
        required=True,
        help="Input folders containing single-cell data files (required)"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default="./output",
        help="Output directory for processed data (default: ./output)"
    )

    parser.add_argument(
        "--min-genes",
        type=int,
        default=200,
        help="Minimum number of genes per cell (default: 200)"
    )

    parser.add_argument(
        "--min-cells",
        type=int,
        default=3,
        help="Minimum number of cells per gene (default: 3)"
    )

    parser.add_argument(
        "--max-mt-percent",
        type=float,
        default=5,
        help="Maximum percentage of mitochondrial genes allowed per cell (default: 5)"
    )

    parser.add_argument(
        "--max-hb-percent",
        type=float,
        default=5,
        help="Maximum percentage of hemoglobin genes allowed per cell (default: 5)"
    )

    return parser.parse_args()


def read_10x_folder(folder_path: str) -> sc.AnnData:
    """
    Read 10x Genomics formatted single-cell data from a folder.

    Parameters
    ----------
    folder_path : str
        Path to the folder containing 10x format files.

    Returns
    -------
    sc.AnnData
        Annotated data matrix with cells as observations and genes as variables.
    """
    folder = Path(folder_path)

    # Check required files exist
    required_files = ["matrix.mtx.gz", "genes.tsv.gz", "barcodes.tsv.gz"]
    for filename in required_files:
        file_path = folder / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Required file not found: {file_path}")

    # Read matrix file and transpose
    adata = sc.read_mtx(folder / "matrix.mtx.gz").transpose()

    # Read genes: column 0 is gene_name, column 1 is gene_id (if present)
    genes = np.loadtxt(folder / "genes.tsv.gz", dtype=str, delimiter="\t")
    adata.var_names = genes[:, 0]
    if genes.shape[1] > 1:
        adata.var["gene_id"] = genes[:, 1]

    # Read barcodes
    barcodes = np.loadtxt(folder / "barcodes.tsv.gz", dtype=str, delimiter="\t")
    adata.obs_names = barcodes

    return adata


def main():
    """Main function to run the preprocessing pipeline."""
    args = parse_args()

    logger.info("=" * 60)
    logger.info("Single-cell Preprocessing Parameters")
    logger.info("=" * 60)
    logger.info(f"Input folders: {args.input}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Minimum genes per cell: {args.min_genes}")
    logger.info(f"Minimum cells per gene: {args.min_cells}")
    logger.info(f"Maximum mitochondrial gene percent: {args.max_mt_percent}")
    logger.info(f"Maximum hemoglobin gene percent: {args.max_hb_percent}")
    logger.info("=" * 60)

    # Read input folders
    logger.info("\nReading input data:")
    logger.info("-" * 40)
    for folder_path in args.input:
        logger.info(f"Reading {folder_path}...")
        adata = read_10x_folder(folder_path)
        n_cells, n_genes = adata.shape
        logger.info(f"  - Cells: {n_cells}")
        logger.info(f"  - Genes: {n_genes}")
    logger.info("-" * 40)


if __name__ == "__main__":
    main()
