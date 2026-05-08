"""Atlas and AtlasEntry models."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Atlas(Base):
    __tablename__ = "atlases"

    id = Column(Integer, primary_key=True)
    version = Column(String(50), nullable=False)  # e.g., "1.0", "1.1"
    category = Column(String(100), nullable=False)

    sprite_sheet_path = Column(String(1024), nullable=False)
    manifest_json_path = Column(String(1024), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    is_current = Column(Boolean, default=True)

    asset_count = Column(Integer, nullable=True)
    atlas_width_px = Column(Integer, nullable=True)
    atlas_height_px = Column(Integer, nullable=True)

    # Relationships
    entries = relationship("AtlasEntry", back_populates="atlas")

    __table_args__ = (
        Index("idx_atlas_category_current", "category", "is_current"),
        Index("idx_atlas_created", "created_at"),
    )

    def __repr__(self):
        return f"<Atlas {self.category} v{self.version}>"


class AtlasEntry(Base):
    __tablename__ = "atlas_entries"

    id = Column(Integer, primary_key=True)
    atlas_id = Column(Integer, ForeignKey("atlases.id"), nullable=False)
    asset_id = Column(String(255), ForeignKey("assets.asset_id"), nullable=False)

    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)

    frame_count = Column(Integer, default=1)
    frames_per_row = Column(Integer, nullable=True)

    # Relationships
    atlas = relationship("Atlas", back_populates="entries")
    asset = relationship("Asset")

    __table_args__ = (
        Index("idx_atlas_entry_atlas_asset", "atlas_id", "asset_id"),
    )

    def __repr__(self):
        return f"<AtlasEntry {self.asset_id} @ {self.atlas_id}>"
