# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "scanpy",
#     "numpy<2",
#     "scipy",
#     "anndata",
#     "pandas",
# ]
# ///
"""
Convert AnnData (.h5ad) to SQLite sparse long-table format.

Converts cell-by-gene expression matrices into (cell_id, gene_id, value) triplets
instead of a wide table.  This is ideal for read-only analysis of large sparse
single-cell datasets and fully compatible with SQLite's row-oriented engine.

Usage:
    UV_INDEX=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple uv run anndata2sqlite.py input.h5ad -o output.db
    UV_INDEX=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple uv run anndata2sqlite.py input.h5ad -o output.db --chunk-size 50000
    UV_INDEX=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple uv run anndata2sqlite.py input.h5ad -o output.db --layers spliced,unspliced
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from typing import List, Optional, Sequence

import numpy as np
import scanpy as sc
from scipy.sparse import issparse


def _coo_rows_from_chunk(X_chunk, cell_offset: int) -> List[tuple[int, int, float]]:
    """Extract non-zero (cell_id, gene_id, value) triplets from a chunk."""
    if issparse(X_chunk):
        coo = X_chunk.tocoo()
        return [
            (cell_offset + int(r), int(c), float(v)) for r, c, v in zip(coo.row, coo.col, coo.data)
        ]
    else:
        mask = X_chunk != 0
        rows, cols = np.nonzero(mask)
        return [(cell_offset + int(r), int(c), float(X_chunk[r, c])) for r, c in zip(rows, cols)]


class AnnData2SQLite:
    """Convert an AnnData object to a SQLite long-table database."""

    _TYPE_MAP = {
        "int64": "INTEGER", "int32": "INTEGER", "int16": "INTEGER", "int8": "INTEGER",
        "uint64": "INTEGER", "uint32": "INTEGER", "uint16": "INTEGER", "uint8": "INTEGER",
        "float64": "REAL", "float32": "REAL",
        "bool": "INTEGER",
    }

    def __init__(
        self,
        h5ad_path: str,
        db_path: str,
        *,
        chunk_size: int = 50000,
        write_obs: bool = True,
        write_var: bool = True,
        write_obsm: bool = True,
        obs_columns: Optional[Sequence[str]] = None,
        var_columns: Optional[Sequence[str]] = None,
        obsm_keys: Optional[Sequence[str]] = None,
        layers: Optional[Sequence[str]] = None,
        build_indices: bool = True,
        overwrite: bool = False,
        verbose: bool = True,
    ):
        self.h5ad_path = h5ad_path
        self.db_path = db_path
        self.chunk_size = chunk_size
        self.write_obs = write_obs
        self.write_var = write_var
        self.write_obsm = write_obsm
        self.obs_columns = list(obs_columns) if obs_columns is not None else None
        self.var_columns = list(var_columns) if var_columns is not None else None
        self.obsm_keys = list(obsm_keys) if obsm_keys is not None else None
        self.layers = list(layers) if layers else []
        self.build_indices = build_indices
        self.overwrite = overwrite
        self.verbose = verbose
        self.conn: sqlite3.Connection | None = None

        self._n_cells: int = 0
        self._n_genes: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(self) -> None:
        """Run the full conversion pipeline."""
        self._prepare_output()
        self._open_db_write()
        self._create_schema()

        adata = self._open_anndata()
        try:
            self._write_metadata_tables(adata)
            self._write_obsm_tables(adata)
            self._write_X(adata, "X")
            for layer in self.layers:
                self._write_X(adata, f"X_{layer}", layer=layer)
        finally:
            adata.file.close()

        if self.build_indices:
            self._build_indices()
        self._optimize_read()
        self.conn.close()
        self._log(f"Done in {time.time() - self._t0:.1f}s → {self.db_path}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def _prepare_output(self) -> None:
        if os.path.exists(self.db_path):
            if self.overwrite:
                os.remove(self.db_path)
            else:
                raise FileExistsError(f"{self.db_path} already exists. Use --overwrite.")
        self._t0 = time.time()

    def _open_anndata(self):
        """Open the h5ad, preferring backed mode for large files."""
        self._log(f"Opening {self.h5ad_path} ...")
        return sc.read_h5ad(self.h5ad_path, backed="r")

    def _open_db_write(self) -> None:
        self.conn = sqlite3.connect(self.db_path)
        # Maximise bulk-insert throughput — safe because this is a one-shot build
        self.conn.execute("PRAGMA journal_mode = OFF")
        self.conn.execute("PRAGMA synchronous = OFF")
        self.conn.execute("PRAGMA cache_size = -2000000")  # ~2 GB page cache
        self.conn.execute("PRAGMA locking_mode = EXCLUSIVE")
        self.conn.execute("PRAGMA page_size = 65536")

    def _create_schema(self) -> None:
        pass  # obs / var are created dynamically in _write_metadata_tables

    # ------------------------------------------------------------------
    # Metadata tables (obs / var) – small, written once
    # ------------------------------------------------------------------

    def _write_metadata_tables(self, adata) -> None:
        self._n_cells = adata.shape[0]
        self._n_genes = adata.shape[1]

        if self.write_obs:
            self._write_obs(adata)

        if self.write_var:
            self._write_var(adata)

    # ------------------------------------------------------------------
    # obs – preserve all columns by default, allow filtering
    # ------------------------------------------------------------------

    def _write_obs(self, adata) -> None:
        obs = adata.obs.copy()
        obs.insert(0, "cell_id", range(len(obs)))
        obs.index.rename("cell_barcode", inplace=True)
        obs.reset_index(inplace=True)

        cols = ["cell_id", "cell_barcode"] + [
            c for c in obs.columns if c not in ("cell_id", "cell_barcode")
        ]
        obs = obs[cols]

        if self.obs_columns is not None:
            keep = {"cell_id", "cell_barcode"} | set(self.obs_columns)
            obs = obs[[c for c in cols if c in keep]]
            missing = set(self.obs_columns) - set(obs.columns) - {"cell_id", "cell_barcode"}
            if missing:
                self._log(f"  Warning: obs column(s) not found: {missing}")

        obs.columns = self._dedup_columns(obs.columns)
        col_defs = [self._col_def("cell_id", "INTEGER", pk=True)]
        for c in obs.columns:
            if c == "cell_id":
                continue
            col_defs.append(self._col_def(c, self._dtype_to_sql(obs[c])))

        self._log(f"Writing obs  ({len(obs)} cells, {len(obs.columns)} cols) ...")
        self.conn.execute(f"CREATE TABLE obs ({', '.join(col_defs)})")
        self._insert_df("obs", obs)

    # ------------------------------------------------------------------
    # var – preserve all columns by default, allow filtering
    # ------------------------------------------------------------------

    def _write_var(self, adata) -> None:
        var = adata.var.copy()
        var.insert(0, "gene_id", range(len(var)))
        var.index.rename("gene_name", inplace=True)  # original AnnData var_names
        var.reset_index(inplace=True)

        cols = ["gene_id", "gene_name"] + [
            c for c in var.columns if c not in ("gene_id", "gene_name")
        ]
        var = var[cols]

        if self.var_columns is not None:
            keep = {"gene_id", "gene_name"} | set(self.var_columns)
            var = var[[c for c in cols if c in keep]]
            missing = set(self.var_columns) - set(var.columns) - {"gene_id", "gene_name"}
            if missing:
                self._log(f"  Warning: var column(s) not found: {missing}")

        var.columns = self._dedup_columns(var.columns)
        col_defs = [self._col_def("gene_id", "INTEGER", pk=True)]
        for c in var.columns:
            if c == "gene_id":
                continue
            col_defs.append(self._col_def(c, self._dtype_to_sql(var[c])))

        self._log(f"Writing var  ({len(var)} genes, {len(var.columns)} cols) ...")
        self.conn.execute(f"CREATE TABLE var ({', '.join(col_defs)})")
        self._insert_df("var", var)

    # ------------------------------------------------------------------
    # obsm – each key becomes a wide table  obsm_<key>(cell_id, dim_0, dim_1, ...)
    # ------------------------------------------------------------------

    def _write_obsm_tables(self, adata) -> None:
        if not self.write_obsm or not adata.obsm:
            return

        keys = self.obsm_keys if self.obsm_keys is not None else list(adata.obsm.keys())
        for key in keys:
            if key not in adata.obsm:
                self._log(f"  Warning: obsm key '{key}' not found, skipping")
                continue
            self._write_obsm(adata, key)

    def _write_obsm(self, adata, key: str) -> None:
        import pandas as pd

        arr = adata.obsm[key]  # (n_cells, n_dims), dense
        table_name = f"obsm_{key.replace('-', '_').replace('.', '_')}"
        n_cells, n_dims = arr.shape

        dim_cols = [f"dim_{d}" for d in range(n_dims)]
        df = pd.DataFrame(arr, columns=dim_cols)
        df.insert(0, "cell_id", range(n_cells))

        col_defs = [self._col_def("cell_id", "INTEGER", pk=True)]
        for c in dim_cols:
            col_defs.append(self._col_def(c, "REAL"))

        self._log(f"Writing {table_name}  ({n_cells} cells × {n_dims} dims) ...")
        self.conn.execute(f"CREATE TABLE {table_name} ({', '.join(col_defs)})")
        self._insert_df(table_name, df)

    # ------------------------------------------------------------------
    # Tiny helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _col_def(name: str, sql_type: str, pk: bool = False) -> str:
        suffix = " PRIMARY KEY" if pk else ""
        return f'"{name}" {sql_type}{suffix}'

    @classmethod
    def _dtype_to_sql(cls, series) -> str:
        return cls._TYPE_MAP.get(str(series.dtype), "TEXT")

    @staticmethod
    def _dedup_columns(columns):
        """Rename duplicate columns (case-insensitive) by appending _1, _2, ..."""
        seen = set()
        result = []
        for col in columns:
            key = col.lower()
            if key not in seen:
                seen.add(key)
                result.append(col)
            else:
                i = 1
                while f"{key}_{i}" in seen:
                    i += 1
                seen.add(f"{key}_{i}")
                result.append(f"{col}_{i}")
        return result

    def _insert_df(self, table: str, df) -> None:
        placeholders = ",".join(["?"] * len(df.columns))
        self.conn.executemany(
            f"INSERT INTO {table} VALUES ({placeholders})",
            (tuple(row) for row in df.itertuples(index=False)),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Expression matrix – chunked, CSR-aware streaming
    # ------------------------------------------------------------------

    def _write_X(self, adata, table_name: str, layer: str | None = None) -> None:
        """
        Stream expression data directly into a WITHOUT ROWID table keyed by
        (gene_id, cell_id).  The B-tree maintains PK order regardless of
        insertion order, so no temp table or explicit sort is needed.
        """
        self.conn.execute(f"""
            CREATE TABLE {table_name} (
                gene_id  INTEGER NOT NULL,
                cell_id  INTEGER NOT NULL,
                value    REAL    NOT NULL,
                PRIMARY KEY (gene_id, cell_id)
            ) WITHOUT ROWID
        """)

        n_cells = adata.shape[0]
        source_name = f"layers['{layer}']" if layer else ".X"
        self._log(
            f"Writing {table_name}  ({n_cells} cells, "
            f"chunk_size={self.chunk_size}, source={source_name}) ..."
        )

        total_rows = 0
        self.conn.commit()
        self.conn.execute("BEGIN")

        for start in range(0, n_cells, self.chunk_size):
            end = min(start + self.chunk_size, n_cells)
            chunk_adata = adata[start:end]
            X_chunk = chunk_adata.X if layer is None else chunk_adata.layers[layer]
            rows = _coo_rows_from_chunk(X_chunk, cell_offset=start)

            # Reorder (cell_id, gene_id, value) → (gene_id, cell_id, value)
            rows = [(g, c, v) for c, g, v in rows]

            BATCH = 200_000
            for i in range(0, len(rows), BATCH):
                self.conn.executemany(
                    f"INSERT INTO {table_name} VALUES (?, ?, ?)",
                    rows[i : i + BATCH],
                )

            total_rows += len(rows)
            self._log(
                f"  cells {start}-{end - 1}  "
                f"({total_rows:,} non-zero rows so far, "
                f"{time.time() - self._t0:.0f}s)"
            )
            del chunk_adata, X_chunk, rows

        self.conn.execute("COMMIT")
        self._log(f"  {table_name}: {total_rows:,} non-zero rows written")

    # ------------------------------------------------------------------
    # Indices (built after bulk insert to avoid per-insert B-tree cost)
    # ------------------------------------------------------------------

    def _build_indices(self) -> None:
        self._log("Building indices ...")
        cpu = os.cpu_count() or 4
        self.conn.execute(f"PRAGMA threads = {cpu}")
        for tbl in ["X"] + [f"X_{ly}" for ly in self.layers]:
            # Covering index so cell-centric queries never touch the main
            # B-tree: SELECT cell_id, value FROM X WHERE cell_id = ? → index-only
            self.conn.execute(f"CREATE INDEX idx_{tbl}_cell ON {tbl} (cell_id, gene_id, value)")
        self._log("Indices done")

    # ------------------------------------------------------------------
    # Switch to read-optimised settings
    # ------------------------------------------------------------------

    def _optimize_read(self) -> None:
        self.conn.commit()
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.execute("PRAGMA locking_mode = NORMAL")
        # mmap as much of the file as possible for fast random reads
        db_size = os.path.getsize(self.db_path)
        self.conn.execute(f"PRAGMA mmap_size = {db_size}")
        self.conn.execute("ANALYZE")


# ======================================================================
# CLI
# ======================================================================


def inspect_h5ad(path: str) -> None:
    """Print the structure of an h5ad file without converting."""
    adata = sc.read_h5ad(path, backed="r")
    print(f"Shape:        {adata.shape[0]:,} cells × {adata.shape[1]:,} genes")
    if hasattr(adata.X, "nnz"):
        sp = adata.X.nnz / (adata.shape[0] * adata.shape[1]) * 100
        print(f"Sparsity:     {adata.X.nnz:,} non-zero ({sp:.1f}%)")
    else:
        print("Matrix type:  dense")

    print(f"\nobs  ({len(adata.obs.columns)} cols):")
    for c, d in zip(adata.obs.columns, adata.obs.dtypes):
        print(f"  {c:<30s} {d}")

    print(f"\nvar  ({len(adata.var.columns)} cols):")
    for c, d in zip(adata.var.columns, adata.var.dtypes):
        print(f"  {c:<30s} {d}")

    print(f"\nobsm ({len(adata.obsm)} keys):")
    for k, v in adata.obsm.items():
        print(f"  {k:<30s} {v.shape}")

    print(f"\nlayers ({len(adata.layers)} keys):")
    for k in adata.layers.keys():
        print(f"  {k}")

    adata.file.close()


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Convert AnnData (.h5ad) to SQLite long-table format",
    )
    parser.add_argument("h5ad", help="Path to input .h5ad file")
    parser.add_argument("-o", "--output", help="Path to output .db file")
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Print h5ad structure (obs/var/obsm columns) and exit",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=50000,
        help="Cells per chunk (default: 50000)",
    )
    parser.add_argument(
        "--layers",
        default="",
        help="Comma-separated layer names to include (e.g. 'spliced,unspliced')",
    )
    parser.add_argument("--no-obs", action="store_true", help="Skip writing the obs table")
    parser.add_argument("--no-var", action="store_true", help="Skip writing the var table")
    parser.add_argument("--no-obsm", action="store_true", help="Skip writing obsm tables")
    parser.add_argument(
        "--obs-columns",
        default="",
        help="Comma-separated obs columns to include (default: all)",
    )
    parser.add_argument(
        "--var-columns",
        default="",
        help="Comma-separated var columns to include (default: all)",
    )
    parser.add_argument(
        "--obsm-keys",
        default="",
        help="Comma-separated obsm keys to include (default: all)",
    )
    parser.add_argument("--no-index", action="store_true", help="Skip building indices")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output file")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress progress output")

    args = parser.parse_args(argv)

    if args.inspect:
        inspect_h5ad(args.h5ad)
        return

    if not args.output:
        parser.error("-o/--output is required (except with --inspect)")

    def _parse_csv(val: str):
        return [v.strip() for v in val.split(",") if v.strip()]

    converter = AnnData2SQLite(
        h5ad_path=args.h5ad,
        db_path=args.output,
        chunk_size=args.chunk_size,
        write_obs=not args.no_obs,
        write_var=not args.no_var,
        write_obsm=not args.no_obsm,
        obs_columns=_parse_csv(args.obs_columns) or None,
        var_columns=_parse_csv(args.var_columns) or None,
        obsm_keys=_parse_csv(args.obsm_keys) or None,
        layers=_parse_csv(args.layers),
        build_indices=not args.no_index,
        overwrite=args.overwrite,
        verbose=not args.quiet,
    )
    converter.convert()


if __name__ == "__main__":
    main()
