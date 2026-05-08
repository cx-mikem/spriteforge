"""Asset and StyleAnchor models."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True)
    asset_id = Column(String(255), unique=True, nullable=False)
    category = Column(String(100), nullable=False)
    display_name = Column(String(255))
    description = Column(Text)

    sprite_width_px = Column(Integer, nullable=False)
    sprite_height_px = Column(Integer, nullable=False)
    animation_type = Column(String(50), default="static")  # static, loop, transition
    frame_count = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    style_anchors = relationship("StyleAnchor", foreign_keys="[StyleAnchor.asset_id]", back_populates="asset", primaryjoin="Asset.asset_id==StyleAnchor.asset_id")
    generations = relationship("Generation", foreign_keys="[Generation.asset_id]", back_populates="asset", primaryjoin="Asset.asset_id==Generation.asset_id")
    processed_assets = relationship("ProcessedAsset", foreign_keys="[ProcessedAsset.asset_id]", back_populates="asset", primaryjoin="Asset.asset_id==ProcessedAsset.asset_id")

    __table_args__ = (
        Index("idx_asset_category", "category"),
    )

    def __repr__(self):
        return f"<Asset {self.asset_id}>"


class StyleAnchor(Base):
    __tablename__ = "style_anchors"

    id = Column(Integer, primary_key=True)
    anchor_id = Column(String(255), unique=True, nullable=False)
    asset_id = Column(String(255), nullable=False)

    prompt_template = Column(Text, nullable=False)
    seed = Column(Integer, nullable=True)
    base_negative_prompt = Column(Text, nullable=True)
    reference_image_path = Column(String(1024), nullable=True)

    model = Column(String(100), default="dall-e-3")
    style_instruction = Column(Text, nullable=True)

    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    asset = relationship("Asset", foreign_keys="[StyleAnchor.asset_id]", back_populates="style_anchors", primaryjoin="Asset.asset_id==StyleAnchor.asset_id")
    generations = relationship("Generation", back_populates="anchor")

    __table_args__ = (
        Index("idx_style_anchor_asset", "asset_id"),
    )

    def __repr__(self):
        return f"<StyleAnchor {self.anchor_id}>"

    @property
    def is_locked(self) -> bool:
        return self.locked_at is not None
