"""Generation service for ChatGPT API integration."""

import time
import logging
from decimal import Decimal
from openai import OpenAI
from app.config import Config

logger = logging.getLogger(__name__)


class GenerationService:
    """Wrapper around ChatGPT API for image generation."""

    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.GENERATION_MODEL
        self.quality = Config.GENERATION_QUALITY
        self.max_retries = Config.MAX_RETRY_ATTEMPTS

    def generate(
        self,
        prompt: str,
        negative_prompt: str = None,
        seed: int = None,
        num_variants: int = 1,
    ) -> dict:
        """
        Generate image(s) from a prompt.

        Args:
            prompt: The main prompt
            negative_prompt: Optional negative prompt
            seed: Optional seed for reproducibility
            num_variants: How many variants to generate

        Returns:
            {
                "images": [{"url": "...", "path": None}],  # URLs from API
                "cost_usd": 0.02,
                "model": "dall-e-3",
            }
        """
        full_prompt = prompt
        if negative_prompt:
            full_prompt += f"\n\nNegative: {negative_prompt}"

        retry_count = 0
        while retry_count < self.max_retries:
            try:
                response = self.client.images.generate(
                    model=self.model,
                    prompt=full_prompt,
                    n=num_variants,
                    size="1024x1024",
                    quality=self.quality,
                )

                images = [{"url": img.url, "path": None} for img in response.data]
                cost = self._estimate_cost(num_variants)

                logger.info(
                    f"Generated {num_variants} image(s) for prompt. Cost: ${cost}"
                )

                return {
                    "images": images,
                    "cost_usd": Decimal(str(cost)),
                    "model": self.model,
                }

            except Exception as e:
                retry_count += 1
                wait_time = 2 ** retry_count  # exponential backoff
                logger.warning(
                    f"Generation failed (attempt {retry_count}): {e}. "
                    f"Retrying in {wait_time}s..."
                )
                if retry_count >= self.max_retries:
                    logger.error(f"Generation failed after {self.max_retries} retries")
                    raise
                time.sleep(wait_time)

    def _estimate_cost(self, num_variants: int) -> float:
        """Estimate cost per generation. Real costs come from usage reports."""
        # DALL-E 3 standard: $0.04 per image
        # This is an estimate; actual costs tracked separately
        return 0.04 * num_variants
