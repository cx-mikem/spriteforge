"""Atlas packing service for sprite sheet generation."""

import json
import logging
from pathlib import Path
from PIL import Image
from rectpack import newPacker
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

        # Pack into sprite sheet
        packer = newPacker(
            mode="heuristic",
            rotation=False,
            width=self.max_width,
            height=self.max_height,
            pack_algo="shelf",
        )

        # Add images to packer
        for asset_id, img in images.items():
            width, height = img.size
            packer.add_rect(width, height, rid=asset_id)

        packer.pack()

        # Create the sprite sheet
        agg_rect = packer.rect_list()
        if not agg_rect:
            logger.error("Packing failed")
            return None

        # Find actual canvas size needed
        max_x = max(rect[0] + rect[2] for rect in agg_rect) if agg_rect else self.max_width
        max_y = max(rect[1] + rect[3] for rect in agg_rect) if agg_rect else self.max_height
        actual_width = min(max_x, self.max_width)
        actual_height = min(max_y, self.max_height)

        sprite_sheet = Image.new("RGBA", (actual_width, actual_height), (0, 0, 0, 0))

        # Build frame map for JSON manifest
        frames = {}
        atlas_entries = []

        for b, x, y, w, h, asset_id in agg_rect:
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
