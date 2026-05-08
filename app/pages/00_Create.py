"""Asset manifest editor."""

import streamlit as st
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Asset, StyleAnchor

st.set_page_config(page_title="Create", page_icon="📋")
st.title("📋 Create")
st.markdown("Define assets and write generation prompts for each one.")

db = SessionLocal()

tab3, tab1, tab2 = st.tabs(["Create Asset", "All Assets", "Style Anchors"])

with tab1:
    st.header("Asset Registry")

    assets = db.query(Asset).filter(Asset.deleted_at == None).all()

    if not assets:
        st.info("No assets defined yet. Create one in the 'Add Asset' tab.")
    else:
        anchored = {
            r[0] for r in db.query(StyleAnchor.asset_id).distinct().all()
        }

        for asset in assets:
            has_anchor = asset.asset_id in anchored
            status = "✅" if has_anchor else "⚠️ needs prompt"
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
                st.write(status)

        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Assets", len(assets))
        with col2:
            st.metric("Categories", len(set(a.category for a in assets)))
        with col3:
            st.metric("Animated", sum(1 for a in assets if a.animation_type != "static"))

        if len(anchored) < len(assets):
            missing = [a.asset_id for a in assets if a.asset_id not in anchored]
            st.warning(
                f"**{len(missing)} asset(s) still need a generation prompt** "
                f"before you can generate: {', '.join(missing)}\n\n"
                "→ Go to the **Style Anchors** tab above to add prompts."
            )

with tab2:
    st.header("Style Anchors")
    st.markdown(
        "A style anchor is a prompt + settings that tells the AI what to generate for each asset. "
        "Each asset needs at least one before you can generate images."
    )

    assets = db.query(Asset).filter(Asset.deleted_at == None).all()

    if not assets:
        st.info("Create assets first in the 'Add Asset' tab.")
    else:
        selected_asset_id = st.selectbox(
            "Select asset to configure",
            [a.asset_id for a in assets],
            format_func=lambda aid: (
                f"{aid}  ✅" if db.query(StyleAnchor).filter(StyleAnchor.asset_id == aid).first()
                else f"{aid}  ⚠️ no prompt yet"
            ),
        )

        asset = next(a for a in assets if a.asset_id == selected_asset_id)
        anchors = db.query(StyleAnchor).filter(StyleAnchor.asset_id == selected_asset_id).all()

        if anchors:
            st.subheader("Existing Anchors")
            for anchor in anchors:
                with st.expander(anchor.anchor_id + (" 🔒 locked" if anchor.is_locked else "")):
                    st.write(f"**Prompt:** {anchor.prompt_template}")
                    if anchor.seed:
                        st.write(f"**Seed:** {anchor.seed}")
                    if anchor.base_negative_prompt:
                        st.write(f"**Negative prompt:** {anchor.base_negative_prompt}")

                    if not anchor.is_locked:
                        if st.button("Delete", key=f"del_anchor_{anchor.id}"):
                            db.delete(anchor)
                            db.commit()
                            st.success("Deleted.")
                            st.rerun()
        else:
            st.info(f"No prompt yet for **{selected_asset_id}**. Create one below.")

        st.divider()
        st.subheader("➕ Create Anchor")

        with st.form(f"anchor_form_{selected_asset_id}"):
            anchor_id = st.text_input(
                "Anchor ID",
                value=f"{selected_asset_id}_v1",
                help="Unique name, e.g. creep_01_v1",
            )
            prompt = st.text_area(
                "Generation Prompt",
                placeholder=(
                    f"e.g. pixel art {asset.display_name or selected_asset_id}, "
                    "top-down view, transparent background, game asset style"
                ),
                help="This is sent directly to the image generation model.",
            )
            negative_prompt = st.text_area(
                "Negative Prompt (optional)",
                placeholder="e.g. blurry, watermark, text, low quality",
            )
            seed = st.number_input(
                "Seed (optional, 0 = random)",
                min_value=0,
                max_value=2147483647,
                value=0,
            )

            submitted = st.form_submit_button("✅ Save Anchor", type="primary")

            if submitted:
                if not anchor_id or not prompt:
                    st.error("Anchor ID and Prompt are required.")
                elif db.query(StyleAnchor).filter(StyleAnchor.anchor_id == anchor_id).first():
                    st.error(f"Anchor '{anchor_id}' already exists. Choose a different ID.")
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
                    st.success(f"✅ Anchor '{anchor_id}' saved! You can now generate images for {selected_asset_id}.")
                    st.rerun()

with tab3:
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
        )

        frame_count = 1
        if animation_type != "static":
            frame_count = st.number_input("Frame Count", min_value=2, max_value=32, value=4)

        submitted = st.form_submit_button("Create Asset")

        if submitted:
            if not asset_id or not category:
                st.error("Asset ID and Category are required.")
            elif db.query(Asset).filter(Asset.asset_id == asset_id).first():
                st.error(f"Asset '{asset_id}' already exists.")
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
                st.success(f"✅ Asset '{asset_id}' created! Now go to **Style Anchors** tab to write its prompt.")
                st.rerun()

db.close()
