#!/usr/bin/env python
"""
Single-cell data preprocessing tool.

This script provides command-line interface for preprocessing single-cell RNA-seq data,
including filtering cells and genes based on various quality control metrics.
"""

import argparse
import logging
import os
import re
from pathlib import Path

import numpy as np
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


def get_mt_genes(adata: sc.AnnData) -> list:
    """
    Identify mitochondrial genes by matching the regex pattern ^MT- (case-insensitive).

    Parameters
    ----------
    adata : sc.AnnData
        Annotated data matrix with gene names in var_names.

    Returns
    -------
    list
        List of gene names that match the mitochondrial gene pattern.
    """
    gene_names = adata.var_names.tolist()
    mt_pattern = re.compile(r"^MT-", re.IGNORECASE)
    mt_genes = [gene for gene in gene_names if mt_pattern.match(gene)]
    return mt_genes


def get_hb_genes(adata: sc.AnnData) -> list:
    """
    Identify hemoglobin genes by matching the regex pattern ^HB[AB] (case-insensitive).

    Parameters
    ----------
    adata : sc.AnnData
        Annotated data matrix with gene names in var_names.

    Returns
    -------
    list
        List of gene names that match the hemoglobin gene pattern.
    """
    gene_names = adata.var_names.tolist()
    hb_pattern = re.compile(r"^HB[AB]", re.IGNORECASE)
    hb_genes = [gene for gene in gene_names if hb_pattern.match(gene)]
    return hb_genes


def calculate_qc_metrics(adata: sc.AnnData) -> sc.AnnData:
    """
    Calculate quality control metrics for the single-cell data.

    This function identifies mitochondrial and hemoglobin genes, marks them in
    adata.var, and calculates QC metrics including percent mitochondrial and
    hemoglobin gene expression per cell.

    Parameters
    ----------
    adata : sc.AnnData
        Annotated data matrix with cells as observations and genes as variables.

    Returns
    -------
    sc.AnnData
        Annotated data matrix with QC metrics added to obs.
    """
    # Get mitochondrial and hemoglobin gene lists
    mt_genes = get_mt_genes(adata)
    hb_genes = get_hb_genes(adata)

    # Mark mitochondrial and hemoglobin genes in adata.var
    adata.var["mt"] = adata.var_names.isin(mt_genes)
    adata.var["hb"] = adata.var_names.isin(hb_genes)

    # Calculate QC metrics
    sc.pp.calculate_qc_metrics(adata, qc_vars=["mt", "hb"], percent_top=None, log1p=False, inplace=True)

    return adata


def filter_cells(adata: sc.AnnData, min_genes: int, min_cells: int, max_mt_percent: float, max_hb_percent: float) -> sc.AnnData:
    """
    Filter cells and genes based on quality control thresholds.

    Parameters
    ----------
    adata : sc.AnnData
        Annotated data matrix with cells as observations and genes as variables.
    min_genes : int
        Minimum number of genes per cell.
    min_cells : int
        Minimum number of cells per gene.
    max_mt_percent : float
        Maximum percentage of mitochondrial genes allowed per cell.
    max_hb_percent : float
        Maximum percentage of hemoglobin genes allowed per cell.

    Returns
    -------
    sc.AnnData
        Filtered annotated data matrix.
    """
    # Filter cells by minimum number of genes
    sc.pp.filter_cells(adata, min_genes=min_genes)

    # Filter genes by minimum number of cells
    sc.pp.filter_genes(adata, min_cells=min_cells)

    # Filter cells by maximum mitochondrial gene percent
    if "percent_mt" in adata.obs.columns:
        adata = adata[adata.obs["percent_mt"] <= max_mt_percent, :]

    # Filter cells by maximum hemoglobin gene percent
    if "percent_hb" in adata.obs.columns:
        adata = adata[adata.obs["percent_hb"] <= max_hb_percent, :]

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

    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)

    # Read input folders
    logger.info("\nReading input data:")
    logger.info("-" * 40)
    for folder_path in args.input:
        logger.info(f"Reading {folder_path}...")
        adata = read_10x_folder(folder_path)
        n_cells_before, n_genes_before = adata.shape
        logger.info(f"  - Cells before filtering: {n_cells_before}")
        logger.info(f"  - Genes before filtering: {n_genes_before}")

        # Calculate QC metrics
        logger.info("Calculating QC metrics...")
        adata = calculate_qc_metrics(adata)

        # Filter cells and genes
        logger.info("Filtering cells and genes...")
        adata = filter_cells(
            adata,
            min_genes=args.min_genes,
            min_cells=args.min_cells,
            max_mt_percent=args.max_mt_percent,
            max_hb_percent=args.max_hb_percent
        )

        n_cells_after, n_genes_after = adata.shape
        logger.info(f"  - Cells after filtering: {n_cells_after}")
        logger.info(f"  - Genes after filtering: {n_genes_after}")
    logger.info("-" * 40)


if __name__ == "__main__":
    main()
