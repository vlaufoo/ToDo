# MyToDo App

A beautiful, feature-rich, cross-platform To-Do and Journaling application built in Python using **Flet** for a premium reactive UI and **SQLite** for offline storage.

## Features & Features Met

*   **Cross-platform Compatibility**: Designed for Windows (native executable) and Linux (tested for Debian 13 Trixie).
*   **Arbitrary Task Tree Hierarchy**: Supports linking subtasks and parent tasks with cyclic dependency checking.
*   **Journal Entries**: Write notes, ideas, and logs, then link them directly to tasks.
*   **Email Metadata Integration**: Attach email history (date, subject, people) to keep context in one place.
*   **Custom Styling without Recompiling**: Configurable markdown renderer dynamically styled by a `style_config.json` file in the user config folder. Reload stylesheet instantly at runtime using the "Reload Stylesheet" button.
*   **Local Attachments Storage**: Uploaded files/images are copied into local app directory, keeping path references relative and completely portable between machines.

---

## Getting Started

### 1. Prerequisites
Ensure you have `pyenv` and virtual environment support installed.

### 2. Set Local Python & Initialize Virtual Env
Run the following commands in the project directory:
```bash
# Sets pyenv version
pyenv local 3.13.2

# Create venv and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the App
To run the app in desktop mode:
```bash
.venv/bin/flet run main.py
```

To run the app as a web application in your browser (useful if running headless or over SSH):
```bash
.venv/bin/flet run --web main.py
```

---

## Customizing Styling (No Recompiling)

When the app runs for the first time, it generates a standard theme configuration file `style_config.json` in the user's application directory:
*   **Linux**: `~/.local/share/MyToDo/style_config.json`
*   **Windows**: `%APPDATA%\MyToDo\style_config.json`

### Example `style_config.json`
You can open this file and modify values to customize the UI colors and font sizes:
```json
{
    "theme_mode": "dark",
    "primary_color": "#6366F1",
    "bg_color": "#0F172A",
    "card_bg_color": "#1E293B",
    "text_color": "#F8FAFC",
    "text_muted": "#94A3B8",
    "md_body_font_size": 15,
    "md_body_color": "#E2E8F0",
    "md_body_font_family": "Segoe UI, sans-serif",
    "md_h1_font_size": 24,
    "md_h1_color": "#F1F5F9",
    "md_h2_font_size": 20,
    "md_h2_color": "#E2E8F0",
    "md_h3_font_size": 17,
    "md_h3_color": "#CBD5E1",
    "md_link_color": "#38BDF8",
    "md_code_bg_color": "#0F172A",
    "md_code_color": "#38BDF8"
}
```
*Tip: After modifying this file, click the **Reload stylesheet** button inside any task's notes pane to see your styling changes update in real-time.*

---

## Compiling for Windows & Linux

To compile the application into a standalone executable (no Python installation required for the user), use `flet pack` (which uses PyInstaller):

### Install Packaging Tool
```bash
.venv/bin/pip install pyinstaller
```

### Build on Windows (Creates `.exe`)
Run this on a Windows machine:
```cmd
.venv\Scripts\flet pack main.py --icon icon.ico --name "MyToDo"
```

### Build on Linux (Creates Binary)
Run this on a Debian/Ubuntu machine:
```bash
.venv/bin/flet pack main.py --name "mytodo"
```

The compiled assets will be placed inside the `dist/` folder.

---

## Project Structure

*   [models.py](file:///home/vlaufoo/Projects/mytodo/models.py): Core Python dataclasses (`Task`, `JournalEntry`, `EmailInfo`).
*   [database.py](file:///home/vlaufoo/Projects/mytodo/database.py): SQLite initialization, cycle detection, file attachment coping, and CRUD interfaces.
*   [styles.py](file:///home/vlaufoo/Projects/mytodo/styles.py): Helper methods to parse and compile dynamically loaded styles from `style_config.json`.
*   [main.py](file:///home/vlaufoo/Projects/mytodo/main.py): Reactive Flet-based user interface.
