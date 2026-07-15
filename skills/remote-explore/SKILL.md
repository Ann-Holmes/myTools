---
name: remote-explore
description: >
  Non-interactively explore remote servers via SSH to browse directories, search for files,
  and download them. TRIGGER whenever the user asks to look at, list, browse, find, search,
  or explore files/directories on a remote server, SSH host, or any machine that isn't local.
  Also trigger when the user wants to download or fetch files from a remote server. Covers
  use cases like "show me what's on that server", "find files on the remote", "scp something
  from the host", or any mention of a remote host combined with file operations.
---

# Remote Server Explorer

Explore remote servers non-interactively using SSH, `find`, and `scp`. Designed for AI agents
that cannot hold interactive sessions — every command is a single shot.

## How to specify the remote host

Accept any of these formats (try the shortest form first):

- **SSH alias** from `~/.ssh/config` (e.g. `PIT`, `prod-web`)
- **user@host** (e.g. `root@10.0.1.5`, `deploy@web.example.com`)
- **host** (e.g. `192.168.1.100` — uses the current local username)

If the user gives an alias and it fails, fall back to asking them for the correct connection string.

## Workflow

The typical flow is: **browse → search → download**. Let the user guide which step to do next.

### 1. Browse directories

Use `ls` via SSH to look around:

```bash
ssh HOST 'ls /path'
ssh HOST 'ls -la /path'
ssh HOST 'ls -lh /path/to/dir'
```

When the user says something like "看看有什么" or "list the contents" or "what's in that directory", use this.

Start broad (home directory or a path the user mentions) and narrow down based on what you see. Present the results and ask the user which directory to explore next.

### 2. Search for files

When the user has a rough idea of what they're looking for (file name, type, date, size), use `find`:

```bash
# By name/pattern
ssh HOST 'find /search/path -name "*.log" -type f'

# By modification time (last N days)
ssh HOST 'find /search/path -type f -mtime -7'

# By size
ssh HOST 'find /search/path -type f -size +100M'

# Limit depth (faster, avoids scanning unrelated areas)
ssh HOST 'find /search/path -maxdepth 3 -type f'

# Show only directories
ssh HOST 'find /search/path -maxdepth 2 -type d'

# Combine conditions
ssh HOST 'find /search/path -name "*.tar.gz" -size +50M -mtime -30'
```

Key flags: `-maxdepth N` (limit depth), `-type f` (files only), `-type d` (directories only), `-mtime -N` (modified within N days), `-size +N` (larger than N), `-name "pattern"` (name match).

### 3. Download files

Once the target is identified, use `scp`:

```bash
# Single file
scp HOST:/path/to/file ./local/path/

# Multiple files by pattern
scp 'HOST:/path/*.tar.gz' ./local/path/

# Entire directory
scp -r HOST:/path/to/dir ./local/path/
```

### 4. Read remote files (optional)

If the user wants to preview a file's content before downloading:

```bash
ssh HOST 'head -100 /path/to/file'
ssh HOST 'wc -l /path/to/file'
ssh HOST 'file /path/to/file'
ssh HOST 'stat /path/to/file'
```

## Tips

- Always quote the remote command: `ssh HOST 'command'`
- If a command times out, the remote path might be huge — add `-maxdepth` to `find` or narrow the search scope
- If `scp` with glob patterns fails, try wrapping the remote path: `scp 'HOST:/path/*.log' ./`
- For large file listings, pipe through `head` or `tail` to avoid flooding context: `ssh HOST 'ls /huge/dir | head -50'`
- Respect the user's intent: don't download or read files they didn't ask for. Browse and search are safe; downloading and reading require explicit request.
