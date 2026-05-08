"""Pytest fixtures for testing."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Asset, StyleAnchor, Generation


@pytest.fixture
def test_db():
    """Create an in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def sample_asset(test_db):
    """Create a sample asset for testing."""
    asset = Asset(
        asset_id="test_creep_01",
        category="creep",
        display_name="Test Creep",
        sprite_width_px=64,
        sprite_height_px=64,
        animation_type="loop",
        frame_count=4,
    )
    test_db.add(asset)
    test_db.commit()
    return asset


@pytest.fixture
def sample_anchor(test_db, sample_asset):
    """Create a sample style anchor."""
    anchor = StyleAnchor(
        anchor_id="test_creep_v1",
        asset_id=sample_asset.asset_id,
        prompt_template="A cute 16-bit pixel art creep monster",
        seed=42,
        style_instruction="pixel art, retro game style",
    )
    test_db.add(anchor)
    test_db.commit()
    return anchor


@pytest.fixture
def sample_generation(test_db, sample_asset, sample_anchor):
    """Create a sample generation."""
    gen = Generation(
        asset_id=sample_asset.asset_id,
        anchor_id=sample_anchor.anchor_id,
        status="pending",
        image_paths=["storage/generated/test_1.png"],
        image_count=1,
        api_cost_usd=0.04,
        prompt_used="A cute 16-bit pixel art creep monster",
    )
    test_db.add(gen)
    test_db.commit()
    return gen
