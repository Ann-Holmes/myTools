# ---------------------------------------------------------------------------------------- #
# Description: This script is used to find all uninstallable dependencies of an R package  #
# Usage: Rscript find_dependencies.R -n <package_name> -o <output_file> -r                 #
# Conda Usage: mamba install -c conda-forge -c bioconda -c r $(cat <output_file>)          #
# ---------------------------------------------------------------------------------------- #

library(optparse)

# Define the input arguments ------
option_list <- list(
  make_option(c("-r", "--recursive"),
    action = "store_true", dest = "recursive", default = FALSE,
    help = "Whether to recursively search for dependencies"
  ),
  make_option(c("-n", "--name"),
    type = "character", default = NULL,
    help = "Package name to search for"
  ),
  make_option(c("-o", "--output"),
    type = "character", default = NULL,
    help = "Path to the output file"
  )
)

# Parse the input arguments
opt <- parse_args(OptionParser(option_list = option_list))
# opt <- list(name = "deseq2", recursive = TRUE, output = "missing_deps.csv")

# Check if the package name is provided
pkg_name <- BiocManager::available(opt$name)

# Check the dependencies ------

#' @title Check dependencies of an R package
#' @description This function checks the dependencies of an R package, and returns the missing ones
#' @param pkg_name The name of the package to check
#' @return A tibble containing the missing dependencies and their repository names
check_dependencies <- function(pkg_name) {
  repo_urls <- BiocManager::repositories()[c("CRAN", "BioCsoft")]
  repo_names <- names(repo_urls)
  names(repo_names) <- contrib.url(repo_urls)

  pkgs_db <- available.packages(repos = repo_urls)
  installed <- installed.packages()[, "Package"]

  deps <- tools::package_dependencies(
    pkg_name,
    db = pkgs_db,
    recursive = opt$recursive
  )

  pkgs_db |>
    as.data.frame() |>
    dplyr::filter(Package %in% unlist(deps), !(Package %in% installed)) |>
    dplyr::mutate(RepoName = dplyr::recode(
      Repository,
      !!!repo_names
    )) |>
    dplyr::select(Package, RepoName) |>
    tibble::as_tibble()
}

#' @title Format dependencies for conda
#' @description This function formats the dependencies for conda
#' @param deps A tibble containing the dependencies
#' @return A character vector containing the dependencies formatted for conda
format_for_conda <- function(deps) {
  deps |>
    dplyr::mutate(
      conda_pkg = dplyr::case_when(
        RepoName == "CRAN" ~ paste0("r-", Package),
        RepoName == "BioCsoft" ~ paste0("bioconductor-", Package)
      )
    ) |>
    dplyr::pull(conda_pkg)
}


check_dependencies(pkg_name) |>
  format_for_conda() |>
  writeLines(opt$output)
