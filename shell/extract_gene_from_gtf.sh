#!/bin/bash

# Extract gene entries from GTF file
# Usage: extract_gene_from_gtf.sh INPUT.gtf.gz
# Output: INPUT.gene.gtf.gz (same directory)

usage() {
    echo "Usage: $0 INPUT.gtf.gz" >&2
    echo "Extract gene entries from GTF file and save to INPUT.gene.gtf.gz" >&2
    exit 1
}

if [ $# -ne 1 ]; then
    echo "Error: Expected 1 argument, got $#" >&2
    usage
fi
