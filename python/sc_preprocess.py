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

import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import numpy as np
import scanpy as sc

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments for single-cell preprocessing."""
    parser = argparse.ArgumentParser(
        description="Single-cell data preprocessing tool for quality control and filtering."
    )

    parser.add_argument(
        "-i",
        "--input",
        type=str,
        nargs="+",
        required=True,
        help="Input folders containing single-cell data files (required)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="./output",
        help="Output directory for processed data (default: ./output)",
    )

    parser.add_argument(
        "--min-genes",
        type=int,
        default=200,
        help="Minimum number of genes per cell (default: 200)",
    )

    parser.add_argument(
        "--min-cells",
        type=int,
        default=3,
        help="Minimum number of cells per gene (default: 3)",
    )

    parser.add_argument(
        "--max-mt-percent",
        type=float,
        default=5,
        help="Maximum percentage of mitochondrial genes allowed per cell (default: 5)",
    )

    parser.add_argument(
        "--max-hb-percent",
        type=float,
        default=5,
        help="Maximum percentage of hemoglobin genes allowed per cell (default: 5)",
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
    sc.pp.calculate_qc_metrics(
        adata, qc_vars=["mt", "hb"], percent_top=None, log1p=False, inplace=True
    )

    return adata


def filter_cells(
    adata: sc.AnnData,
    min_genes: int,
    min_cells: int,
    max_mt_percent: float,
    max_hb_percent: float,
) -> sc.AnnData:
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


def plot_qc_violin(adata: sc.AnnData, output_dir: Path):
    """
    Plot violin plots for QC metrics.

    Parameters
    ----------
    adata : sc.AnnData
        Annotated data matrix with QC metrics in obs.
    output_dir : Path
        Directory to save the violin plot.
    """
    logger.info("Generating violin plot...")
    sc.pl.violin(
        adata,
        keys=["n_genes_by_counts", "total_counts", "percent_mt", "percent_hb"],
        rotation=45,
        save="violin.png",
        show=False,
    )
    # Move the saved figure to the output directory
    output_path = output_dir / "violin.png"
    if Path("figures/violin.png").exists():
        Path("figures/violin.png").rename(output_path)
        Path("figures").rmdir()
    plt.close()


def plot_qc_scatter(adata: sc.AnnData, output_dir: Path):
    """
    Plot scatter plot for QC metrics.

    Parameters
    ----------
    adata : sc.AnnData
        Annotated data matrix with QC metrics in obs.
    output_dir : Path
        Directory to save the scatter plot.
    """
    logger.info("Generating scatter plot...")
    sc.pl.scatter(
        adata,
        x="n_genes_by_counts",
        y="total_counts",
        color="percent_mt",
        save="scatter.png",
        show=False,
    )
    # Move the saved figure to the output directory
    output_path = output_dir / "scatter.png"
    if Path("figures/scatter.png").exists():
        Path("figures/scatter.png").rename(output_path)
        Path("figures").rmdir()
    plt.close()


def plot_pca_umap(adata: sc.AnnData, output_dir: Path):
    """
    Plot PCA and UMAP for QC metrics.

    Parameters
    ----------
    adata : sc.AnnData
        Annotated data matrix with QC metrics in obs.
    output_dir : Path
        Directory to save the PCA and UMAP plots.
    """
    logger.info("Running PCA...")
    n_comps = min(50, adata.n_vars - 1)
    sc.pp.pca(adata, n_comps=n_comps)

    logger.info("Computing neighbors...")
    sc.pp.neighbors(adata)

    logger.info("Running UMAP...")
    sc.tl.umap(adata)

    logger.info("Generating PCA and UMAP plots...")
    # Create 1x2 subplots
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Plot PCA
    sc.pl.pca(adata, color="n_genes_by_counts", ax=axes[0], show=False, title="PCA")

    # Plot UMAP
    sc.pl.umap(adata, color="n_genes_by_counts", ax=axes[1], show=False, title="UMAP")

    # Save the figure
    output_path = output_dir / "pca_umap.png"
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


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
            max_hb_percent=args.max_hb_percent,
        )

        n_cells_after, n_genes_after = adata.shape
        logger.info(f"  - Cells after filtering: {n_cells_after}")
        logger.info(f"  - Genes after filtering: {n_genes_after}")

        # Create output directory structure for the sample
        sample_name = Path(folder_path).name
        sample_output_dir = Path(args.output) / sample_name
        qc_plots_dir = sample_output_dir / "qc_plots"
        qc_plots_dir.mkdir(parents=True, exist_ok=True)

        # Generate QC plots
        logger.info(f"\nGenerating QC plots for {sample_name}...")
        plot_qc_violin(adata, qc_plots_dir)
        plot_qc_scatter(adata, qc_plots_dir)
        plot_pca_umap(adata, qc_plots_dir)

        # Save h5ad file
        h5ad_path = sample_output_dir / f"{sample_name}.h5ad"
        adata.write_h5ad(h5ad_path)

        logger.info(f"  - Saved: {h5ad_path}")
        logger.info(f"  - Saved: {qc_plots_dir / 'violin.png'}")
        logger.info(f"  - Saved: {qc_plots_dir / 'scatter.png'}")
        logger.info(f"  - Saved: {qc_plots_dir / 'pca_umap.png'}")
    logger.info("-" * 40)


if __name__ == "__main__":
    main()
