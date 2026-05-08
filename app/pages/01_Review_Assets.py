"""Review and approve generated assets."""

import streamlit as st
from datetime import datetime
from pathlib import Path
from PIL import Image as PILImage
from app.database import SessionLocal
from app.models import Asset, Generation, Approval, ProcessedAsset
from app.services import PostProcessService
from app.config import Config

st.set_page_config(page_title="Review Assets", page_icon="👁️", layout="wide")
st.title("👁️ Review Assets")
st.markdown("Approve the best image for each asset before it moves to export.")

db = SessionLocal()


def load_thumbnail(path_or_url: str, size: int = 200):
    """Return a PIL image — local file or URL, first frame only."""
    try:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            import requests
            from io import BytesIO
            resp = requests.get(path_or_url, timeout=15)
            resp.raise_for_status()
            img = PILImage.open(BytesIO(resp.content)).convert("RGBA")
        else:
            p = Path(path_or_url)
            if not p.exists():
                return None
            img = PILImage.open(p).convert("RGBA")
        img.thumbnail((size, size), PILImage.Resampling.LANCZOS)
        return img
    except Exception:
        return None


tab_pending, tab_approved = st.tabs(["Pending Review", "Approved"])

with tab_pending:
    pending = (
        db.query(Generation)
        .filter(Generation.status == "pending")
        .order_by(Generation.created_at.desc())
        .all()
    )

    if not pending:
        total = db.query(Generation).count()
        if total == 0:
            st.info(
                "Nothing to review yet.\n\n"
                "1. Go to **Create** — fill in asset details + prompt, click 🚀 Create & Generate\n"
                "2. Come back here to approve the results"
            )
        else:
            st.success("✓ All caught up — no pending generations.")
    else:
        st.caption(f"{len(pending)} generation(s) waiting for review")
        st.divider()

        # Thumbnail grid
        cols_per_row = 3
        for row_start in range(0, len(pending), cols_per_row):
            row_gens = pending[row_start: row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, gen in zip(cols, row_gens):
                asset = db.query(Asset).filter(Asset.asset_id == gen.asset_id).first()
                image_paths = gen.image_paths or []

                with col:
                    # Show only the first image as the representative thumbnail
                    if image_paths:
                        thumb = load_thumbnail(image_paths[0])
                        if thumb:
                            st.image(thumb, use_container_width=True)
                        else:
                            st.caption("⚠️ Image not found")
                    else:
                        st.caption("No images saved")

                    label = (asset.display_name or gen.asset_id) if asset else gen.asset_id
                    anim = asset.animation_type if asset else "static"
                    st.markdown(f"**{label}**")
                    st.caption(
                        f"{anim} · {len(image_paths)} variant(s) · "
                        f"${float(gen.api_cost_usd or 0):.2f} · "
                        f"{gen.created_at.strftime('%b %d %H:%M')}"
                    )

                    if st.button("Review →", key=f"open_{gen.id}", use_container_width=True):
                        st.session_state["reviewing_id"] = gen.id

        # Detail panel for selected generation
        reviewing_id = st.session_state.get("reviewing_id")
        if reviewing_id:
            gen = db.query(Generation).filter(Generation.id == reviewing_id).first()
            if gen and gen.status == "pending":
                asset = db.query(Asset).filter(Asset.asset_id == gen.asset_id).first()
                image_paths = gen.image_paths or []
                is_animated = asset and asset.animation_type != "static"

                st.divider()
                st.subheader(f"Reviewing: {(asset.display_name or gen.asset_id) if asset else gen.asset_id}")

                col_imgs, col_actions = st.columns([3, 1])

                with col_imgs:
                    if not image_paths:
                        st.warning("No images available.")
                    elif is_animated:
                        # Animations: show just the first frame as representative
                        st.caption(f"Animation asset ({asset.animation_type}) — showing representative frame")
                        thumb = load_thumbnail(image_paths[0], size=400)
                        if thumb:
                            st.image(thumb, use_container_width=True,
                                     caption=f"{asset.animation_type} · {asset.frame_count} frames")
                        if len(image_paths) > 1:
                            with st.expander(f"See all {len(image_paths)} variants"):
                                vcols = st.columns(min(len(image_paths), 4))
                                for i, path in enumerate(image_paths):
                                    with vcols[i % 4]:
                                        t = load_thumbnail(path, size=150)
                                        if t:
                                            st.image(t, caption=f"Variant {i+1}", use_container_width=True)
                    else:
                        # Static: show all variants side by side
                        vcols = st.columns(min(len(image_paths), 4))
                        for i, path in enumerate(image_paths):
                            with vcols[i % 4]:
                                t = load_thumbnail(path, size=300)
                                if t:
                                    st.image(t, caption=f"Variant {i+1}", use_container_width=True)
                                else:
                                    st.caption(f"Variant {i+1} — not found")

                with col_actions:
                    st.subheader("Decision")

                    action = st.radio(
                        "Action",
                        [("✅ Approve", "approve"), ("✗ Reject", "reject")],
                        format_func=lambda x: x[0],
                        key=f"action_{reviewing_id}",
                    )
                    action = action[1]

                    variant_idx = 0
                    if action == "approve" and len(image_paths) > 1:
                        variant_idx = st.number_input(
                            "Which variant?",
                            min_value=1,
                            max_value=len(image_paths),
                            value=1,
                            key=f"var_{reviewing_id}",
                        ) - 1

                    notes = st.text_area("Notes (optional)", key=f"notes_{reviewing_id}")

                    col_a, col_b = st.columns(2)

                    with col_a:
                        if action == "approve" and st.button("✅ Approve", type="primary", use_container_width=True):
                            try:
                                approval = Approval(
                                    generation_id=gen.id,
                                    asset_id=gen.asset_id,
                                    approved_by="user",
                                    chosen_image_index=variant_idx,
                                    notes=notes or None,
                                )
                                db.add(approval)
                                gen.status = "approved"
                                gen.approved_at = datetime.utcnow()
                                gen.approved_by = "user"
                                db.commit()
                                st.success("✅ Approved!")
                                st.session_state.pop("reviewing_id", None)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")

                    with col_b:
                        if action == "reject" and st.button("✗ Reject", use_container_width=True):
                            try:
                                gen.status = "rejected"
                                gen.rejected_at = datetime.utcnow()
                                gen.rejected_by = "user"
                                gen.last_error = notes or "Rejected"
                                db.commit()
                                st.warning("Rejected. Regenerate from Create.")
                                st.session_state.pop("reviewing_id", None)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")

                    if st.button("← Back to list", use_container_width=True):
                        st.session_state.pop("reviewing_id", None)
                        st.rerun()

with tab_approved:
    approvals = (
        db.query(Approval)
        .order_by(Approval.approved_at.desc())
        .all()
    )

    if not approvals:
        st.info("No approved assets yet.")
    else:
        st.metric("Approved Assets", len(approvals))
        st.divider()

        cols_per_row = 4
        for row_start in range(0, len(approvals), cols_per_row):
            row = approvals[row_start: row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, approval in zip(cols, row):
                gen = db.query(Generation).filter(Generation.id == approval.generation_id).first()
                asset = db.query(Asset).filter(Asset.asset_id == approval.asset_id).first()
                image_paths = (gen.image_paths or []) if gen else []
                chosen = approval.chosen_image_index or 0

                with col:
                    if image_paths and chosen < len(image_paths):
                        thumb = load_thumbnail(image_paths[chosen])
                        if thumb:
                            st.image(thumb, use_container_width=True)
                    label = (asset.display_name or approval.asset_id) if asset else approval.asset_id
                    st.caption(f"**{label}**  \n{approval.approved_at.strftime('%b %d')}")

db.close()
