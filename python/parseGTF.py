import pandas as pd


def read_gtf(gtf_path: str) -> pd.DataFrame:
    """Read a GTF file into a pandas DataFrame.

    Parameters
    ----------
    gtf_path : str
        Path to GTF file.

    Returns
    -------
    gtf : pd.DataFrame
        GTF file as a pandas DataFrame.
    """
    gtf = pd.read_csv(gtf_path, sep='\t', comment='#', header=None)
    gtf.columns = ['seqname', 'source', 'feature', 'start',
                   'end', 'score', 'strand', 'frame', 'attribute']

    # extract gene_id, gene_name, gene_type
    # transcript_id, transcript_name, transcript_type
    # exon_number, exon_id
    gtf.insert(8, 'gene_id', gtf['attribute'].str.extract(r'gene_id "([^"]+)"'))
    gtf.insert(9, 'gene_name', gtf['attribute'].str.extract(r'gene_name "([^"]+)"'))
    gtf.insert(10, 'gene_type', gtf['attribute'].str.extract(r'gene_type "([^"]+)"'))
    gtf.insert(11, 'transcript_id', gtf['attribute'].str.extract(r'transcript_id "([^"]+)"'))
    gtf.insert(12, 'transcript_name', gtf['attribute'].str.extract(r'transcript_name "([^"]+)"'))
    gtf.insert(13, 'transcript_type', gtf['attribute'].str.extract(r'transcript_type "([^"]+)"'))
    gtf.insert(14, 'exon_number', gtf['attribute'].str.extract(r'exon_number (\d+)'))
    gtf.insert(15, 'exon_id', gtf['attribute'].str.extract(r'exon_id "([^"]+)"'))
    return gtf


def read_gff3(gff3_path: str) -> pd.DataFrame:
    """Read a GFF3 file into a pandas DataFrame.

    Parameters
    ----------
    gff3_path : str
        Path to GFF3 file.

    Returns
    -------
    gff3 : pd.DataFrame
        GFF3 file as a pandas DataFrame.
    """
    gtf = pd.read_csv(gff3_path, sep='\t', comment='#', header=None)
    gtf.columns = ['seqname', 'source', 'feature', 'start',
                   'end', 'score', 'strand', 'frame', 'attribute']

    # extract gene_id, gene_name, gene_type
    # transcript_id, transcript_name, transcript_type
    # exon_number, exon_id
    gtf.insert(8, 'gene_id', gtf['attribute'].str.extract(r'gene_id=([^;]+)'))
    gtf.insert(9, 'gene_name', gtf['attribute'].str.extract(r'gene_name=([^;]+)'))
    gtf.insert(10, 'gene_type', gtf['attribute'].str.extract(r'gene_type=([^;]+)'))
    gtf.insert(11, 'transcript_id', gtf['attribute'].str.extract(r'transcript_id=([^;]+)'))
    gtf.insert(12, 'transcript_name', gtf['attribute'].str.extract(r'transcript_name=([^;]+)'))
    gtf.insert(13, 'transcript_type', gtf['attribute'].str.extract(r'transcript_type=([^;]+)'))
    gtf.insert(14, 'exon_number', gtf['attribute'].str.extract(r'exon_number=(\d+)'))
    gtf.insert(15, 'exon_id', gtf['attribute'].str.extract(r'exon_id=([^;]+)'))
    return gtf
