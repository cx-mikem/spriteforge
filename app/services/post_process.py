"""Post-processing service for image cleanup and alignment."""

import logging
from io import BytesIO
from pathlib import Path
from PIL import Image
import requests
from app.config import Config

logger = logging.getLogger(__name__)


class PostProcessService:
    """Handle image cleanup: background removal, alignment, resizing."""

    def __init__(self):
        self.bg_removal_enabled = Config.BACKGROUND_REMOVAL_ENABLED
        self.sprite_format = Config.SPRITE_FORMAT
        self.remove_bg = None

        if self.bg_removal_enabled:
            try:
                from rembg import remove
                self.remove_bg = remove
            except ImportError:
                logger.info("rembg not installed; install with: pip install rembg")
                self.bg_removal_enabled = False

    def process(
        self,
        image_url: str,
        sprite_width: int,
        sprite_height: int,
        output_path: Path,
    ) -> dict:
        """
        Process a generated image:
        1. Download from URL
        2. Remove background (if enabled)
        3. Detect bounding box
        4. Center and pad to sprite size
        5. Save

        Args:
            image_url: URL of generated image
            sprite_width: Target width in pixels
            sprite_height: Target height in pixels
            output_path: Where to save processed image

        Returns:
            {
                "processed_image_path": "...",
                "bounding_box": {"x": 10, "y": 5, "width": 80, "height": 90},
            }
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Download image from URL
        img = self._download_image(image_url)
        logger.info(f"Downloaded image {img.size}")

        # Remove background
        if self.bg_removal_enabled:
            img = self.remove_bg(img)
            logger.info("Background removed")

        # Detect bounding box of non-transparent content
        bbox = self._detect_bounding_box(img)
        logger.info(f"Bounding box: {bbox}")

        # Center and pad to target sprite size
        img = self._center_and_pad(img, sprite_width, sprite_height)
        logger.info(f"Resized to {sprite_width}x{sprite_height}")

        # Save
        output_path = output_path.with_suffix(f".{self.sprite_format}")
        img.save(output_path, self.sprite_format.upper())
        logger.info(f"Saved to {output_path}")

        return {
            "processed_image_path": str(output_path),
            "bounding_box": {
                "x": bbox[0],
                "y": bbox[1],
                "width": bbox[2] - bbox[0],
                "height": bbox[3] - bbox[1],
            },
        }

    def _download_image(self, url: str) -> Image.Image:
        """Download image from URL."""
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")

    def _detect_bounding_box(self, img: Image.Image) -> tuple:
        """
        Detect bounding box of non-transparent content.
        Returns (x1, y1, x2, y2).
        """
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        data = img.getdata()
        pixels = img.load()
        width, height = img.size

        min_x, min_y = width, height
        max_x, max_y = 0, 0

        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                if a > 128:  # consider alpha > 50% as opaque
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        # If all transparent, return full image bounds
        if min_x >= max_x or min_y >= max_y:
            return (0, 0, width, height)

        return (min_x, min_y, max_x + 1, max_y + 1)

    def _center_and_pad(
        self, img: Image.Image, target_width: int, target_height: int
    ) -> Image.Image:
        """Center image and pad to target size with transparency."""
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # Create transparent canvas
        canvas = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))

        # Scale image to fit within target, maintaining aspect ratio
        img.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)

        # Center on canvas
        x = (target_width - img.width) // 2
        y = (target_height - img.height) // 2
        canvas.paste(img, (x, y), img)

        return canvas
