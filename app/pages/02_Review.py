"""Review and approve generated assets."""

import streamlit as st
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Asset, Generation, Approval, ProcessedAsset
from app.services import PostProcessService
from app.config import Config

st.set_page_config(page_title="Review", page_icon="👁️", layout="wide")
st.title("👁️ Review & Approve")
st.markdown("Approve generations before they become production assets.")

db = SessionLocal()

tab1, tab2 = st.tabs(["Pending Review", "Approval History"])

with tab1:
    st.header("Pending Generations")

    pending = (
        db.query(Generation)
        .filter(Generation.status == "pending")
        .order_by(Generation.created_at.desc())
        .all()
    )

    if not pending:
        st.info("✓ All caught up! No pending generations to review.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Waiting Review", len(pending))

        selected_gen_id = st.selectbox(
            "Select Generation",
            pending,
            format_func=lambda g: f"{g.asset_id} • {len(g.image_paths)} images • {g.created_at.strftime('%H:%M')}",
        )

        selected_gen = selected_gen_id

        if selected_gen:
            asset = (
                db.query(Asset).filter(Asset.asset_id == selected_gen.asset_id).first()
            )

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"**Asset:** {asset.asset_id}")
            with col2:
                st.write(f"**Category:** {asset.category}")
            with col3:
                st.write(f"**Sprites:** {selected_gen.image_count}")
            with col4:
                st.write(f"**Cost:** ${float(selected_gen.api_cost_usd):.4f}")

            st.divider()

            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("Candidate Images")
                for idx, image_url in enumerate(selected_gen.image_paths):
                    st.write(f"**Variant {idx + 1}**")
                    try:
                        st.image(image_url, use_container_width=True, caption=image_url[:40] + "...")
                    except Exception as e:
                        st.error(f"Could not load image: {e}")

            with col2:
                st.subheader("Actions")

                st.write("**Choose action:**")

                # Check if previous approved version exists
                prev_approved = (
                    db.query(Generation)
                    .filter(
                        Generation.asset_id == selected_gen.asset_id,
                        Generation.status == "approved",
                        Generation.id != selected_gen.id,
                    )
                    .order_by(Generation.created_at.desc())
                    .first()
                )

                if prev_approved:
                    st.info(f"Previous approved: {prev_approved.created_at.strftime('%Y-%m-%d %H:%M')}")

                # Approval decision
                action = st.radio(
                    "Decision",
                    [
                        ("✓ Approve", "approve"),
                        ("✗ Reject", "reject"),
                        ("🔄 Regenerate", "regenerate"),
                    ],
                    format_func=lambda x: x[0],
                )
                action = action[1]

                notes = st.text_area("Notes (optional)", placeholder="Why did you approve/reject?")

                if action == "approve":
                    variant_idx = st.number_input(
                        "Which variant?",
                        min_value=0,
                        max_value=len(selected_gen.image_paths) - 1,
                        value=0,
                    )

                    if st.button("✓ Approve", type="primary", use_container_width=True):
                        try:
                            # Create approval
                            approval = Approval(
                                generation_id=selected_gen.id,
                                asset_id=selected_gen.asset_id,
                                approved_by="user",
                                chosen_image_index=variant_idx,
                                notes=notes if notes else None,
                            )
                            db.add(approval)

                            # Mark generation as approved
                            selected_gen.status = "approved"
                            selected_gen.approved_at = datetime.utcnow()
                            selected_gen.approved_by = "user"

                            db.commit()

                            st.success(
                                f"✓ Approved! Image will be processed in next step."
                            )
                            st.balloons()

                            # Offer to process immediately
                            if st.button("Process Now"):
                                try:
                                    service = PostProcessService()
                                    image_url = selected_gen.image_paths[variant_idx]

                                    with st.spinner("Processing image..."):
                                        result = service.process(
                                            image_url=image_url,
                                            sprite_width=asset.sprite_width_px,
                                            sprite_height=asset.sprite_height_px,
                                            output_path=st.session_state.get(
                                                "temp_dir", "/tmp"
                                            ),
                                        )

                                        processed = ProcessedAsset(
                                            generation_id=selected_gen.id,
                                            asset_id=selected_gen.asset_id,
                                            processed_image_path=result[
                                                "processed_image_path"
                                            ],
                                            bounding_box_x=result["bounding_box"]["x"],
                                            bounding_box_y=result["bounding_box"]["y"],
                                            bounding_box_width=result["bounding_box"][
                                                "width"
                                            ],
                                            bounding_box_height=result["bounding_box"][
                                                "height"
                                            ],
                                        )
                                        db.add(processed)
                                        db.commit()

                                        st.success(
                                            "✓ Processed! Ready for atlas packing."
                                        )

                                except Exception as e:
                                    st.error(f"Processing failed: {e}")

                        except Exception as e:
                            st.error(f"Approval failed: {e}")

                elif action == "reject":
                    reject_reason = st.text_input(
                        "Reason for rejection", placeholder="Quality issues, wrong style, etc."
                    )

                    if st.button("✗ Reject", type="secondary", use_container_width=True):
                        try:
                            selected_gen.status = "rejected"
                            selected_gen.rejected_at = datetime.utcnow()
                            selected_gen.rejected_by = "user"
                            selected_gen.last_error = reject_reason or notes
                            db.commit()

                            st.warning("✗ Rejected. This generation will not be used.")
                            st.rerun()

                        except Exception as e:
                            st.error(f"Rejection failed: {e}")

                else:  # regenerate
                    new_seed = st.number_input(
                        "New seed (for variation)",
                        min_value=0,
                        max_value=2147483647,
                        value=None,
                    )

                    if st.button("🔄 Regenerate", use_container_width=True):
                        st.info(
                            "Mark as rejected and regenerate with new seed from Generate tab"
                        )
                        selected_gen.status = "rejected"
                        selected_gen.rejected_at = datetime.utcnow()
                        selected_gen.rejected_by = "user"
                        selected_gen.last_error = f"Regenerate with seed {new_seed}"
                        db.commit()
                        st.warning("✓ Marked for regeneration. Go to Generate tab.")
                        st.rerun()

with tab2:
    st.header("Approval History")

    approvals = (
        db.query(Approval)
        .order_by(Approval.approved_at.desc())
        .limit(20)
        .all()
    )

    if not approvals:
        st.info("No approvals yet.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Approved", len(approvals))
        with col2:
            st.metric("Ready for Export", len(set(a.asset_id for a in approvals)))

        st.divider()

        for approval in approvals:
            asset = (
                db.query(Asset).filter(Asset.asset_id == approval.asset_id).first()
            )
            gen = db.query(Generation).filter(Generation.id == approval.generation_id).first()

            with st.expander(
                f"{approval.asset_id} • {approval.approved_at.strftime('%Y-%m-%d %H:%M')} • "
                f"${float(gen.api_cost_usd):.4f}"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Category:** {asset.category}")
                    st.write(f"**Variant:** {approval.chosen_image_index + 1}/{gen.image_count}")
                with col2:
                    st.write(f"**Approved by:** {approval.approved_by}")
                    if approval.notes:
                        st.write(f"**Notes:** {approval.notes}")

db.close()
