"""Export engine-ready asset bundles."""

import streamlit as st
import json
from io import BytesIO
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Atlas, AtlasEntry, Asset
from app.storage import get_storage_backend

st.set_page_config(page_title="Export", page_icon="📦")
st.title("📦 Export")
st.markdown("Download game-ready asset bundles.")

db = SessionLocal()

tab1, tab2 = st.tabs(["Export Bundles", "Atlas History"])

with tab1:
    st.header("Create Bundle")

    # Get current atlases
    current_atlases = db.query(Atlas).filter(Atlas.is_current == True).all()

    if not current_atlases:
        st.warning("No atlases created yet. Go to Gallery to create them.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Ready to Export", len(current_atlases))

        with col2:
            total_assets = sum(a.asset_count for a in current_atlases)
            st.metric("Total Assets", total_assets)

        st.divider()

        # Bundle format selection
        export_format = st.radio(
            "Export Format",
            [
                ("Phaser 3 (JSON + PNG)", "phaser"),
                ("Raw Assets (PNG only)", "png"),
                ("Full Bundle (all files)", "bundle"),
            ],
            format_func=lambda x: x[0],
        )
        export_format = export_format[1]

        st.divider()

        # Select categories to include
        categories = sorted(set(a.category for a in current_atlases))
        selected_categories = st.multiselect(
            "Categories to Include",
            categories,
            default=categories,
        )

        # Filter atlases
        export_atlases = [
            a for a in current_atlases if a.category in selected_categories
        ]

        if not export_atlases:
            st.warning("No atlases selected.")
        else:
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("Bundle Contents")
                for atlas in export_atlases:
                    st.write(
                        f"📦 **{atlas.category}** (v{atlas.version}) • "
                        f"{atlas.asset_count} assets • "
                        f"{atlas.atlas_width_px}×{atlas.atlas_height_px}px"
                    )

            with col2:
                st.subheader("Download")

                # Create download bundle
                bundle_data = {
                    "version": "1.0",
                    "format": "spriteforge-phaser",
                    "exported_at": st._get_script_run_ctx().script_path if False else "now",
                    "atlases": [],
                }

                try:
                    for atlas in export_atlases:
                        atlas_info = {
                            "category": atlas.category,
                            "version": atlas.version,
                            "sprite_sheet": atlas.sprite_sheet_path,
                            "manifest": atlas.manifest_json_path,
                            "size": {
                                "width": atlas.atlas_width_px,
                                "height": atlas.atlas_height_px,
                            },
                            "assets": [],
                        }

                        entries = (
                            db.query(AtlasEntry)
                            .filter(AtlasEntry.atlas_id == atlas.id)
                            .all()
                        )
                        for entry in entries:
                            atlas_info["assets"].append(
                                {
                                    "asset_id": entry.asset_id,
                                    "x": entry.x,
                                    "y": entry.y,
                                    "width": entry.width,
                                    "height": entry.height,
                                    "frame_count": entry.frame_count,
                                }
                            )

                        bundle_data["atlases"].append(atlas_info)

                    if export_format == "phaser":
                        # Export Phaser JSON
                        json_bytes = json.dumps(bundle_data, indent=2).encode()
                        st.download_button(
                            label="📥 Download JSON Manifest",
                            data=json_bytes,
                            file_name="spriteforge-manifest.json",
                            mime="application/json",
                        )

                    elif export_format == "png":
                        # Export PNG files only (placeholder)
                        st.info(
                            "PNG export requires downloading individual sprite sheets. "
                            "Use JSON manifest above with the Phaser loader."
                        )

                    elif export_format == "bundle":
                        # Full bundle
                        st.info(
                            "Full bundle export includes JSON + all sprite sheets. "
                            "Use the manifest file and download sprite sheets from storage."
                        )
                        json_bytes = json.dumps(bundle_data, indent=2).encode()
                        st.download_button(
                            label="📥 Download Bundle JSON",
                            data=json_bytes,
                            file_name="spriteforge-bundle.json",
                            mime="application/json",
                        )

                        st.write("**Sprite Sheet URLs:**")
                        for atlas in export_atlases:
                            st.code(f"assets/{atlas.category}/{atlas.version}.png")

                except Exception as e:
                    st.error(f"Export failed: {e}")

        st.divider()

        # Copy-paste snippet
        st.subheader("Integration Code")

        phaser_code = """
// Phaser 3 example
const scene = new Phaser.Scene('MyScene');

scene.preload = function() {
  // Load texture from URL or local file
  this.load.setPath('assets/');
  this.load.atlas('sprites', 'spritesheet.png', 'manifest.json');
};

scene.create = function() {
  // Add sprite from loaded atlas
  this.add.sprite(100, 100, 'sprites', 'asset_id_001');
};
"""

        if st.toggle("Show Phaser 3 Integration Code"):
            st.code(phaser_code, language="javascript")

with tab2:
    st.header("Atlas History")

    all_atlases = db.query(Atlas).order_by(Atlas.created_at.desc()).all()

    if not all_atlases:
        st.info("No atlases created yet.")
    else:
        by_category = {}
        for atlas in all_atlases:
            if atlas.category not in by_category:
                by_category[atlas.category] = []
            by_category[atlas.category].append(atlas)

        for category in sorted(by_category.keys()):
            atlases = by_category[category]
            st.subheader(f"📦 {category.title()}")

            for atlas in atlases:
                status = "✓ Current" if atlas.is_current else "📦 Archive"
                with st.expander(
                    f"v{atlas.version} • {status} • {atlas.created_at.strftime('%Y-%m-%d %H:%M')} • "
                    f"{atlas.asset_count} assets"
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Size:** {atlas.atlas_width_px}×{atlas.atlas_height_px}px")
                        st.write(f"**Path:** `{atlas.sprite_sheet_path}`")
                    with col2:
                        st.write(f"**Manifest:** `{atlas.manifest_json_path}`")

                    if not atlas.is_current:
                        if st.button(
                            "↩️ Restore", key=f"restore_{atlas.id}"
                        ):
                            # Mark others as not current
                            db.query(Atlas).filter(
                                Atlas.category == atlas.category,
                                Atlas.id != atlas.id,
                            ).update({"is_current": False})

                            # Mark this as current
                            atlas.is_current = True
                            db.commit()

                            st.success(f"✓ Restored v{atlas.version}")
                            st.rerun()

db.close()
