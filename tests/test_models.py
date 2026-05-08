"""Tests for ORM models."""

from app.models import Asset, StyleAnchor, Generation, Approval


def test_asset_creation(test_db):
    """Test creating an asset."""
    asset = Asset(
        asset_id="test_01",
        category="test",
        display_name="Test Asset",
        sprite_width_px=64,
        sprite_height_px=64,
    )
    test_db.add(asset)
    test_db.commit()

    retrieved = test_db.query(Asset).filter(Asset.asset_id == "test_01").first()
    assert retrieved is not None
    assert retrieved.display_name == "Test Asset"
    assert retrieved.category == "test"


def test_style_anchor_creation(test_db, sample_asset):
    """Test creating a style anchor."""
    anchor = StyleAnchor(
        anchor_id="test_anchor_1",
        asset_id=sample_asset.asset_id,
        prompt_template="A test prompt",
        seed=123,
    )
    test_db.add(anchor)
    test_db.commit()

    retrieved = test_db.query(StyleAnchor).filter(
        StyleAnchor.anchor_id == "test_anchor_1"
    ).first()
    assert retrieved is not None
    assert retrieved.seed == 123
    assert retrieved.is_locked is False


def test_style_anchor_locking(test_db, sample_anchor):
    """Test locking a style anchor."""
    from datetime import datetime

    sample_anchor.locked_at = datetime.utcnow()
    sample_anchor.locked_by = "test_user"
    test_db.commit()

    retrieved = test_db.query(StyleAnchor).filter(
        StyleAnchor.anchor_id == sample_anchor.anchor_id
    ).first()
    assert retrieved.is_locked is True
    assert retrieved.locked_by == "test_user"


def test_generation_creation(test_db, sample_generation):
    """Test creating a generation."""
    assert sample_generation.status == "pending"
    assert sample_generation.image_count == 1
    assert sample_generation.api_cost_usd == 0.04


def test_generation_status_transition(test_db, sample_generation):
    """Test transitioning generation status."""
    sample_generation.status = "approved"
    test_db.commit()

    retrieved = test_db.query(Generation).filter(
        Generation.id == sample_generation.id
    ).first()
    assert retrieved.status == "approved"


def test_approval_creation(test_db, sample_generation):
    """Test creating an approval."""
    from datetime import datetime

    approval = Approval(
        generation_id=sample_generation.id,
        asset_id=sample_generation.asset_id,
        approved_by="test_user",
        chosen_image_index=0,
        notes="Looks good!",
    )
    test_db.add(approval)
    test_db.commit()

    retrieved = test_db.query(Approval).filter(
        Approval.generation_id == sample_generation.id
    ).first()
    assert retrieved is not None
    assert retrieved.approved_by == "test_user"
    assert retrieved.notes == "Looks good!"


def test_asset_relationships(test_db, sample_asset, sample_anchor, sample_generation):
    """Test model relationships."""
    # Asset → StyleAnchors
    assert len(sample_asset.style_anchors) == 1
    assert sample_asset.style_anchors[0].anchor_id == "test_creep_v1"

    # Asset → Generations
    assert len(sample_asset.generations) == 1
    assert sample_asset.generations[0].api_cost_usd == 0.04
