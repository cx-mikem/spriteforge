"""Tests for services."""

import pytest
from app.services import GenerationService, PostProcessService
from app.config import Config


def test_generation_service_init():
    """Test GenerationService initialization."""
    # Skip OpenAI client instantiation for unit tests
    # GenerationService will be tested in integration tests
    assert Config.GENERATION_MODEL == "dall-e-3"
    assert Config.GENERATION_QUALITY == "hd"
    assert Config.MAX_RETRY_ATTEMPTS > 0


def test_generation_service_has_methods():
    """Test that GenerationService has required methods."""
    assert hasattr(GenerationService, "generate")
    assert hasattr(GenerationService, "_estimate_cost")


def test_post_process_service_init():
    """Test PostProcessService initialization."""
    service = PostProcessService()
    # bg_removal_enabled may be False if rembg is not installed
    assert service.sprite_format == Config.SPRITE_FORMAT


def test_post_process_service_has_methods():
    """Test that PostProcessService has required methods."""
    service = PostProcessService()
    assert hasattr(service, "process")
    assert callable(service.process)
    assert hasattr(service, "_download_image")
    assert hasattr(service, "_detect_bounding_box")
    assert hasattr(service, "_center_and_pad")
