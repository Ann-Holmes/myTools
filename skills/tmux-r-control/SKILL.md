---
name: tmux-r-control
description: >
  Control R sessions (radian) running in tmux panes. TRIGGER whenever the user wants to execute R code,
  run R commands, visualize data with ggplot2, install R packages, or interact with an R console that is
  running inside tmux. Also trigger when the user says things like "run this in R", "在 R 里运行",
  "用 tmux 执行 R", "画个图", or any request involving R code execution that should happen in an existing
  terminal session rather than a new ephemeral R process.
---

# Tmux R Session Controller

Execute R code in an existing radian/R session running inside a tmux pane. This allows Claude to
run R commands, read outputs, and return results — including plots — without starting a new R process.

## Why this matters

Running R code via `Rscript -e "..."` starts a fresh process each time, losing the session state
(library loads, data objects, environment). By controlling the radian session in tmux, the R
environment persists across commands, which is essential for interactive data analysis workflows.

## Discover the target pane

Before sending any commands, identify which tmux pane runs radian:

1. List sessions: `tmux ls`
2. Ask the user which session (and optionally window/pane) to use
3. List panes: `tmux list-panes -t <session>:<window> -F "#{pane_index} #{pane_current_command}"`
4. Confirm the target pane with the user

**Note:** radian is a Python-based R console, so `pane_current_command` may show `python3.12` or
similar, NOT `radian`. Verify by checking the prompt — radian shows `r$>`. Always capture the pane
content to confirm before proceeding.

Store the target as `<session>:<window>.<pane>` for subsequent commands.

## Command execution strategy

Choose based on complexity:

### Single-line commands
Send directly via `tmux send-keys`:
```bash
tmux send-keys -t <target> 'library(ggplot2)' Enter
```

### Multi-line analysis → write scripts, then source
For any non-trivial analysis (data loading, multiple steps, plots), write R scripts to disk and
`source()` them. This is critical because:

- If a script errors, fix the script and re-source — no need to rewrite from scratch
- Scripts accumulate into a reproducible analysis pipeline
- The user can review, reuse, and build on them later

## Analysis script organization

Follow this directory structure:

```
code/
├── utils/                    # Reusable utility functions
│   └── read_data.R
├── some_analysis/            # One directory per analysis
│   ├── main.R               # Entry point: sources sub-scripts in order
│   ├── 01_load_data.R       # Data loading & cleaning
│   ├── 02_explore_X.R       # One analysis task per script
│   └── 03_explore_Y.R

result/
└── some_analysis/            # All outputs for this analysis
    ├── figures/              # Saved plots (ggsave)
    ├── tables/               # Tables/CSVs (write_csv)
    └── ...                   # Other output files

docs/
└── some_analysis/            # Analysis notes, reports, memos, records
    ├── report.md
    └── ...                   # Any documentation referencing result/ outputs
```

Key conventions:
- **Numbered prefix** (`01_`, `02_`) ensures clear execution order
- **Main script** (`main.R`) sources sub-scripts sequentially
- **One task per sub-script**: typically one statistical analysis + one visualization
- **Sub-scripts execute directly**, not as function definitions — R objects are shared in the session
- **Utilities** in `code/utils/` are sourced by sub-scripts as needed
- **Output paths**: use `file.path(PROJECT_DIR, "result/<analysis>/figures/...", "result/<analysis>/tables/...")`
- **Docs** can use relative paths like `![](../../result/some_analysis/figures/plot.png)` to embed outputs, and are not limited to reports — any notes, memos, or analysis records go here

### Path handling — always use absolute paths

`here::here()` depends on project markers (`.Rproj`, `.git`) and may resolve to wrong directories.
Instead, define `PROJECT_DIR` in the main script and use `file.path()` everywhere:

```r
PROJECT_DIR <- "/path/to/project"
source(file.path(PROJECT_DIR, "code/utils/read_data.R"))
write_csv(result, file.path(PROJECT_DIR, "tables/my_analysis/output.csv"))
ggsave("plot.png", path = file.path(PROJECT_DIR, "figures/my_analysis"))
```

### Script workflow

1. Write the script file to disk using the Write tool
2. `source()` it in the radian session via `tmux send-keys`
3. Capture output to check for errors
4. If errors: fix the script in place, re-source — never create new temp files
5. For new analysis steps: add a new numbered sub-script, update `main.R`

## Read R output

After sending a command, wait and then capture the pane content:

```bash
sleep 2  # adjust based on command complexity
tmux capture-pane -t <target> -p
```

For quick commands, `sleep 2` is usually enough. For data-heavy operations or complex plots,
use `sleep 5` or longer. Use `tail` to focus on recent output:

```bash
tmux capture-pane -t <target> -p | tail -20
```

## Plotting with httpgd

When the user wants to visualize data:

1. Check if httpgd is already running by capturing the pane output and looking for an httpgd URL
2. If not running, start it:
   ```bash
   tmux send-keys -t <target> 'library(httpgd); hgd()' Enter
   sleep 2
   tmux capture-pane -t <target> -p | grep -o 'http://[^ ]*' | tail -1
   ```
3. Send the ggplot2/plot command
4. Return the httpgd URL to the user so they can view the plot in their browser

During exploration, plots are viewed via httpgd. After analysis is finalized, add `ggsave()`
to save plots to `figures/<analysis_name>/`.

## Common patterns

### Install a package
```bash
tmux send-keys -t <target> 'install.packages("packagename", repos="https://cloud.r-project.org")' Enter
```

### Run a complete analysis
1. Write scripts to `code/<analysis_name>/`
2. `tmux send-keys -t <target> 'source("/path/to/code/<analysis_name>/main.R")' Enter`
3. Capture and verify output

### Quick one-off check
```bash
tmux send-keys -t <target> 'sessionInfo()' Enter
```

## Error handling

If the captured output shows an `Error in` message:
1. Parse the error message from the output
2. If it's in a sourced script: fix the script file, then re-source it
3. If it's a one-liner: fix and resend
4. Report the error to the user with context

## Important notes

- The user's R session state is valuable — avoid commands that could clear the workspace (like `rm(list=ls())`) unless explicitly asked
- If the radian prompt shows `r$>` the session is ready for input; if not, wait longer before sending the next command
- httpgd plots persist on the server — the user can refresh the browser URL to see updated plots
- Always use absolute paths with `file.path()` — never rely on `here::here()` unless the project has proper markers
