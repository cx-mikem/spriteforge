"""Animation preview component for sprite playback."""

import streamlit as st
from PIL import Image, ImageDraw
import json
from pathlib import Path
from io import BytesIO
import time


def animation_player(
    sprite_sheet_path: str,
    manifest_json_path: str,
    asset_id: str = None,
    width: int = 200,
    show_controls: bool = True,
    show_background: bool = False,
    background_color: tuple = (128, 128, 128),
):
    """
    Play an animated sprite from atlas.

    Args:
        sprite_sheet_path: Path to sprite sheet PNG
        manifest_json_path: Path to Phaser manifest JSON
        asset_id: If specified, play only this asset. If None, play all.
        width: Display width in pixels
        show_controls: Show FPS and zoom controls
        show_background: Display background color
        background_color: RGB tuple for background
    """

    # Load sprite sheet
    try:
        sprite_sheet = Image.open(sprite_sheet_path).convert("RGBA")
    except Exception as e:
        st.error(f"Could not load sprite sheet: {e}")
        return

    # Load manifest
    try:
        with open(manifest_json_path) as f:
            manifest = json.load(f)
    except Exception as e:
        st.error(f"Could not load manifest: {e}")
        return

    frames = manifest.get("frames", {})

    # Filter to single asset if specified
    if asset_id:
        frames = {k: v for k, v in frames.items() if k == asset_id or k.startswith(asset_id + "_")}

    if not frames:
        st.warning(f"No frames found for {asset_id or 'any assets'}")
        return

    # Extract frame data
    frame_list = []
    for asset_name, frame_data in frames.items():
        frame = frame_data.get("frame", {})
        frame_list.append({
            "name": asset_name,
            "x": frame.get("x", 0),
            "y": frame.get("y", 0),
            "width": frame.get("w", 64),
            "height": frame.get("h", 64),
        })

    if show_controls:
        col1, col2, col3 = st.columns(3)
        with col1:
            fps = st.slider("FPS", min_value=1, max_value=60, value=10)
        with col2:
            zoom = st.slider("Zoom", min_value=1, max_value=4, value=1)
        with col3:
            loop = st.checkbox("Loop", value=True)
    else:
        fps = 10
        zoom = 1
        loop = True

    frame_duration = 1.0 / fps

    # Animation loop
    frame_container = st.empty()
    frame_index = st.session_state.get(f"frame_{asset_id}", 0)

    # Play animation
    play_button, stop_button = st.columns(2)
    with play_button:
        play = st.button("▶️ Play", use_container_width=True)
    with stop_button:
        stop = st.button("⏹️ Stop", use_container_width=True)

    if play:
        st.session_state[f"frame_{asset_id}"] = 0
        frame_index = 0
        start_time = time.time()
        frame_count = len(frame_list)

        placeholder = st.empty()

        while True:
            elapsed = time.time() - start_time
            current_frame = int((elapsed / frame_duration) % frame_count)

            if not loop and current_frame >= frame_count:
                break

            frame_info = frame_list[current_frame]

            # Extract frame from sprite sheet
            frame_x = frame_info["x"]
            frame_y = frame_info["y"]
            frame_w = frame_info["width"]
            frame_h = frame_info["height"]

            frame_image = sprite_sheet.crop(
                (frame_x, frame_y, frame_x + frame_w, frame_y + frame_h)
            )

            # Add background if requested
            if show_background:
                bg = Image.new("RGBA", frame_image.size, background_color + (255,))
                bg.paste(frame_image, (0, 0), frame_image)
                frame_image = bg

            # Apply zoom
            if zoom > 1:
                new_size = (frame_w * zoom, frame_h * zoom)
                frame_image = frame_image.resize(new_size, Image.Resampling.NEAREST)

            # Display
            with placeholder.container():
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    st.image(
                        frame_image,
                        use_container_width=False,
                        width=min(width * zoom, 500),
                    )
                    st.caption(f"Frame {current_frame + 1}/{frame_count}")

            if stop:
                break

            time.sleep(frame_duration * 0.8)  # Slight margin for processing

    else:
        # Static preview of first frame
        if frame_list:
            frame_info = frame_list[0]
            frame_x = frame_info["x"]
            frame_y = frame_info["y"]
            frame_w = frame_info["width"]
            frame_h = frame_info["height"]

            frame_image = sprite_sheet.crop(
                (frame_x, frame_y, frame_x + frame_w, frame_y + frame_h)
            )

            if show_background:
                bg = Image.new("RGBA", frame_image.size, background_color + (255,))
                bg.paste(frame_image, (0, 0), frame_image)
                frame_image = bg

            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                st.image(frame_image, use_container_width=False, width=width)
                st.caption(f"Frame 1/{len(frame_list)}")


def sprite_sheet_browser(sprite_sheet_path: str, manifest_json_path: str):
    """
    Browse and preview individual sprites from a sheet.

    Args:
        sprite_sheet_path: Path to sprite sheet PNG
        manifest_json_path: Path to Phaser manifest JSON
    """

    # Load sprite sheet
    try:
        sprite_sheet = Image.open(sprite_sheet_path).convert("RGBA")
    except Exception as e:
        st.error(f"Could not load sprite sheet: {e}")
        return

    # Load manifest
    try:
        with open(manifest_json_path) as f:
            manifest = json.load(f)
    except Exception as e:
        st.error(f"Could not load manifest: {e}")
        return

    frames = manifest.get("frames", {})

    # Frame selector
    frame_names = list(frames.keys())
    selected_frame = st.selectbox("Select Frame", frame_names)

    if selected_frame:
        frame_data = frames[selected_frame]
        frame = frame_data.get("frame", {})

        frame_x = frame.get("x", 0)
        frame_y = frame.get("y", 0)
        frame_w = frame.get("w", 64)
        frame_h = frame.get("h", 64)

        # Extract and display
        frame_image = sprite_sheet.crop(
            (frame_x, frame_y, frame_x + frame_w, frame_y + frame_h)
        )

        col1, col2 = st.columns(2)
        with col1:
            st.image(frame_image, use_container_width=True)

        with col2:
            st.write(f"**Name:** {selected_frame}")
            st.write(f"**Position:** ({frame_x}, {frame_y})")
            st.write(f"**Size:** {frame_w}×{frame_h}px")

            # Show in context of full sheet
            st.write("**In Atlas:**")
            st.image(sprite_sheet, use_container_width=True, caption="Full sprite sheet")
