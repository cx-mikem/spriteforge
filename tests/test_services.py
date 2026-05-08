"""Tests for services."""

import pytest
from app.services import GenerationService, PostProcessService
from app.config import Config


def test_generation_service_init():
    """Test GenerationService initialization."""
    service = GenerationService()
    assert service.model == Config.GENERATION_MODEL
    assert service.quality == Config.GENERATION_QUALITY
    assert service.max_retries == Config.MAX_RETRY_ATTEMPTS


def test_generation_service_has_methods():
    """Test that GenerationService has required methods."""
    service = GenerationService()
    assert hasattr(service, "generate")
    assert callable(service.generate)


def test_post_process_service_init():
    """Test PostProcessService initialization."""
    service = PostProcessService()
    assert service.bg_removal_enabled == Config.BACKGROUND_REMOVAL_ENABLED
    assert service.sprite_format == Config.SPRITE_FORMAT


def test_post_process_service_has_methods():
    """Test that PostProcessService has required methods."""
    service = PostProcessService()
    assert hasattr(service, "process")
    assert callable(service.process)
    assert hasattr(service, "_download_image")
    assert hasattr(service, "_detect_bounding_box")
    assert hasattr(service, "_center_and_pad")
