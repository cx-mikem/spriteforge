"""Streamlit entry point for spriteforge."""

import streamlit as st
from app.config import Config
from app.database import init_db

# Validate config at startup
try:
    Config.validate()
except ValueError as e:
    st.error(f"Configuration error: {e}")
    st.stop()

# Initialize database
init_db()

# Configure page
st.set_page_config(
    page_title="spriteforge",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎨 spriteforge")
st.markdown("Manifest-driven asset pipeline for 2D games")

st.sidebar.markdown("---")
st.sidebar.info(
    """
    **spriteforge** turns your art into repeatable build artifacts.

    - Generate sprites from prompts via ChatGPT
    - Review and approve before they enter the pipeline
    - Post-process (cleanup, align, resize)
    - Pack into game-engine-ready atlases

    Start with [Manifest](/manifest) to define your assets.
    """
)

st.markdown(
    """
    ### Welcome!

    Use the pages in the sidebar to:
    1. **Manifest** - Define what assets your game needs
    2. **Generate** - Create images from style anchors
    3. **Review** - Approve or reject generations
    4. **Gallery** - See all approved assets
    5. **Export** - Download engine-ready bundles
    6. **Settings** - Configure generation and storage
    """
)
