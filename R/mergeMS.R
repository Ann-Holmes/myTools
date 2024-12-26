suppressMessages(library(tidyverse))
suppressMessages(library(readxl))
suppressMessages(library(openxlsx))
suppressMessages(library(optparse))


# Preface: Function Define ------------------------------------------------

extract_gn <- function(df) {
  df <- mutate(df, gene_name = str_extract(Description, "(?<=GN=)[^\\s]+"))
  return(df)
}


# Section1: Merge ---------------------------------------------------------

option <- list(
  make_option(c("-p", "--prefix"), type = "character", help = "The Directory of files"),
  make_option(c("-o", "--output"), type = "character", help = "The output filename")
)
args <- parse_args(OptionParser(
  option_list = option, prog = "mergeMS",
  description = "Merge ProteinDiscovery outputs to one excel file"
))


# prefix <- "/mnt/d/work/project/Others/210803_zmq/data"
files <- list.files(args$prefix, full.names = T)
file_names <- str_remove(basename(files), "\\.xlsx$") %>%
  str_replace_all("\\s|-", "_")

tabs <- map(files, read_excel, .name_repair = ~ str_replace_all(.x, "\\s|-", "_"))
names(tabs) <- file_names

# Compute norm_PSM_MW = PSM/MW * 100
norm_PSM_MW <- function(tab) {
  tab %>%
    mutate(PSM_MW_norm = `#_PSMs` / `MW_[kDa]` * 100)
}
tabs <- map(tabs, norm_PSM_MW)


# Merge whole tables
tabs_merged <- bind_rows(tabs) %>%
  select(Accession, Description) %>%
  distinct()

for (file in file_names) {
  tabs_merged <- tabs_merged %>%
    left_join(select(tabs[[file]], -Description),
      by = "Accession",
      suffix = c("", str_glue("_{file}"))
    )
}
tabs_merged <- rename_with(
  tabs_merged,
  ~ str_glue("{.x}_{file_names[1]}"),
  `Coverage_[%]`:`#_Peptides_(by_Search_Engine):_Sequest_HT`
)

tabs_merged_psm <- tabs_merged %>%
  extract_gn() %>%
  select(Accession, Description, Symbol = gene_name, starts_with("#_PSMs"))

tabs_merged_psm_mw <- tabs_merged %>%
  extract_gn() %>%
  select(Accession, Description, Symbol = gene_name, starts_with("PSM_MW_norm"))

tabs_merged_psm_mw <- rename_with(
  tabs_merged_psm_mw,
  ~ str_glue("{.x}_{file_names[1]}"),
  PSM_MW_norm
)

write.xlsx(list(PSM_MW_norm = tabs_merged_psm_mw, PSM = tabs_merged_psm, Whole_table = tabs_merged),
  file = str_glue(args$output)
)
