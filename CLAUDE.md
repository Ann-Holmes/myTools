# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a personal collection of utility tools - primarily Python scripts and R scripts for various bioinformatics and general-purpose tasks. There's no unified build system; each tool is independent.

## Directory Structure

```
/home/hzl/Work/Project/myTools/
├── python/
│   ├── meeting-summary/          # Structured Python package with CLI
│   ├── deepseek_v3_tokenizer/   # Token counting utilities
│   ├── sqlite_utils.py          # SQLite database toolkit
│   ├── downloader.py           # Multi-threaded file downloader
│   ├── compress_video.py        # Video compression (ffmpeg)
│   ├── convert_video_gif.py     # Video to GIF conversion
│   ├── split_file.py           # Binary file splitter with MD5
│   ├── io_h5ad_feather.py      # Single-cell data I/O (h5ad <-> feather)
│   ├── parseGTF.py              # GTF/GFF3 parser (supports gene_biotype fallback)
│   └── sc_preprocess.py        # Single-cell QC and preprocessing (scanpy)
└── R/
    ├── find_dependencies.R      # Find uninstallable R package dependencies
    ├── mergeMS.R                # Merge ProteinDiscovery outputs to Excel
    └── io_SE_feather.R          # Feather file I/O for R
```

## Key Tools

### Python Scripts (root-level)

- **sqlite_utils.py**: SQLite database toolkit with `SQLiteConnection` class. Usage:

  ```python
  from sqlite_utils import connect, quick_look
  db = connect("database.db")
  tables = db.list_tables()
  info = quick_look("database.db", "table_name")  # Quick inspection
  ```

- **downloader.py**: Multi-threaded file downloader with resume and retry support.

  ```python
  from downloader import Downloader
  d = Downloader(urls, outdir, names, max_workers=4)
  d.download()
  d.md5check(md5sums)
  ```

- **compress_video.py**: Video compression using ffmpeg (libx264, CRF 23). Edit the `video_dir` variable to configure input/output paths.

- **split_file.py**: Splits binary files into chunks with MD5 checksums for verification.

- **sc_preprocess.py**: Single-cell RNA-seq preprocessing tool using scanpy. Reads 10x Genomics format (matrix.mtx.gz, genes.tsv.gz, barcodes.tsv.gz), performs QC filtering (mitochondrial %, hemoglobin %, gene count, UMI count), generates QC plots, and saves h5ad files.

  ```bash
  python python/sc_preprocess.py -i sample1 sample2 -o ./output
  # Requires: scanpy, numpy, matplotlib
  ```

### meeting-summary Module

The most structured project in this collection. A Python package for AI-powered meeting transcription summarization.

**Installation**:

```bash
cd python/meeting-summary
uv tool install .  # or: uv sync
```

**Usage**:

```bash
meeting-summary --input meeting.txt --basename output
# Requires OPENAI_API_KEY environment variable
```

**Development**:

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format .
```

### deepseek_v3_tokenizer

Token counting tool using DeepSeek tokenizer.

```bash
python python/deepseek_v3_tokenizer/count_tokens.py file1.txt file2.txt
```

Requires Python 3.12+ and transformers library.

### R Scripts

- **find_dependencies.R**: Find uninstallable dependencies of an R package. Outputs conda-installable package list.

  ```bash
  Rscript R/find_dependencies.R -n <package_name> -o <output_file> -r
  ```

- **mergeMS.R**: Merge ProteinDiscovery outputs into a single Excel file.

### Shell Scripts

- **extract_gene_from_gtf.sh**: Extract gene entries from GTF files.

  ```bash
  ./shell/extract_gene_from_gtf.sh input.gtf.gz
  # Output: input.gene.gtf.gz (same directory)
  # Preserves comment lines, extracts only gene feature entries
  ```

## Notes

- Most Python scripts at the root level are standalone and can be run directly.
- No unified testing or linting configuration exists for the collection (only meeting-summary has ruff configured).
- The project uses conventional commits with emoji prefixes (✨, 🐞, etc.).
- **IMPORTANT**: Don't include the "Co-Authored-By" line in commit messages.
