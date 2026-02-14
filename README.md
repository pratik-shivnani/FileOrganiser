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
- **Keyboard shortcuts** — Ctrl+C/V/X, F2 rename, Delete, Ctrl+N new folder, Ctrl+L command bar

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

### NLP Command Bar (Ctrl+L)
Type natural language queries in the command bar at the top:

- `find all PDFs in Documents`
- `show files larger than 100MB`
- `move screenshots from Downloads to Pictures`
- `star all Python files in Projects`
- `tag invoices as finance`
- `what's taking up space?`

**Note:** Folders must be indexed first for NLP search to work. Click "Index Folder" in the toolbar.

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+L | Focus command bar |
| Ctrl+N | New folder |
| Ctrl+Z | Undo last operation |
| F2 | Rename selected |
| F5 | Refresh |
| Delete | Delete selected |
| Alt+Up | Navigate up |
| Ctrl+H | Operation history |

## Tech Stack

- **PyQt6** — native desktop UI
- **Ollama** (`llama3.2:3b`) — local NLP, no API keys needed
- **SQLite** — file index, tags, stars, operation history
