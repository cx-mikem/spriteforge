"""Configuration and environment loading."""

import os
from typing import Literal
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://spriteforge:spriteforge@localhost:5432/spriteforge"
    )

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Storage
    STORAGE_BACKEND: Literal["local", "s3", "replit"] = os.getenv(
        "STORAGE_BACKEND", "local"
    )
    STORAGE_LOCAL_PATH = os.getenv("STORAGE_LOCAL_PATH", "/data/storage")

    # S3
    S3_BUCKET = os.getenv("S3_BUCKET", "spriteforge-assets")
    S3_REGION = os.getenv("S3_REGION", "us-east-1")
    S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID")
    S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
    S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")

    # Replit
    REPLIT_OBJECT_STORAGE_TOKEN = os.getenv("REPLIT_OBJECT_STORAGE_TOKEN")

    # Generation
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
    MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    GENERATION_MODEL = os.getenv("GENERATION_MODEL", "dall-e-3")
    GENERATION_QUALITY = os.getenv("GENERATION_QUALITY", "hd")

    # Post-processing
    SPRITE_FORMAT = os.getenv("SPRITE_FORMAT", "png")
    BACKGROUND_REMOVAL_ENABLED = os.getenv("BACKGROUND_REMOVAL_ENABLED", "true").lower() == "true"

    # Atlas
    MAX_ATLAS_WIDTH = int(os.getenv("MAX_ATLAS_WIDTH", "2048"))
    MAX_ATLAS_HEIGHT = int(os.getenv("MAX_ATLAS_HEIGHT", "2048"))

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        """Validate critical config at startup."""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        if cls.STORAGE_BACKEND == "s3" and not (cls.S3_ACCESS_KEY_ID and cls.S3_SECRET_ACCESS_KEY):
            raise ValueError("S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY required for S3 backend")
        if cls.STORAGE_BACKEND == "replit" and not cls.REPLIT_OBJECT_STORAGE_TOKEN:
            raise ValueError("REPLIT_OBJECT_STORAGE_TOKEN required for Replit backend")
