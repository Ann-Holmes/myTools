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

# Replace .gtf.gz with .gene.gtf.gz
output_file="${input_file%.gtf.gz}.gene.gtf.gz"

output_dir=$(dirname "$output_file")

if [ ! -d "$output_dir" ]; then
    echo "Error: Output directory does not exist: $output_dir" >&2
    exit 1
fi

if [ ! -w "$output_dir" ]; then
    echo "Error: Output directory is not writable: $output_dir" >&2
    exit 1
fi

# Trap to clean up partial output on failure
cleanup() {
    if [ -f "$output_file" ]; then
        rm -f "$output_file"
    fi
}

trap cleanup EXIT

# Extract gene entries and comments
gzip -dc "$input_file" | awk '/^#/ || $3=="gene"' | gzip > "$output_file"

# Disable trap on successful completion
trap - EXIT

echo "Successfully extracted gene entries to: $output_file"
