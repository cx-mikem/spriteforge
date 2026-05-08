"""Generation, Approval, and ProcessedAsset models."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, DECIMAL, JSON, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Generation(Base):
    __tablename__ = "generations"

    id = Column(Integer, primary_key=True)
    batch_id = Column(String(255), nullable=True)
    asset_id = Column(String(255), ForeignKey("assets.asset_id"), nullable=False)
    anchor_id = Column(String(255), ForeignKey("style_anchors.anchor_id"), nullable=True)

    status = Column(String(50), default="pending")  # pending, approved, rejected, processing
    image_paths = Column(JSON, default=list)  # ["path/to/img_1.png", ...]
    image_count = Column(Integer, default=1)

    prompt_used = Column(Text, nullable=True)
    model = Column(String(100), nullable=True)
    api_cost_usd = Column(DECIMAL(10, 4), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(255), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejected_by = Column(String(255), nullable=True)

    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)

    # Relationships
    asset = relationship("Asset", back_populates="generations")
    anchor = relationship("StyleAnchor", back_populates="generations")
    approval = relationship("Approval", uselist=False, back_populates="generation")
    processed_asset = relationship("ProcessedAsset", uselist=False, back_populates="generation")
    costs = relationship("GenerationCost", back_populates="generation")

    __table_args__ = (
        Index("idx_generation_asset_status", "asset_id", "status"),
        Index("idx_generation_batch", "batch_id"),
        Index("idx_generation_created", "created_at"),
    )

    def __repr__(self):
        return f"<Generation {self.id} {self.status}>"


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), unique=True, nullable=False)
    asset_id = Column(String(255), ForeignKey("assets.asset_id"), nullable=False)
    approved_by = Column(String(255), nullable=False)
    approved_at = Column(DateTime, default=datetime.utcnow)

    chosen_image_index = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    playback_fps = Column(Integer, nullable=True)

    # Relationships
    generation = relationship("Generation", back_populates="approval")
    asset = relationship("Asset")

    __table_args__ = (
        Index("idx_approval_asset", "asset_id"),
        Index("idx_approval_approved_at", "approved_at"),
    )

    def __repr__(self):
        return f"<Approval {self.id}>"


class ProcessedAsset(Base):
    __tablename__ = "processed_assets"

    id = Column(Integer, primary_key=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), unique=True, nullable=False)
    asset_id = Column(String(255), ForeignKey("assets.asset_id"), nullable=False)

    processed_image_path = Column(String(1024), nullable=False)
    bounding_box_x = Column(Integer, nullable=True)
    bounding_box_y = Column(Integer, nullable=True)
    bounding_box_width = Column(Integer, nullable=True)
    bounding_box_height = Column(Integer, nullable=True)

    background_removed_at = Column(DateTime, nullable=True)
    resized_at = Column(DateTime, nullable=True)
    centered_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    generation = relationship("Generation", back_populates="processed_asset")
    asset = relationship("Asset", back_populates="processed_assets")

    __table_args__ = (
        Index("idx_processed_asset", "asset_id"),
    )

    def __repr__(self):
        return f"<ProcessedAsset {self.id}>"
