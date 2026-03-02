# File Organiser

A native desktop file manager with NLP-powered search and file operations, using Ollama for fully offline natural language processing.

## Features

- **Windows Explorer-style UI** — folder tree, file table with sortable columns, detail panel
- **Full file management** — create folders, copy, move, rename, delete (to recycle bin)
- **Tags & Stars** — tag files with custom labels, star/favorite files
- **Natural language search** — "find all PDFs larger than 10MB modified this week"
- **NLP file operations** — "move all screenshots from Downloads to Pictures"
- **On-demand indexing** — index specific folders for fast NLP-powered search
- **Operation history** — log of all actions with undo support
- **AI Chat Panel** — chat interface on the right with message history and AI responses
- **AI navigation** — "go to Downloads" or "open Documents/Projects" navigates the file manager
- **Disk Cleanup** — find largest files, detect potential duplicates, AI-powered cleanup suggestions
- **Auto-updates** — checks GitHub releases for new versions and self-updates the exe
- **Keyboard shortcuts** — Ctrl+C/V/X, F2 rename, Delete, Ctrl+N new folder, Ctrl+L focus chat

## Download

Download the latest `.exe` from [GitHub Releases](https://github.com/pratik-shivnani/FileOrganiser/releases). No installation needed — just run it.

The app checks for updates on startup and can self-update from **Help → Check for Updates**.

## Prerequisites

1. **Python 3.12+**
2. **Ollama** installed and running
   - Install: https://ollama.ai
   - Start: `ollama serve`
   - Pull model: `ollama pull llama3.2:3b`

## Installation

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Usage

### Basic Navigation
- Click folders in the tree panel to browse
- Double-click files to open them
- Use the path bar to navigate directly

### AI Chat Panel (Ctrl+L)
The chat panel on the right side lets you interact with the AI assistant. Type natural language queries and get responses:

- `go to Downloads` — navigates to the folder
- `find all PDFs in Documents` — searches indexed files
- `show files larger than 100MB` — filters by size
- `move screenshots from Downloads to Pictures` — moves files with confirmation
- `star all Python files in Projects` — stars matching files
- `tag invoices as finance` — tags matching files
- `what's taking up space?` — shows largest files
- `create a folder called Archives in Documents` — creates folders

**Note:** Folders must be indexed first for search to work. Click "Index Folder" in the toolbar.

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+L | Focus chat input |
| Ctrl+N | New folder |
| Ctrl+Z | Undo last operation |
| F2 | Rename selected |
| F5 | Refresh |
| Delete | Delete selected |
| Alt+Up | Navigate up |
| Ctrl+H | Operation history |
| Ctrl+Shift+D | Disk cleanup |

## Tech Stack

- **PyQt6** — native desktop UI
- **Ollama** (`llama3.2:3b`) — local NLP, no API keys needed
- **SQLite** — file index, tags, stars, operation history
