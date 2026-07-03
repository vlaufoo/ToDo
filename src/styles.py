import os
import json
import flet as ft
from database import get_app_dir

STYLE_CONFIG_FILE = "style_config.json"

# Default theme configuration
DEFAULT_STYLE = {
    "theme_mode": "dark",  # "dark" or "light"
    "primary_color": "#6366F1",  # Indigo
    "bg_color": "#0F172A",       # Slate 900
    "card_bg_color": "#1E293B",  # Slate 800
    "text_color": "#F8FAFC",     # Slate 50
    "text_muted": "#94A3B8",     # Slate 400
    
    # Markdown Rendering Styling
    "md_body_font_size": 15,
    "md_body_color": "#E2E8F0",  # Slate 200
    "md_body_font_family": "Segoe UI, sans-serif",
    
    "md_h1_font_size": 24,
    "md_h1_color": "#F1F5F9",    # Slate 100
    
    "md_h2_font_size": 20,
    "md_h2_color": "#E2E8F0",
    
    "md_h3_font_size": 17,
    "md_h3_color": "#CBD5E1",
    
    "md_link_color": "#38BDF8",  # Sky 400
    "md_code_bg_color": "#0F172A",
    "md_code_color": "#38BDF8"
}

def load_style_config() -> dict:
    """Loads styling configuration from style_config.json or creates it with defaults if not present."""
    config_path = os.path.join(get_app_dir(), STYLE_CONFIG_FILE)
    if not os.path.exists(config_path):
        try:
            with open(config_path, "w") as f:
                json.dump(DEFAULT_STYLE, f, indent=4)
        except Exception:
            pass
        return DEFAULT_STYLE.copy()
    
    try:
        with open(config_path, "r") as f:
            user_config = json.load(f)
            # Merge with defaults to ensure all keys are present
            merged = DEFAULT_STYLE.copy()
            merged.update(user_config)
            return merged
    except Exception:
        return DEFAULT_STYLE.copy()

def get_markdown_styles(config: dict) -> dict:
    """Creates Flet TextStyles for Markdown rendering based on configuration."""
    body_style = ft.TextStyle(
        size=config.get("md_body_font_size", 15),
        color=config.get("md_body_color", "#E2E8F0"),
        font_family=config.get("md_body_font_family", "Segoe UI, sans-serif")
    )
    
    h1_style = ft.TextStyle(
        size=config.get("md_h1_font_size", 24),
        color=config.get("md_h1_color", "#F1F5F9"),
        weight=ft.FontWeight.BOLD,
        font_family=config.get("md_body_font_family", "Segoe UI, sans-serif")
    )
    
    h2_style = ft.TextStyle(
        size=config.get("md_h2_font_size", 20),
        color=config.get("md_h2_color", "#E2E8F0"),
        weight=ft.FontWeight.BOLD,
        font_family=config.get("md_body_font_family", "Segoe UI, sans-serif")
    )
    
    h3_style = ft.TextStyle(
        size=config.get("md_h3_font_size", 17),
        color=config.get("md_h3_color", "#CBD5E1"),
        weight=ft.FontWeight.BOLD,
        font_family=config.get("md_body_font_family", "Segoe UI, sans-serif")
    )
    
    link_style = ft.TextStyle(
        color=config.get("md_link_color", "#38BDF8"),
        decoration=ft.TextDecoration.UNDERLINE
    )
    
    code_style = ft.TextStyle(
        color=config.get("md_code_color", "#38BDF8"),
        font_family="Courier New, monospace"
    )
    
    return {
        #"body_style": body_style,
        "h1_text_style": h1_style,
        "h2_text_style": h2_style,
        "h3_text_style": h3_style,
        "a_text_style": link_style,
        "code_text_style": code_style
    }
