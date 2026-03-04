#!/usr/bin/env python
"""
Single-cell data preprocessing tool.

This script provides command-line interface for preprocessing single-cell RNA-seq data,
including filtering cells and genes based on various quality control metrics.
"""

import argparse
import os
import sys
from pathlib import Path


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


def main():
    """Main function to run the preprocessing pipeline."""
    args = parse_args()

    print("=" * 60)
    print("Single-cell Preprocessing Parameters")
    print("=" * 60)
    print(f"Input folders: {args.input}")
    print(f"Output directory: {args.output}")
    print(f"Minimum genes per cell: {args.min_genes}")
    print(f"Minimum cells per gene: {args.min_cells}")
    print(f"Maximum mitochondrial gene percent: {args.max_mt_percent}")
    print(f"Maximum hemoglobin gene percent: {args.max_hb_percent}")
    print("=" * 60)


if __name__ == "__main__":
    main()
