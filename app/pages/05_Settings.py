"""Configuration and style anchor management."""

import streamlit as st
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Asset, StyleAnchor

st.set_page_config(page_title="Settings", page_icon="⚙️")
st.title("⚙️ Settings")

db = SessionLocal()

tab1, tab2 = st.tabs(["Style Anchors", "Configuration"])

with tab1:
    st.header("Style Anchors")
    st.markdown("Define generation recipes for consistent asset regeneration.")

    assets = db.query(Asset).filter(Asset.deleted_at == None).all()

    if not assets:
        st.info("Create assets in Manifest first.")
    else:
        selected_asset_id = st.selectbox(
            "Asset",
            [a.asset_id for a in assets],
            key="anchor_asset_selector",
        )

        asset = next(a for a in assets if a.asset_id == selected_asset_id)
        anchors = db.query(StyleAnchor).filter(StyleAnchor.asset_id == selected_asset_id).all()

        if anchors:
            st.subheader("Existing Anchors")
            for anchor in anchors:
                with st.expander(f"{anchor.anchor_id}" + (" 🔒" if anchor.is_locked else "")):
                    st.write(f"**Prompt:** {anchor.prompt_template}")
                    if anchor.seed:
                        st.write(f"**Seed:** {anchor.seed}")
                    if anchor.base_negative_prompt:
                        st.write(f"**Negative:** {anchor.base_negative_prompt}")

        st.divider()
        st.subheader("Create Anchor")

        with st.form(f"anchor_form_{selected_asset_id}"):
            anchor_id = st.text_input("Anchor ID", help="e.g., creep_01_v1")
            prompt = st.text_area("Prompt Template", help="Main generation prompt")
            seed = st.number_input("Seed (optional)", min_value=0, max_value=2147483647, value=0)
            negative_prompt = st.text_area("Negative Prompt (optional)")

            submitted = st.form_submit_button("Create Anchor")

            if submitted:
                if not anchor_id or not prompt:
                    st.error("Anchor ID and Prompt are required")
                else:
                    existing = db.query(StyleAnchor).filter(
                        StyleAnchor.anchor_id == anchor_id
                    ).first()
                    if existing:
                        st.error(f"Anchor '{anchor_id}' already exists")
                    else:
                        anchor = StyleAnchor(
                            anchor_id=anchor_id,
                            asset_id=selected_asset_id,
                            prompt_template=prompt,
                            seed=seed if seed > 0 else None,
                            base_negative_prompt=negative_prompt if negative_prompt else None,
                        )
                        db.add(anchor)
                        db.commit()
                        st.success(f"Anchor '{anchor_id}' created!")
                        st.rerun()

with tab2:
    st.header("Configuration")
    st.markdown("Environment and storage settings.")

    from app.config import Config

    st.write(f"**Storage Backend:** {Config.STORAGE_BACKEND}")
    st.write(f"**Generation Model:** {Config.GENERATION_MODEL}")
    st.write(f"**Batch Size:** {Config.BATCH_SIZE}")
    st.write(f"**Max Retries:** {Config.MAX_RETRY_ATTEMPTS}")
    st.write(f"**Background Removal:** {'Enabled' if Config.BACKGROUND_REMOVAL_ENABLED else 'Disabled'}")
    st.write(f"**Atlas Max Size:** {Config.MAX_ATLAS_WIDTH}×{Config.MAX_ATLAS_HEIGHT}")

    st.info("Edit .env file to change configuration. Restart app for changes to take effect.")

db.close()
