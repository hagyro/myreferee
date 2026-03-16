# myreferee

An AI-powered referee agent that provides rigorous, journal-specific reviews of academic papers in economics and finance.

## Features

- **Journal-calibrated reviews**: Researches target journals (aims & scope, recent publications, referee priors)
- **Multi-format support**: PDF, Word (.docx), and LaTeX (.tex) papers
- **Academic database integration**: Scopus and ScienceDirect APIs for comprehensive journal analysis
- **Persistent review history**: Track R&R submissions and compare versions
- **Markdown output**: Clean, portable referee reports
- **CLI tool**: Callable from any directory once installed
- **Web interface**: Localhost browser UI for uploading papers and downloading reports

## Prerequisites

1. **Claude Code** installed on your system
2. **Python 3.10+**
3. **uv** package manager (recommended)
4. **Elsevier API key** (optional, for Scopus/ScienceDirect access)

## Installation

### 1. Install Claude Code

```bash
# macOS/Linux
curl -fsSL https://claude.ai/install.sh | bash

# Homebrew
brew install --cask claude-code

# Windows (WinGet)
winget install Anthropic.ClaudeCode
```

### 2. Clone or download this project

```bash
git clone https://github.com/hagyro/myreferee.git
cd myreferee
```

### 3. Install with uv

```bash
# Create virtual environment and install
uv venv
uv pip install -e .
```

Or with pip:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 4. Configure API keys (optional)

Set the Elsevier API key for enhanced journal research:

```bash
export ELSEVIER_API_KEY=your-elsevier-api-key
```

Or create a `.env` file:
```
ELSEVIER_API_KEY=your-elsevier-api-key
```

## Usage

### Start the agent

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Run interactively
myreferee

# Or with a paper
myreferee -p path/to/paper.pdf
```

### Basic workflow

1. **Specify target journal**
   - Provide 1-3 candidate journals
   - Indicate if first submission or R&R

2. **Agent researches the journal**
   - Pulls aims & scope, author guidelines
   - Analyzes 20-40 recent articles
   - Infers referee priors (methods, contribution framing, etc.)

3. **Upload your paper**
   - Provide file path
   - Supports PDF, Word, LaTeX

4. **Agent delivers structured review**
   - Summary (2-3 sentences)
   - Contribution & fit assessment
   - Major concerns (deal-breakers)
   - Minor concerns
   - Robustness/diagnostics checklist
   - Section-by-section rewrite suggestions
   - Positioning vs. journal's recent papers

5. **Output saved to `~/.local/share/myreferee/reviews/`**

### Web interface

myreferee also provides a browser-based interface running on localhost. Upload papers via drag-and-drop, track review progress in real time, and download `.md` reports to any destination.

```bash
# Launch the web UI (default: http://127.0.0.1:5000)
myreferee --web

# Use a custom port
myreferee --web --port 8080

# Or use the standalone command
myreferee-web
```

The web interface provides:
- **Upload form**: Drag-and-drop or click to upload `.pdf`, `.tex`, or `.docx` files
- **Journal selection**: Specify the target journal before submitting
- **Live progress**: Status bar tracks each stage (parsing, research, review)
- **Download**: Save the `.md` report to any location on your machine
- **Review history**: Browse and re-download all past reviews

### Command-line options

```bash
myreferee --help                    # Show all options

myreferee -p paper.pdf              # Start with a paper

myreferee -p paper.pdf -j "Journal of Finance"  # Non-interactive mode

myreferee --resume SESSION_ID       # Resume a previous session

myreferee --list-reviews            # List past reviews

myreferee --list-sessions           # List saved sessions

myreferee -o ./my-reviews           # Custom output directory

myreferee --show-prompt -p paper.pdf  # Show review prompt without running

myreferee --web                     # Launch web interface

myreferee --web --port 8080         # Web interface on custom port
```

## Configuration

Default configuration is bundled with the package. To customize, create `~/.config/myreferee/settings.yaml`:

```yaml
# API settings
api:
  scopus:
    results_per_journal: 30
    years_back: 5

# Output preferences
output:
  format: markdown
  include:
    editor_note: true
    todo_list: true

# Review depth
review:
  section_by_section: true
  positioning_analysis: true
```

## Data Storage

- **Reviews**: `~/.local/share/myreferee/reviews/`
- **Sessions**: `~/.local/share/myreferee/sessions/`
- **Config**: `~/.config/myreferee/settings.yaml`

## Project Structure

```
myreferee/
├── pyproject.toml          # Package definition
├── README.md
├── src/
│   └── myreferee/
│       ├── __init__.py
│       ├── __main__.py     # python -m myreferee
│       ├── cli.py          # CLI entry point
│       ├── agent.py        # Core agent logic
│       ├── config.py       # Configuration handling
│       ├── web.py          # Flask web interface
│       ├── templates/
│       │   └── index.html  # Web UI template
│       ├── tools/
│       │   ├── paper_parser.py
│       │   ├── journal_research.py
│       │   └── report_generator.py
│       └── prompts/
│           └── system_prompt.py
└── config/
    └── settings.yaml       # Default configuration
```

## Getting Elsevier API Keys

1. Go to [dev.elsevier.com](https://dev.elsevier.com)
2. Register with your institutional email
3. Create an API key (free for academic use)
4. Ensure you're on campus network or VPN for full access

## Troubleshooting

### "Claude CLI not found"
- Install Claude Code: https://claude.ai/code
- Ensure `claude` is in your PATH

### "Scopus API rate limit exceeded"
- Wait 1-2 minutes between requests
- Ensure you're on institutional network for higher limits

### "Paper extraction failed"
- For scanned PDFs, OCR may be needed
- Try converting to different format

### "Session not found"
- Session IDs expire after 30 days
- Use `myreferee --list-sessions` to see available sessions

## License

For personal and academic use.
