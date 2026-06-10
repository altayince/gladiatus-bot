# GLA - Gladiatus Automation Bot

GLA is a Python + Selenium automation tool for Gladiatus. It logs in, manages the game tab, and runs selected mechanics from the GUI or the CLI.

## What GLA Can Do
- Log in with saved or CLI-provided credentials
- Find and activate the active game tab
- Check expedition readiness and trigger the expedition flow
- Pick a specific expedition target from the GUI and keep that choice between restarts
- Check dungeon readiness and click a random dungeon attack target
- Check Circus Turma readiness and attack the lowest-level target
- Refill HP when the current HP drops below a threshold
- Show the current refill potion count from the first inventory bag on the main screen
- Run from the GUI or from the command line

## Workflow
Every change follows the same issue-first flow:
1. Create a GitHub issue and describe the task.
2. Assign the issue to `@me`.
3. Create a branch named `feature/GLA-[ticket]-description` or `bugfix/GLA-[ticket]-description`.
4. Do the work only on that branch.
5. Open a PR into `main`.
6. Review the PR yourself and merge once checks pass.

Direct pushes to `main` are blocked by GitHub branch protection and local hooks. When a PR is merged, the linked GLA issue closes automatically; closing or deleting the PR leaves the issue open.

See [WORKFLOW.md](WORKFLOW.md) for the full process.

## Requirements
- Python 3.10+
- Google Chrome or a compatible browser

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

To enable the local guard rails, run:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-githooks.ps1
```

## Usage
Fill in `.env` first. See `env.example` for the expected keys.

Run from the command line:
```bash
python -m src.main
```

Run the GUI:
```bash
python gui_main.py
```

## CLI Options
- `--username`: Override the username
- `--password`: Override the password
- `--base-url`: Override the target base URL
- `--headless true|false`: Run the browser headless or visible
- `--no-close`: Keep the browser open on error

## Notes
- Game selectors and flow logic live in `src/selenium_bot.py`.
- The GUI uses the same bot class and provides one panel for the main mechanics.
- The GUI now splits main controls from expedition details, so the expedition target lives in its own tab.

