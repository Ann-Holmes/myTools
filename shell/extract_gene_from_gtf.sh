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

input_file="$1"

if [ ! -f "$input_file" ]; then
    echo "Error: Input file does not exist: $input_file" >&2
    exit 1
fi

if [ ! -r "$input_file" ]; then
    echo "Error: Input file is not readable: $input_file" >&2
    exit 1
fi

if [[ ! "$input_file" =~ \.gtf\.gz$ ]]; then
    echo "Error: Input file must end with .gtf.gz: $input_file" >&2
    exit 1
fi
