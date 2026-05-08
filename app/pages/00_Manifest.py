"""Asset manifest editor."""

import streamlit as st
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Asset

st.set_page_config(page_title="Manifest", page_icon="📋")
st.title("📋 Manifest")
st.markdown("Define and manage the assets your game needs.")

db = SessionLocal()

tab1, tab2 = st.tabs(["Assets", "Add Asset"])

with tab1:
    st.header("Asset Registry")

    assets = db.query(Asset).filter(Asset.deleted_at == None).all()

    if not assets:
        st.info("No assets defined yet. Create one in the 'Add Asset' tab.")
    else:
        # Display as a table
        for asset in assets:
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 2, 1])
            with col1:
                st.write(f"**{asset.asset_id}**")
            with col2:
                st.write(asset.category)
            with col3:
                st.write(f"{asset.sprite_width_px}×{asset.sprite_height_px}")
            with col4:
                st.write(asset.display_name or "-")
            with col5:
                if st.button("Edit", key=f"edit_{asset.id}"):
                    st.session_state[f"editing_{asset.id}"] = True

        st.divider()
        st.subheader("Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Assets", len(assets))
        with col2:
            categories = set(a.category for a in assets)
            st.metric("Categories", len(categories))
        with col3:
            animated = sum(1 for a in assets if a.animation_type != "static")
            st.metric("Animated", animated)

with tab2:
    st.header("Create New Asset")

    with st.form("add_asset_form"):
        asset_id = st.text_input("Asset ID (e.g., creep_01)", help="Unique identifier")
        category = st.text_input("Category (e.g., creep)", help="Group name for atlas packing")
        display_name = st.text_input("Display Name", help="Human-readable name")
        description = st.text_area("Description", help="Optional notes")

        col1, col2 = st.columns(2)
        with col1:
            sprite_width = st.number_input("Sprite Width (px)", min_value=16, max_value=512, value=64)
        with col2:
            sprite_height = st.number_input("Sprite Height (px)", min_value=16, max_value=512, value=64)

        animation_type = st.selectbox(
            "Animation Type",
            ["static", "loop", "transition"],
            help="static = single frame, loop = repeating animation, transition = one-time animation",
        )

        frame_count = 1
        if animation_type != "static":
            frame_count = st.number_input("Frame Count", min_value=2, max_value=32, value=4)

        submitted = st.form_submit_button("Create Asset")

        if submitted:
            if not asset_id or not category:
                st.error("Asset ID and Category are required")
            else:
                existing = db.query(Asset).filter(Asset.asset_id == asset_id).first()
                if existing:
                    st.error(f"Asset '{asset_id}' already exists")
                else:
                    asset = Asset(
                        asset_id=asset_id,
                        category=category,
                        display_name=display_name,
                        description=description,
                        sprite_width_px=sprite_width,
                        sprite_height_px=sprite_height,
                        animation_type=animation_type,
                        frame_count=frame_count,
                    )
                    db.add(asset)
                    db.commit()
                    st.success(f"Asset '{asset_id}' created!")
                    st.rerun()

db.close()
