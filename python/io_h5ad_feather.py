import scanpy as sc
import pandas as pd
import warnings
import os


def read_h5ad4feather(feather_dirname: str) -> sc.AnnData:
    """Read feather files and combine to Anndata

    colData - `.obs`
    rowData - `.var`
    assays - `.layers`

    If no `X_assay.feather` is in `feather_dirname`, will try to use `count_assay.feather` or 
    `counts_assay.feather` as `.X`. If also no `count_assay.feather` or `counts_assay.feather`, will
    try to use random first assay as `.X`

    Parameters
    ----------
    feather_dirname : str
        directory where the feather files saved

    Returns
    -------
    sc.AnnData
    """
    feather_files = os.listdir(feather_dirname)
    assay_files = []
    assay_names = []
    for ffile in feather_files:
        if ffile.endswith("_assay.feather"):
            assay_files.append(ffile)
            assay_names.append(ffile[:-14])
        elif ffile.startswith("colData"):
            coldata_file = ffile
        elif ffile.startswith("rowData"):
            rowdata_file = ffile

    # Read assays
    assay_dict = {}
    for afile, aname in zip(assay_files, assay_names):
        tmp_assay = pd.read_feather(os.path.join(feather_dirname, afile))
        tmp_assay.index = tmp_assay["gene_id"].to_list()
        tmp_assay.drop(columns=["gene_id"], inplace=True)
        assay_dict[aname] = tmp_assay.T

    # Read obs
    obs = pd.read_feather(os.path.join(feather_dirname, coldata_file))
    obs.index = obs["colnames"].to_list()
    obs.drop(columns=["colnames"], inplace=True)

    # Read var
    var = pd.read_feather(os.path.join(feather_dirname, rowdata_file))
    var.index = var["rownames"].to_list()
    var.drop(columns=["rownames"], inplace=True)

    # Make count/counts as X
    if "X" in assay_dict:
        X = assay_dict.pop("X", None)
    elif "count" in assay_dict:
        warnings.warn("Don't have `X` assay, use `count` as `X` assay")
        X = assay_dict.pop("count", None)
    elif "counts" in assay_dict:
        warnings.warn("Don't have `X` assay, use `counts` as `X` assay")
        X = assay_dict.pop("counts", None)
    else:
        first_key = list(assay_dict.keys())[0]
        warnings.warn(f"Don't have `X` assay, use `{first_key}` as `X` assay")
        X = assay_dict[first_key]

    return sc.AnnData(X, obs, var, layers=assay_dict)


def write_h5ad2feather(adata: sc.AnnData, feather_dirname: str) -> None:
    """Write Anndata to some feather files

    colData - `.obs`
    rowData - `.var`
    assays - `.layers`

    If no `X_assay.feather` is in `feather_dirname`, will try to use `count_assay.feather` or 
    `counts_assay.feather` as `.X`. If also no `count_assay.feather` or `counts_assay.feather`, will
    try to use random first assay as `.X`

    Parameters
    ----------
    adata : sc.AnnData

    feather_dirname : str
        directory where the feather files saved
    """
    if not os.path.exists(feather_dirname):
        os.makedirs(feather_dirname)
    tmp_df = adata.to_df().T
    tmp_df = tmp_df.reset_index().rename(columns={"index": "gene_id"})
    tmp_df.to_feather(os.path.join(feather_dirname, "X_assay.feather"))

    # Write layer to assay.feather
    for layerk in adata.layers.keys():
        tmp_df = adata.to_df(layerk).T
        tmp_df = tmp_df.reset_index().rename(columns={"index": "gene_id"})
        tmp_df.to_feather(os.path.join(feather_dirname, f"{layerk}_assay.feather"))

    # Write obs to colData.feather
    obs = adata.obs.reset_index().rename(columns={"index": "colnames"})
    obs.to_feather(os.path.join(feather_dirname, "colData.feather"))

    # Write var to rowData.feather
    var = adata.var.reset_index().rename(columns={"index": "rownames"})
    var.to_feather(os.path.join(feather_dirname, "rowData.feather"))


if __name__ == '__main__':
    tcga_adata = read_h5ad4feather("test/tmp.feather")
    write_h5ad2feather(tcga_adata, "test/tmp.feather")
    print(tcga_adata)
