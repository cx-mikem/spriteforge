"""Atlas packing service for sprite sheet generation."""

import json
import logging
from pathlib import Path
from PIL import Image
from sqlalchemy.orm import Session
from app.models import Asset, ProcessedAsset, Atlas, AtlasEntry
from app.config import Config
from storage import get_storage_backend

logger = logging.getLogger(__name__)


class AtlasPacker:
    """Pack approved processed assets into sprite sheets."""

    def __init__(self, db: Session):
        self.db = db
        self.storage = get_storage_backend()
        self.max_width = Config.MAX_ATLAS_WIDTH
        self.max_height = Config.MAX_ATLAS_HEIGHT

    def pack_category(self, category: str, version: str = None) -> dict:
        """
        Pack all approved processed assets in a category into a sprite sheet.

        Args:
            category: Asset category (e.g., "creep", "structure")
            version: Version string (auto-incremented if not provided)

        Returns:
            {
                "atlas_id": 123,
                "sprite_sheet_path": "atlases/creep/1.0.png",
                "manifest_json_path": "atlases/creep/1.0.json",
            }
        """
        # Fetch all approved processed assets in this category
        assets = self.db.query(Asset).filter(Asset.category == category).all()
        if not assets:
            logger.warning(f"No assets found in category {category}")
            return None

        processed = {}
        for asset in assets:
            p = self.db.query(ProcessedAsset).join(
                ProcessedAsset.generation
            ).filter(
                ProcessedAsset.asset_id == asset.asset_id
            ).first()
            if p:
                processed[asset.asset_id] = p

        if not processed:
            logger.warning(f"No processed assets in category {category}")
            return None

        logger.info(f"Packing {len(processed)} assets from {category}")

        # Load processed images
        images = {}
        for asset_id, proc in processed.items():
            img_path = Path(proc.processed_image_path)
            if not img_path.exists():
                logger.warning(f"Processed image not found: {img_path}")
                continue
            images[asset_id] = Image.open(img_path)

        if not images:
            logger.error("No processed images could be loaded")
            return None

        # Simple grid-based packing
        positions = self._pack_grid(images, self.max_width, self.max_height)
        if not positions:
            logger.error("Packing failed - images too large for atlas")
            return None

        # Calculate actual canvas size needed
        actual_width = max(x + w for x, y, w, h in positions.values()) if positions else self.max_width
        actual_height = max(y + h for x, y, w, h in positions.values()) if positions else self.max_height
        actual_width = min(actual_width, self.max_width)
        actual_height = min(actual_height, self.max_height)

        sprite_sheet = Image.new("RGBA", (actual_width, actual_height), (0, 0, 0, 0))

        # Build frame map for JSON manifest
        frames = {}
        atlas_entries = []

        for asset_id, (x, y, w, h) in positions.items():
            img = images[asset_id]
            sprite_sheet.paste(img, (x, y), img)

            asset = self.db.query(Asset).filter(Asset.asset_id == asset_id).first()
            frame_count = asset.frame_count if asset else 1

            frames[asset_id] = {
                "frame": {"x": x, "y": y, "w": w, "h": h},
                "rotated": False,
                "trimmed": False,
                "spriteSourceSize": {"x": 0, "y": 0, "w": w, "h": h},
                "sourceSize": {"w": w, "h": h},
                "duration": 100,  # default frame duration
            }

            atlas_entries.append(
                {
                    "asset_id": asset_id,
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "frame_count": frame_count,
                }
            )

        # Save sprite sheet
        atlas_dir = Path("atlases") / category
        if version is None:
            # Auto-increment version
            existing = self.db.query(Atlas).filter(
                Atlas.category == category
            ).order_by(Atlas.version.desc()).first()
            if existing:
                major, minor = map(int, existing.version.split("."))
                version = f"{major}.{minor + 1}"
            else:
                version = "1.0"

        sprite_path = atlas_dir / f"{version}.png"
        manifest_path = atlas_dir / f"{version}.json"

        sprite_path.parent.mkdir(parents=True, exist_ok=True)
        sprite_sheet.save(sprite_path)
        logger.info(f"Saved sprite sheet: {sprite_path}")

        # Save manifest
        manifest = {
            "frames": frames,
            "meta": {
                "app": "spriteforge",
                "version": "1.0",
                "image": str(sprite_path),
                "format": "RGBA",
                "size": {"w": actual_width, "h": actual_height},
                "scale": "1",
            },
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Saved manifest: {manifest_path}")

        # Save to storage
        remote_sprite_path = self.storage.save(sprite_path, str(sprite_path))
        remote_manifest_path = self.storage.save(manifest_path, str(manifest_path))

        # Create Atlas record
        atlas = Atlas(
            version=version,
            category=category,
            sprite_sheet_path=remote_sprite_path,
            manifest_json_path=remote_manifest_path,
            asset_count=len(atlas_entries),
            atlas_width_px=actual_width,
            atlas_height_px=actual_height,
        )
        self.db.add(atlas)

        # Mark old atlases as not current
        self.db.query(Atlas).filter(
            Atlas.category == category,
            Atlas.id != atlas.id,
        ).update({"is_current": False})

        for entry_data in atlas_entries:
            entry = AtlasEntry(
                atlas_id=atlas.id,
                asset_id=entry_data["asset_id"],
                x=entry_data["x"],
                y=entry_data["y"],
                width=entry_data["width"],
                height=entry_data["height"],
                frame_count=entry_data["frame_count"],
            )
            self.db.add(entry)

        self.db.commit()
        logger.info(f"Created atlas record: {version}")

        return {
            "atlas_id": atlas.id,
            "sprite_sheet_path": remote_sprite_path,
            "manifest_json_path": remote_manifest_path,
            "version": version,
        }

    def _pack_grid(self, images: dict, max_width: int, max_height: int) -> dict:
        """
        Simple grid-based bin packing.
        Returns {asset_id: (x, y, w, h)} or empty dict if packing fails.
        """
        positions = {}
        rows = []
        current_row = []
        current_y = 0
        max_row_height = 0

        sorted_images = sorted(images.items(), key=lambda x: x[1].height, reverse=True)

        for asset_id, img in sorted_images:
            width, height = img.size

            # Try to fit in current row
            current_x = sum(current_row[i][2] for i in range(len(current_row)))

            if current_x + width > max_width and current_row:
                # Start new row
                rows.append(current_row)
                current_row = []
                current_y += max_row_height
                max_row_height = 0
                current_x = 0

            if current_y + height > max_height:
                # Cannot fit - packing failed
                logger.warning("Image does not fit in atlas")
                return {}

            current_row.append((asset_id, current_x, width, height))
            max_row_height = max(max_row_height, height)

        if current_row:
            rows.append(current_row)

        # Convert rows to absolute positions
        current_y = 0
        for row in rows:
            for asset_id, x, w, h in row:
                positions[asset_id] = (x, current_y, w, h)
            if row:
                current_y += max(h for _, _, _, h in row)

        return positions
