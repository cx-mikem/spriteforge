# spriteforge Architecture Proposal

## 1. System Architecture

### High-Level Overview
```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web App                         │
│  (UI: Manifest, Generations, Review, Preview, Gallery)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
    ┌────▼────┐         ┌──────▼──────┐      ┌──────▼──────┐
    │ Manifest│         │ Generation  │      │  Approval & │
    │ Manager │         │ Orchestrator│      │ Review Flow │
    └────┬────┘         └──────┬──────┘      └──────┬──────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Pipeline Service   │
                    │  (Coordinating      │
                    │   Generation,       │
                    │   Processing,       │
                    │   Packing)          │
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
    ┌────▼──────┐      ┌──────▼──────┐      ┌──────▼──────┐
    │   ChatGPT │      │Post-Process │      │    Atlas    │
    │ Generation│      │  (Cleanup,  │      │   Packer    │
    │  Service  │      │ Align, Pad) │      │             │
    └────┬──────┘      └──────┬──────┘      └──────┬──────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Storage Layer      │
                    │  (Pluggable:        │
                    │   Local FS, S3, etc)│
                    └────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │     Postgres        │
                    │   (Metadata,        │
                    │    Manifest,        │
                    │    Approvals)       │
                    └────────────────────┘
```

### Layer Details

#### 1. UI Layer (Streamlit)
- **Pages**: 
  - `Manifest` - define and edit asset registry
  - `Generate` - trigger generation batches
  - `Review` - approve/reject pending generations with preview
  - `Gallery` - view all approved assets (bestiary)
  - `Export` - download engine-ready bundles
  - `Settings` - configure storage, API keys, generation parameters

#### 2. Service Layer
**PipelineService**: Orchestrates entire flow
- Receives generation requests from UI
- Batches them efficiently
- Coordinates with ChatGPT API
- Routes approved assets to post-processing
- Manages atlas packing
- Tracks cost and progress

**GenerationService**: Wraps ChatGPT API
- Calls OpenAI API with style anchor + prompt template
- Handles retries with exponential backoff
- Logs cost per generation
- Returns image URLs and metadata

**PostProcessService**: Cleans up generated images
- Background removal (rembg or PIL)
- Bounding box detection & recentering
- Palette analysis (optional locking for animations)
- Resize to target sprite size
- High-quality downscaling

**AtlasPacker**: Builds sprite sheets
- Groups approved assets by category
- Packs into sprite sheets (max 2048×2048)
- Generates Phaser-compatible JSON manifest
- Versions output (archive old atlases)
- Calculates frame offsets for animations

#### 3. Storage Layer
**StorageBackend** (pluggable interface)
- `LocalStorageBackend` - filesystem in docker volume
- `S3StorageBackend` - S3-compatible (AWS, Wasabi, etc)
- `ReplitStorageBackend` - Replit object storage

Key paths stored:
- `generated/` - raw outputs from ChatGPT
- `processed/` - after post-processing
- `atlases/` - final sprite sheets + JSON
- `assets/` - other (reference images, etc)

