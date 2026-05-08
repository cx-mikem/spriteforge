"""Asset generation trigger and batch management."""

import uuid
import requests
import streamlit as st
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Asset, StyleAnchor, Generation
from app.services import GenerationService
from app.config import Config

st.set_page_config(page_title="Generate", page_icon="✨")
st.title("✨ Generate")
st.markdown("Create new images from style anchors.")

db = SessionLocal()

tab1, tab2, tab3 = st.tabs(["Trigger", "Pending", "Cost Summary"])

# Local directory for downloaded generation images
GENERATIONS_DIR = Path(Config.STORAGE_LOCAL_PATH) / "generations"
GENERATIONS_DIR.mkdir(parents=True, exist_ok=True)


def download_image(url: str, dest: Path) -> str:
    """Download image URL to disk and return local path string."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return str(dest)


with tab1:
    st.header("Trigger Generation")

    # Check prerequisites
    all_assets = db.query(Asset).filter(Asset.deleted_at == None).all()
    if not all_assets:
        st.warning("No assets defined yet — go to **Manifest** to create some first.")
        db.close()
        st.stop()

    anchored_ids = {
        r[0]
        for r in db.query(StyleAnchor.asset_id).distinct().all()
    }
    missing_anchors = [a for a in all_assets if a.asset_id not in anchored_ids]
    if missing_anchors:
        st.info(
            f"{len(missing_anchors)} asset(s) have no style anchor yet: "
            + ", ".join(a.asset_id for a in missing_anchors)
            + " — add prompts in **Settings → Style Anchors**."
        )

    col1, col2 = st.columns(2)

    with col1:
        scope = st.radio(
            "Generation Scope",
            [
                ("Single Asset", "single"),
                ("Category", "category"),
                ("Missing Only", "missing"),
                ("All Assets", "all"),
            ],
            format_func=lambda x: x[0],
        )
        scope = scope[1]

    with col2:
        variants = st.number_input(
            "Variants per Asset",
            min_value=1,
            max_value=5,
            value=1,
            help="Generate N candidates per asset",
        )

    assets = all_assets

    if scope == "single":
        selected_asset = st.selectbox(
            "Select Asset",
            assets,
            format_func=lambda a: f"{a.asset_id} ({a.category})",
        )
        target_assets = [selected_asset]

    elif scope == "category":
        categories = sorted(set(a.category for a in assets))
        selected_category = st.selectbox("Select Category", categories)
        target_assets = [a for a in assets if a.category == selected_category]

    elif scope == "missing":
        target_assets = []
        for asset in assets:
            approved = db.query(Generation).filter(
                Generation.asset_id == asset.asset_id,
                Generation.status == "approved",
            ).first()
            if not approved:
                target_assets.append(asset)
        st.info(f"Found {len(target_assets)} assets needing generation")

    else:  # all
        target_assets = assets
        st.info(f"Will regenerate all {len(target_assets)} assets")

    if target_assets:
        estimated_cost = len(target_assets) * variants * 0.04
        st.metric("Estimated Cost", f"${estimated_cost:.2f}")

        if st.button("🚀 Generate", use_container_width=True, type="primary"):
            st.info(f"Generating {len(target_assets)} assets × {variants} variants...")

            progress_bar = st.progress(0)
            status_container = st.empty()
            results = []

            try:
                service = GenerationService()

                for idx, asset in enumerate(target_assets):
                    anchor = (
                        db.query(StyleAnchor)
                        .filter(StyleAnchor.asset_id == asset.asset_id)
                        .first()
                    )

                    if not anchor:
                        status_container.warning(
                            f"⚠️ {asset.asset_id}: No style anchor — add one in Settings."
                        )
                        results.append({"asset_id": asset.asset_id, "status": "⚠️ no anchor"})
                        continue

                    try:
                        status_container.info(f"🔄 Generating {asset.asset_id}...")

                        result = service.generate(
                            prompt=anchor.prompt_template,
                            negative_prompt=anchor.base_negative_prompt,
                            seed=anchor.seed,
                            num_variants=variants,
                        )

                        # Download images to local disk so URLs don't expire
                        batch_id = uuid.uuid4().hex[:8]
                        local_paths = []
                        for i, img in enumerate(result["images"]):
                            fname = GENERATIONS_DIR / asset.asset_id / f"{batch_id}_{i}.png"
                            try:
                                local_path = download_image(img["url"], fname)
                                local_paths.append(local_path)
                            except Exception as dl_err:
                                # Fall back to URL if download fails
                                local_paths.append(img["url"])
                                status_container.warning(f"Could not download image {i}: {dl_err}")

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

                        results.append(
                            {
                                "asset_id": asset.asset_id,
                                "status": "✓",
                                "cost": float(result["cost_usd"]),
                            }
                        )

                        progress_bar.progress(
                            (idx + 1) / len(target_assets),
                            text=f"{idx + 1}/{len(target_assets)}",
                        )

                    except Exception as e:
                        results.append(
                            {"asset_id": asset.asset_id, "status": "✗", "error": str(e)}
                        )
                        status_container.error(f"Failed {asset.asset_id}: {e}")

                total_cost = sum(r.get("cost", 0) for r in results)
                success_count = sum(1 for r in results if r["status"] == "✓")

                st.success(
                    f"Generated {success_count}/{len(target_assets)} assets. "
                    f"Total cost: ${total_cost:.2f}. "
                    "→ Go to **Review** to approve them."
                )

                if results:
                    st.dataframe(results, use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"Generation failed: {e}")

with tab2:
    st.header("Pending Generations")

    pending = db.query(Generation).filter(Generation.status == "pending").all()

    if not pending:
        st.info("No pending generations. Go to Review to check approved ones.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Pending", len(pending))
        with col2:
            total_cost = sum(g.api_cost_usd for g in pending if g.api_cost_usd)
            st.metric("Cost", f"${float(total_cost):.2f}")
        with col3:
            by_asset = len(set(g.asset_id for g in pending))
            st.metric("Unique Assets", by_asset)

        st.divider()

        for gen in pending[-10:]:
            with st.expander(
                f"{gen.asset_id} • {gen.created_at.strftime('%H:%M:%S')} • "
                f"{len(gen.image_paths or [])} images • ${float(gen.api_cost_usd or 0):.4f}"
            ):
                st.write(f"**Prompt:** {gen.prompt_used}")
                st.write(f"**Model:** {gen.model}")
                if gen.last_error:
                    st.error(f"Error: {gen.last_error}")
                else:
                    st.info(f"Images saved: {len(gen.image_paths or [])}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Review", key=f"review_{gen.id}"):
                        st.info("Go to Review tab to approve/reject")
                with col2:
                    if st.button("Delete", key=f"delete_{gen.id}"):
                        db.delete(gen)
                        db.commit()
                        st.rerun()

with tab3:
    st.header("Cost Summary")

    all_gens = db.query(Generation).all()

    if not all_gens:
        st.info("No generations yet.")
    else:
        total_cost = sum(g.api_cost_usd for g in all_gens if g.api_cost_usd)
        st.metric("Total Spend", f"${float(total_cost):.2f}")

        st.divider()

        by_asset = {}
        for gen in all_gens:
            if gen.api_cost_usd:
                asset_id = gen.asset_id
                by_asset[asset_id] = by_asset.get(asset_id, 0) + float(gen.api_cost_usd)

        if by_asset:
            st.subheader("Cost by Asset")
            for asset_id, cost in sorted(by_asset.items(), key=lambda x: x[1], reverse=True):
                st.write(f"**{asset_id}**: ${cost:.2f}")

        st.subheader("Cost by Status")
        by_status = {}
        for gen in all_gens:
            if gen.api_cost_usd:
                status = gen.status
                by_status[status] = by_status.get(status, 0) + float(gen.api_cost_usd)

        for status, cost in by_status.items():
            st.write(f"**{status}**: ${cost:.2f}")

db.close()
