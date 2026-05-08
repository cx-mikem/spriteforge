# spriteforge

Manifest-driven asset pipeline for 2D games. Generate, review, process, and package sprite assets into game-engine-ready atlases.

## Features

- **Manifest-driven**: Single source of truth for what assets your game needs
- **AI generation**: Generate assets from prompts using ChatGPT's DALL-E 3
- **Human approval gates**: Review and approve before assets enter the pipeline
- **Post-processing**: Automatic background removal, alignment, and resizing
- **Atlas packing**: Sprites packed into game-ready sheet + JSON manifests
- **Cost tracking**: See how much you're spending on generation
- **Reproducibility**: Same inputs always produce same outputs
- **Portable**: Runs in Docker anywhere—local, Replit, Fly.io, Railway, etc.

## Quick Start

### 1. Clone and Setup

```bash
git clone <repo>
cd spriteforge
cp .env.example .env
# Edit .env: set OPENAI_API_KEY
```

### 2. Run with Docker

```bash
docker-compose up
```

Visit `http://localhost:8501` in your browser.

### 3. Define Assets

1. Go to **Manifest** page
2. Create assets (e.g., `creep_01`, `structure_tower`)
3. Set sprite size and animation type

### 4. Create Style Anchors

1. Go to **Settings** → **Style Anchors**
2. Create a generation recipe with prompts and seed
3. This ensures consistent regeneration

### 5. Generate

1. Go to **Generate** page
2. Trigger batch generation
3. View costs in real-time

### 6. Review & Approve

1. Go to **Review** page
2. Preview generations
3. Approve or reject

### 7. Export

1. Go to **Export** page
2. Download engine-ready atlases (Phaser JSON format)

## Architecture

```
Streamlit UI
    ↓
Pipeline Service (orchestrator)
    ├─ Generation Service (ChatGPT API)
    ├─ Post-Process Service (cleanup, align, resize)
    └─ Atlas Packer (sprite sheet + JSON)
    ↓
Storage Layer (local, S3, Replit)
    ↓
Database (Postgres)
```

## Configuration

All configuration via `.env`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | (required) | Postgres connection |
| `OPENAI_API_KEY` | (required) | ChatGPT API key |
| `STORAGE_BACKEND` | `local` | `local`, `s3`, or `replit` |
| `STORAGE_LOCAL_PATH` | `/data/storage` | Local storage directory |
| `BATCH_SIZE` | `5` | Generations per batch |
| `MAX_RETRY_ATTEMPTS` | `3` | API retries on failure |
| `GENERATION_MODEL` | `dall-e-3` | Model to use |
| `MAX_ATLAS_WIDTH` | `2048` | Max sprite sheet width |
| `MAX_ATLAS_HEIGHT` | `2048` | Max sprite sheet height |

## Development

### Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Run Locally (without Docker)

```bash
# Start Postgres
docker run -d -e POSTGRES_PASSWORD=spriteforge \
  -e POSTGRES_DB=spriteforge -p 5432:5432 postgres:16-alpine

# Set env
export OPENAI_API_KEY=sk-...
export DATABASE_URL=postgresql://spriteforge:spriteforge@localhost:5432/spriteforge

# Run Streamlit
streamlit run app/main.py
```

### Tests

```bash
pytest
```

## Schema

Key tables:

- `assets` - Registry (asset_id, category, sprite size, animation type)
- `style_anchors` - Generation recipes (prompts, seeds, locked state)
- `generations` - ChatGPT outputs (status, image_paths, cost, retries)
- `approvals` - Approved generations
- `processed_assets` - Post-processing results
- `atlases` - Versioned sprite sheets
- `atlas_entries` - Asset positions in atlases

## Storage Backends

### Local (Development)

```
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=/data/storage
```

Stores files in a local directory. Perfect for development.

### S3 (Production)

```
STORAGE_BACKEND=s3
S3_BUCKET=spriteforge-assets
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
S3_ENDPOINT_URL=  # Optional, for Wasabi, Minio, etc.
```

### Replit

Coming soon.

## Output Format

Atlases are exported as:

```
atlases/{category}/{version}.png     # Sprite sheet
atlases/{category}/{version}.json    # Frame metadata
```

JSON format is Phaser-compatible:

```json
{
  "frames": {
    "creep_01": {
      "frame": {"x": 0, "y": 0, "w": 64, "h": 64},
      "spriteSourceSize": {...},
      "sourceSize": {...}
    }
  },
  "meta": {
    "image": "creep/1.0.png",
    "size": {"w": 512, "h": 512}
  }
}
```

## Workflows

### Add a New Asset

1. Manifest: Create asset entry
2. Settings: Create style anchor with prompts
3. Generate: Batch generate for new asset
4. Review: Approve best variant
5. Export: Re-download category bundle

### Regenerate with Improved Prompts

1. Settings: Unlock anchor, update prompt
2. Generate: Batch regenerate
3. Review: Compare against previous version
4. Approve selective updates
5. Atlas packer auto-rebuilds

### Fix One Bad Asset

1. Generate: Single-asset regeneration with adjusted seed
2. Review: Approve replacement
3. Atlas packer rebuilds category

## Roadmap

- [ ] Animation preview (plays frames at configurable FPS)
- [ ] Batch approval actions
- [ ] Cost dashboard
- [ ] Support for multiple export formats (Godot, Unity, custom)
- [ ] Variant management (per-asset color variants, etc.)
- [ ] Reference image uploads for consistent regeneration
- [ ] Multi-user support (v2)

## License

MIT

## Contributing

See issues for contribution opportunities. Start with `good-first-issue` label.

## Support

Open an issue on GitHub.
