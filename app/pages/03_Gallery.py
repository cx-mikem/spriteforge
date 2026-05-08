"""Gallery/Bestiary view of all approved assets."""

import streamlit as st
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Asset, Generation, Approval, Atlas, AtlasEntry
from app.services import AtlasPacker

st.set_page_config(page_title="Gallery", page_icon="🎨", layout="wide")
st.title("🎨 Gallery")
st.markdown("View and manage all approved assets organized by category.")

db = SessionLocal()

# Get all approved assets
approvals = db.query(Approval).all()
approved_asset_ids = set(a.asset_id for a in approvals)

if not approved_asset_ids:
    st.info("No approved assets yet. Go to Review to approve generations.")
else:
    assets = db.query(Asset).filter(Asset.asset_id.in_(approved_asset_ids)).all()
    categories = sorted(set(a.category for a in assets))

    # Category filter
    col1, col2 = st.columns([3, 1])
    with col1:
        show_category = st.multiselect(
            "Filter by Category",
            categories,
            default=categories,
            key="category_filter",
        )
    with col2:
        st.metric("Total Assets", len([a for a in assets if a.category in show_category]))

    st.divider()

    # Display assets by category in columns
    for category in show_category:
        cat_assets = [a for a in assets if a.category == category]
        if not cat_assets:
            continue

        st.subheader(f"📦 {category.title()}")

        # Check if atlas exists for this category
        current_atlas = (
            db.query(Atlas)
            .filter(Atlas.category == category, Atlas.is_current == True)
            .first()
        )

        if current_atlas:
            st.caption(f"Atlas v{current_atlas.version} • {current_atlas.asset_count} assets")

            # Try to show atlas preview
            try:
                st.image(current_atlas.sprite_sheet_path, use_container_width=True)
            except Exception as e:
                st.info(f"Atlas file: {current_atlas.sprite_sheet_path}")

            if st.button(f"Rebuild {category}", key=f"rebuild_{category}"):
                try:
                    with st.spinner(f"Repacking {category}..."):
                        packer = AtlasPacker(db)
                        result = packer.pack_category(category)

                        if result:
                            st.success(
                                f"✓ Atlas rebuilt: v{result['version']} with {current_atlas.asset_count} assets"
                            )
                        else:
                            st.error("Packing failed")
                except Exception as e:
                    st.error(f"Rebuild failed: {e}")

        else:
            st.caption("No atlas yet. Create one:")
            if st.button(f"Create atlas for {category}", key=f"create_{category}"):
                try:
                    with st.spinner(f"Packing {category}..."):
                        packer = AtlasPacker(db)
                        result = packer.pack_category(category)

                        if result:
                            st.success(
                                f"✓ Atlas created: v{result['version']} with {len(cat_assets)} assets"
                            )
                            st.rerun()
                        else:
                            st.error("Packing failed")
                except Exception as e:
                    st.error(f"Packing failed: {e}")

        # Display individual assets
        cols = st.columns(4)
        for idx, asset in enumerate(cat_assets):
            with cols[idx % 4]:
                approval = (
                    db.query(Approval)
                    .filter(Approval.asset_id == asset.asset_id)
                    .first()
                )
                gen = (
                    db.query(Generation).filter(Generation.id == approval.generation_id).first()
                    if approval
                    else None
                )

                with st.expander(f"📷 {asset.asset_id}"):
                    st.write(f"**Category:** {asset.category}")
                    st.write(f"**Display Name:** {asset.display_name or '-'}")
                    st.write(f"**Size:** {asset.sprite_width_px}×{asset.sprite_height_px}px")

                    if asset.animation_type != "static":
                        st.write(f"**Animation:** {asset.animation_type} ({asset.frame_count} frames)")

                    if gen and gen.image_paths:
                        st.write(f"**Generated:** {gen.created_at.strftime('%Y-%m-%d %H:%M')}")
                        try:
                            st.image(gen.image_paths[approval.chosen_image_index], use_container_width=True)
                        except Exception as e:
                            st.info("Image preview unavailable")

                    if st.button("📝 Edit", key=f"edit_{asset.id}"):
                        st.info("Edit Manifest page to modify asset properties")

        st.divider()

    # Summary
    st.subheader("Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_approved = len(approved_asset_ids)
        st.metric("Approved Assets", total_approved)
    with col2:
        total_categories = len(show_category)
        st.metric("Categories", total_categories)
    with col3:
        atlases = db.query(Atlas).filter(Atlas.is_current == True).count()
        st.metric("Current Atlases", atlases)
    with col4:
        animated = len([a for a in assets if a.animation_type != "static"])
        st.metric("Animated", animated)

db.close()
