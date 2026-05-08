"""Create assets and generate images in one flow."""

import uuid
import requests
import streamlit as st
from datetime import datetime
from pathlib import Path
from app.database import SessionLocal
from app.models import Asset, StyleAnchor, Generation
from app.services import GenerationService
from app.config import Config

st.set_page_config(page_title="Create", page_icon="📋")
st.title("📋 Create")
st.markdown("Define an asset, write its prompt, and generate images — all in one step.")

db = SessionLocal()

GENERATIONS_DIR = Path(Config.STORAGE_LOCAL_PATH) / "generations"
GENERATIONS_DIR.mkdir(parents=True, exist_ok=True)


def download_image(url: str, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return str(dest)


tab_create, tab_assets = st.tabs(["Create Asset", "All Assets"])

with tab_create:
    # Animation type lives OUTSIDE the form so changing it rerenders the page
    # and shows/hides the frame count input reactively.
    st.subheader("Asset Details")
    col1, col2 = st.columns(2)
    with col2:
        animation_type = st.selectbox("Animation Type", ["static", "loop", "transition"])
        frame_count = 1
        if animation_type != "static":
            frame_count = st.number_input(
                "Frame Count",
                min_value=2,
                max_value=32,
                value=4,
                help="How many animation frames to request from the API",
            )

    with st.form("create_asset_form"):
        col1, col2 = st.columns(2)
        with col1:
            asset_id = st.text_input("Asset ID", placeholder="e.g. creep_01", help="Unique identifier")
            category = st.text_input("Category", placeholder="e.g. creep", help="Used to group assets into sprite sheets")
            display_name = st.text_input("Display Name", placeholder="e.g. Basic Creep")
        with col2:
            sprite_width = st.number_input("Sprite Width (px)", min_value=16, max_value=512, value=64)
            sprite_height = st.number_input("Sprite Height (px)", min_value=16, max_value=512, value=64)
            st.caption(f"Animation: **{animation_type}**" + (f" · {frame_count} frames" if animation_type != "static" else ""))

        st.divider()
        st.subheader("Generation Prompt")

        prompt = st.text_area(
            "Prompt",
            placeholder="e.g. pixel art energy core building, top-down view, glowing blue, transparent background, game asset style",
            help="Sent directly to the image generation model.",
        )
        negative_prompt = st.text_area(
            "Negative Prompt (optional)",
            placeholder="e.g. blurry, watermark, text, low quality",
        )

        col1, col2 = st.columns(2)
        with col1:
            variants = st.number_input("Variants to generate", min_value=1, max_value=5, value=1)
        with col2:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            estimated_cost = variants * 0.04
            st.caption(f"Estimated cost: ${estimated_cost:.2f}")

        submitted = st.form_submit_button("🚀 Create & Generate", type="primary", use_container_width=True)

    if submitted:
        errors = []
        if not asset_id:
            errors.append("Asset ID is required.")
        if not category:
            errors.append("Category is required.")
        if not prompt:
            errors.append("A generation prompt is required.")
        if asset_id and db.query(Asset).filter(Asset.asset_id == asset_id).first():
            errors.append(f"Asset '{asset_id}' already exists.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            # 1. Save asset
            asset = Asset(
                asset_id=asset_id,
                category=category,
                display_name=display_name,
                sprite_width_px=sprite_width,
                sprite_height_px=sprite_height,
                animation_type=animation_type,
                frame_count=frame_count,
            )
            db.add(asset)
            db.flush()

            # 2. Save style anchor
            anchor_id = f"{asset_id}_v1"
            anchor = StyleAnchor(
                anchor_id=anchor_id,
                asset_id=asset_id,
                prompt_template=prompt,
                base_negative_prompt=negative_prompt if negative_prompt else None,
            )
            db.add(anchor)
            db.flush()

            db.commit()
            st.success(f"✅ Asset **{asset_id}** created. Generating {variants} image(s)…")

            # 3. Generate
            try:
                service = GenerationService()
                with st.spinner("Calling image generation API…"):
                    result = service.generate(
                        prompt=prompt,
                        negative_prompt=negative_prompt if negative_prompt else None,
                        num_variants=variants,
                    )

                # Download images to disk
                batch_id = uuid.uuid4().hex[:8]
                local_paths = []
                for i, img in enumerate(result["images"]):
                    fname = GENERATIONS_DIR / asset_id / f"{batch_id}_{i}.png"
                    try:
                        local_paths.append(download_image(img["url"], fname))
                    except Exception:
                        local_paths.append(img["url"])

                gen = Generation(
                    asset_id=asset_id,
                    anchor_id=anchor_id,
                    status="pending",
                    image_paths=local_paths,
                    image_count=len(local_paths),
                    prompt_used=prompt,
                    model=result["model"],
                    api_cost_usd=result["cost_usd"],
                )
                db.add(gen)
                db.commit()

                st.success(
                    f"✅ {len(local_paths)} image(s) generated (cost: ${float(result['cost_usd']):.2f}). "
                    "→ Go to **Review** to approve them."
                )

                # Preview the generated images inline
                cols = st.columns(len(local_paths))
                for i, path in enumerate(local_paths):
                    with cols[i]:
                        p = Path(path)
                        if p.exists():
                            from PIL import Image as PILImage
                            st.image(PILImage.open(p), caption=f"Variant {i+1}", use_container_width=True)
                        elif path.startswith("http"):
                            st.image(path, caption=f"Variant {i+1}", use_container_width=True)

            except Exception as e:
                st.error(f"Generation failed: {e}")
                st.info("Asset and prompt were saved. You can retry generation later.")

with tab_assets:
    st.subheader("All Assets")

    assets = db.query(Asset).filter(Asset.deleted_at == None).all()

    if not assets:
        st.info("No assets yet. Use the Create Asset tab to add one.")
    else:
        anchored = {r[0] for r in db.query(StyleAnchor.asset_id).distinct().all()}

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total", len(assets))
        with col2:
            st.metric("Categories", len(set(a.category for a in assets)))
        with col3:
            st.metric("Ready to generate", len(anchored))

        st.divider()

        for asset in assets:
            has_anchor = asset.asset_id in anchored
            pending_count = db.query(Generation).filter(
                Generation.asset_id == asset.asset_id,
                Generation.status == "pending",
            ).count()
            approved_count = db.query(Generation).filter(
                Generation.asset_id == asset.asset_id,
                Generation.status == "approved",
            ).count()

            with st.expander(
                f"{'✅' if has_anchor else '⚠️'} **{asset.asset_id}** — {asset.category} "
                f"| {asset.sprite_width_px}×{asset.sprite_height_px}px "
                f"| pending: {pending_count} | approved: {approved_count}"
            ):
                col1, col2 = st.columns([3, 1])
                with col1:
                    if not has_anchor:
                        new_prompt = st.text_area(
                            "Add a prompt to enable generation",
                            key=f"prompt_{asset.asset_id}",
                        )
                        if st.button("Save Prompt", key=f"save_{asset.asset_id}"):
                            if new_prompt:
                                anchor = StyleAnchor(
                                    anchor_id=f"{asset.asset_id}_v1",
                                    asset_id=asset.asset_id,
                                    prompt_template=new_prompt,
                                )
                                db.add(anchor)
                                db.commit()
                                st.success("Prompt saved.")
                                st.rerun()
                    else:
                        anchor = db.query(StyleAnchor).filter(
                            StyleAnchor.asset_id == asset.asset_id
                        ).first()
                        st.caption(f"**Prompt:** {anchor.prompt_template}")
                with col2:
                    if has_anchor:
                        n = st.number_input("Variants", min_value=1, max_value=5, value=1, key=f"var_{asset.asset_id}")
                        if st.button("🚀 Generate", key=f"gen_{asset.asset_id}", use_container_width=True):
                            try:
                                anchor = db.query(StyleAnchor).filter(
                                    StyleAnchor.asset_id == asset.asset_id
                                ).first()
                                service = GenerationService()
                                with st.spinner("Generating…"):
                                    result = service.generate(
                                        prompt=anchor.prompt_template,
                                        negative_prompt=anchor.base_negative_prompt,
                                        num_variants=n,
                                    )
                                batch_id = uuid.uuid4().hex[:8]
                                local_paths = []
                                for i, img in enumerate(result["images"]):
                                    fname = GENERATIONS_DIR / asset.asset_id / f"{batch_id}_{i}.png"
                                    try:
                                        local_paths.append(download_image(img["url"], fname))
                                    except Exception:
                                        local_paths.append(img["url"])

                                gen = Generation(
                                    asset_id=asset.asset_id,
                                    anchor_id=anchor.anchor_id,
                                    status="pending",
                                    image_paths=local_paths,
                                    image_count=len(local_paths),
                                    prompt_used=anchor.prompt_template,
                                    model=result["model"],
                                    api_cost_usd=result["cost_usd"],
                                )
                                db.add(gen)
                                db.commit()
                                st.success(f"Generated {len(local_paths)} image(s). → Review to approve.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")

db.close()