#### 4. Database Layer (Postgres)
- Manifest entries (assets, categories)
- Style anchors (prompts, seeds, references)
- Generations (batches, URLs, costs, status)
- Approvals (which generations are approved)
- Atlas versions (what's in each shipped atlas)
- Generation costs (tracking spend over time)

---

## 2. Database Schema

### Core Tables

#### `assets`
```sql
CREATE TABLE assets (
  id SERIAL PRIMARY KEY,
  asset_id VARCHAR(255) UNIQUE NOT NULL,  -- e.g., "creep_01"
  category VARCHAR(100) NOT NULL,          -- e.g., "creep"
  display_name VARCHAR(255),
  description TEXT,
  
  -- Rendering
  sprite_width_px INT NOT NULL,
  sprite_height_px INT NOT NULL,
  animation_type VARCHAR(50) DEFAULT 'static',  -- static, loop, transition
  frame_count INT DEFAULT 1,
  
  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  deleted_at TIMESTAMP,  -- soft delete for rollback
  
  CONSTRAINT animation_frames CHECK (
    (animation_type = 'static' AND frame_count = 1) OR
    (animation_type IN ('loop', 'transition') AND frame_count > 1)
  )
);
```

#### `style_anchors`
```sql
CREATE TABLE style_anchors (
  id SERIAL PRIMARY KEY,
  anchor_id VARCHAR(255) UNIQUE NOT NULL,
  asset_id VARCHAR(255) NOT NULL REFERENCES assets(asset_id),
  
  -- The recipe for consistent generation
  prompt_template TEXT NOT NULL,
  seed INT,  -- optional, for reproducibility
  base_negative_prompt TEXT,
  
  -- Reference image for consistency
  reference_image_path VARCHAR(1024),  -- path in storage, or NULL
  
  -- Model params
  model VARCHAR(100) DEFAULT 'dall-e-3',
  style_instruction TEXT,  -- e.g., "pixel art, 16-bit"
  
  -- Locking
  locked_at TIMESTAMP,  -- NULL = unlocked, set to prevent drift
  locked_by VARCHAR(255),
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  INDEX (asset_id)
);
```

#### `generations`
```sql
CREATE TABLE generations (
  id SERIAL PRIMARY KEY,
  batch_id VARCHAR(255),  -- groups multiple generations
  asset_id VARCHAR(255) NOT NULL REFERENCES assets(asset_id),
  anchor_id VARCHAR(255) REFERENCES style_anchors(anchor_id),
  
  -- Results
  status VARCHAR(50) DEFAULT 'pending',  -- pending, approved, rejected, processing
  
  -- Multiple candidates per asset
  image_paths JSONB,  -- ["storage/path/img_1.png", "storage/path/img_2.png"]
  image_count INT DEFAULT 1,
  
  -- Metadata
  prompt_used TEXT,
  model VARCHAR(100),
  api_cost_usd DECIMAL(10, 4),
  
  -- Timeline
  created_at TIMESTAMP DEFAULT NOW(),
  approved_at TIMESTAMP,
  approved_by VARCHAR(255),
  rejected_at TIMESTAMP,
  rejected_by VARCHAR(255),
  
  -- Retry logic
  retry_count INT DEFAULT 0,
  last_error TEXT,
  
  INDEX (asset_id, status),
  INDEX (batch_id),
  INDEX (created_at)
);
```

#### `approvals`
```sql
CREATE TABLE approvals (
  id SERIAL PRIMARY KEY,
  generation_id INT UNIQUE NOT NULL REFERENCES generations(id),
  asset_id VARCHAR(255) NOT NULL REFERENCES assets(asset_id),
  approved_by VARCHAR(255) NOT NULL,
  approved_at TIMESTAMP DEFAULT NOW(),
  
  -- Which image from the batch?
  chosen_image_index INT DEFAULT 0,
  
  -- Optional notes
  notes TEXT,
  
  -- For animation, optionally override playback FPS
  playback_fps INT,
  
  INDEX (asset_id),
  INDEX (approved_at)
);
```

#### `processed_assets`
```sql
CREATE TABLE processed_assets (
  id SERIAL PRIMARY KEY,
  generation_id INT UNIQUE NOT NULL REFERENCES generations(id),
  asset_id VARCHAR(255) NOT NULL REFERENCES assets(asset_id),
  
  -- Post-processing results
  processed_image_path VARCHAR(1024) NOT NULL,
  bounding_box_x INT,
  bounding_box_y INT,
  bounding_box_width INT,
  bounding_box_height INT,
  
  -- Processing metadata
  background_removed_at TIMESTAMP,
  resized_at TIMESTAMP,
  centered_at TIMESTAMP,
  
  created_at TIMESTAMP DEFAULT NOW(),
  
  INDEX (asset_id)
);
```

#### `atlases`
```sql
CREATE TABLE atlases (
  id SERIAL PRIMARY KEY,
  version VARCHAR(50) NOT NULL,  -- e.g., "1.0", "1.1"
  category VARCHAR(100) NOT NULL,
  
  -- Output files
  sprite_sheet_path VARCHAR(1024) NOT NULL,
  manifest_json_path VARCHAR(1024) NOT NULL,
  
  -- Versioning
  created_at TIMESTAMP DEFAULT NOW(),
  is_current BOOLEAN DEFAULT TRUE,
  
  -- Metadata
  asset_count INT,
  atlas_width_px INT,
  atlas_height_px INT,
  
  INDEX (category, is_current),
  INDEX (created_at)
);
```

#### `atlas_entries`
```sql
CREATE TABLE atlas_entries (
  id SERIAL PRIMARY KEY,
  atlas_id INT NOT NULL REFERENCES atlases(id),
  asset_id VARCHAR(255) NOT NULL REFERENCES assets(asset_id),
  
  -- Position in sprite sheet
  x INT NOT NULL,
  y INT NOT NULL,
  width INT NOT NULL,
  height INT NOT NULL,
  
  -- For animated assets, frame layout
  frame_count INT DEFAULT 1,
  frames_per_row INT,  -- how atlas is laid out
  
  INDEX (atlas_id, asset_id)
);
```

#### `generation_costs`
```sql
CREATE TABLE generation_costs (
  id SERIAL PRIMARY KEY,
  generation_id INT NOT NULL REFERENCES generations(id),
  cost_usd DECIMAL(10, 4) NOT NULL,
  timestamp TIMESTAMP DEFAULT NOW(),
  
  INDEX (timestamp)
);
```

### Key Indexes for Query Performance
- `generations(asset_id, status)` - frequent filters
- `generations(batch_id)` - batch operations
- `approvals(asset_id)` - finding approved assets
- `atlases(category, is_current)` - current atlases by category
- `assets(asset_id)` - unique lookup
- `style_anchors(asset_id)` - find anchor for asset

---

## 3. Folder Structure

```
spriteforge/
├── .github/
│   └── workflows/
│       ├── build.yml          # Docker build + push on PR/main
│       └── smoke-tests.yml    # Basic integration tests
│
├── app/
│   ├── __init__.py
│   ├── main.py                # Streamlit entry point
│   ├── config.py              # Settings, env var loading
│   ├── database.py            # DB connection & session management
│   ├── storage.py             # Storage backend abstraction
│   │
│   ├── pages/
│   │   ├── 00_manifest.py     # Asset registry UI
│   │   ├── 01_generate.py     # Generation trigger UI
│   │   ├── 02_review.py       # Approval gallery UI
│   │   ├── 03_gallery.py      # Bestiary (approved assets)
│   │   ├── 04_export.py       # Download bundles
│   │   └── 05_settings.py     # Config UI
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── asset.py           # Asset, StyleAnchor ORM
│   │   ├── generation.py      # Generation, Approval ORM
│   │   ├── atlas.py           # Atlas, AtlasEntry ORM
│   │   └── cost.py            # Cost tracking ORM
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pipeline.py        # Main orchestrator
│   │   ├── generation.py      # ChatGPT API wrapper
│   │   ├── post_process.py    # Image cleanup, alignment
│   │   ├── atlas_packer.py    # Sprite sheet + JSON gen
│   │   └── cost_tracker.py    # Spend tracking
│   │
│   ├── components/
│   │   ├── __init__.py
│   │   ├── asset_grid.py      # Reusable asset display
│   │   ├── animation_preview.py  # Animation player
│   │   ├── manifest_editor.py # Manifest table editor
│   │   └── progress.py        # Generation progress display
│   │
│   └── utils/
│       ├── __init__.py
│       ├── validators.py      # Manifest validation
│       ├── formatting.py      # Cost, date formatting
│       └── logging.py         # Structured logging
│
├── migrations/
│   ├── 001_initial_schema.sql
│   ├── 002_add_indexes.sql
│   └── README.md              # Migration instructions
│
├── storage/
│   ├── __init__.py
│   ├── base.py                # Abstract storage backend
│   ├── local.py               # Local filesystem
│   ├── s3.py                  # S3-compatible
│   └── replit.py              # Replit object storage
│
├── scripts/
│   ├── init_db.py             # Initialize DB from scratch
│   ├── migrate.py             # Run migrations
│   ├── seed_manifest.py       # Load sample manifest
│   └── health_check.py        # Container health endpoint
│
├── docker/
│   ├── Dockerfile             # Multi-stage Python + Streamlit
│   ├── .dockerignore
│   └── requirements-docker.txt
│
├── config/
│   ├── sample_manifest.json   # Example asset registry
│   ├── sample_settings.json   # Example generation config
│   └── phaser_export.py       # Phaser-specific atlas format
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Pytest fixtures
│   ├── test_models.py         # ORM tests
│   ├── test_services.py       # Service layer tests
│   ├── test_storage.py        # Storage backend tests
│   └── integration/
│       └── test_full_pipeline.py  # End-to-end test
│
├── docs/
│   ├── GETTING_STARTED.md
│   ├── MANIFEST_FORMAT.md
│   ├── STORAGE_BACKENDS.md
│   ├── EXPORT_FORMATS.md
│   └── TROUBLESHOOTING.md
│
├── docker-compose.yml         # Local dev: app + postgres
├── .env.example               # All required env vars
├── .gitignore
├── README.md                  # Project overview
├── ARCHITECTURE.md            # This document
├── LICENSE                    # MIT
├── requirements.txt           # Python dependencies
└── pyproject.toml             # Build config, pytest setup
```

---

## 4. Tech Stack Rationale

| Component | Choice | Why |
|-----------|--------|-----|
| Web Framework | Streamlit | Fast iteration, minimal HTML/CSS, built-in components |
| Database | Postgres | Relational data (assets, approvals, versions), JSON support, JSONB for flexibility |
| Storage | Pluggable | Supports local dev, S3 for production, Replit for hosted hobby projects |
| Image Gen | ChatGPT API (DALL-E) | Reliable, cost-visible, high quality for 2D art, batch inference |
| Post-Process | PIL + rembg | PIL for alignment/resize, rembg for background removal (fast, Python-native) |
| Atlas Packing | PIL + pypacker (or Rectpack) | Pure Python, no native deps, fast for typical atlas sizes |
| Deployment | Docker + docker-compose | Works on Replit, Fly.io, Railway, local machines, any Linux host |

---

## 5. Data Flow Example: "Generate a Single Asset"

```
User clicks "Generate" for asset "creep_01"
    │
    ├─ Pipeline.generate_single(asset_id="creep_01")
    │
    ├─ Fetch asset from DB → Asset(sprite_width=64, sprite_height=64)
    │
    ├─ Fetch style anchor → StyleAnchor(prompt_template, seed)
    │
    ├─ Call GenerationService.generate()
    │   ├─ Format prompt: "{prompt_template}, pixel art, 16-bit style"
    │   ├─ Call OpenAI API with seed
    │   ├─ Get image URL
    │   ├─ Log cost
    │   └─ Return Generation(status='pending', image_url)
    │
    ├─ Save Generation record to DB
    │   └─ Refresh Streamlit UI with pending generation
    │
    ├─ (User approves)
    │   ├─ Save Approval record
    │   │
    │   ├─ Call PostProcessService.process()
    │   │   ├─ Download image
    │   │   ├─ Remove background (rembg)
    │   │   ├─ Detect bounding box
    │   │   ├─ Center and pad to 64×64
    │   │   ├─ Save processed image to storage
    │   │   └─ Save ProcessedAsset record
    │   │
    │   ├─ Call AtlasPacker.repack_category("creep")
    │   │   ├─ Fetch all approved assets in category
    │   │   ├─ Pack them into a sprite sheet
    │   │   ├─ Generate Phaser-compatible JSON
    │   │   ├─ Save atlas files to storage
    │   │   ├─ Create Atlas version record (versioned, not overwritten)
    │   │   └─ Update is_current flag
    │   │
    │   └─ UI updates to show new atlas with "creep_01" included
```

---

## 6. Open Questions Resolved (for this proposal)

| Question | Decision |
|----------|----------|
| Animation preview engine | **Lighter playback**: Streamlit component that reads atlas JSON + PNG, renders frames at configurable FPS. Not embedding a full game engine. Can preview at 1x/2x/4x zoom, on colored backgrounds. |
| Reference images storage | **Object storage**: Same backend as generated images. Compressed path stored in `style_anchors.reference_image_path`. Supports iteration (re-upload new ref → re-lock anchor → regenerate). |
| Post-processing aggressiveness | **Light defaults, heavy optionally**: Always do background removal + bounding box + resize. Offer palette locking as a per-asset opt-in after review. |
| Variants/tiers schema | **Flexible per-asset**: Single `style_anchors` table. Multiple anchors per asset are supported (e.g., `creep_01_base`, `creep_01_variant_blue`). Asset ID is hierarchical enough for this. |
| Storage backend abstraction | **Single interface, env-switched**: `StorageBackend` base class, factory function picks implementation from `STORAGE_BACKEND` env var. Clean pluggability. |

---

## 7. Immediate Next Steps (Proposal Approval)

1. ✅ Approval of schema design (normalize? denormalize? versioning strategy?)
2. ✅ Approval of folder structure (too nested? too flat? models vs. ORM location?)
3. ✅ Approval of layer separation (services, storage, UI isolation?)
4. **Then**: Implement models → services → pages → integration tests

