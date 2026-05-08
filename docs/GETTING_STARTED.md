# Getting Started with spriteforge

## Foundation Complete ✓

The spriteforge asset pipeline foundation is complete with:

- **Architecture** fully designed and documented (see ARCHITECTURE.md)
- **Database schema** with 8 core tables and relationships
- **Storage abstraction** with pluggable backends (Local, S3, Replit)
- **Core services**: Generation (ChatGPT), PostProcess (cleanup), AtlasPacker (sprite sheets)
- **Streamlit UI** with 6 pages (Manifest, Generate, Review, Gallery, Export, Settings)
- **Docker setup** for easy local and cloud deployment
- **Test suite** covering models, storage, and services

## Quick Start for Development

### 1. Clone the Repo

```bash
git clone <repo>
cd spriteforge
```

### 2. Environment Setup

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...
```

### 3. Run with Docker (Recommended)

```bash
docker-compose up
```

Then visit `http://localhost:8501`.

### 4. Run Locally (Python 3.11+)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Start Postgres (Docker)
docker run -d -e POSTGRES_PASSWORD=spriteforge \
  -e POSTGRES_DB=spriteforge -p 5432:5432 \
  postgres:16-alpine

# Initialize database
python scripts/init_db.py

# Run Streamlit
streamlit run app/main.py
```

## Next Steps

### Immediate (v1 Polish)

1. **Generation Workflow**: Implement `app/pages/01_Generate.py`
   - Batch generation trigger
   - Cost tracking during generation
   - Progress display with real-time updates

2. **Review & Approval**: Implement `app/pages/02_Review.py`
   - Preview gallery of pending generations
   - Side-by-side comparison with previous version
   - Approve/reject/regenerate UI
   - Animation preview at multiple FPS

3. **Gallery (Bestiary)**: Implement `app/pages/03_Gallery.py`
   - Wall view of all approved assets by category
   - Animate at game speed
   - Detect style consistency issues visually

4. **Export**: Implement `app/pages/04_Export.py`
   - Download current atlases
   - Export in Phaser JSON + PNG format
   - Version management (which atlas version to export)

### Testing

Run tests with Docker (cleanest environment):

```bash
docker-compose exec app pytest tests/ -v
```

Or locally:

```bash
pytest tests/ -v
```

Tests cover:
- ORM models and relationships
- Storage backend operations
- Service initialization and interfaces

### Cost Tracking

Implement a cost dashboard in Settings showing:
- Total spend to date
- Spend per category
- Cost per generation
- Trend over time

### Animation Preview

The `AnimationPreview` component will:
- Load atlas PNG + JSON from storage
- Play frames at configurable FPS
- Support 1x/2x/4x zoom
- Preview on representative backgrounds
- Display frame count and timing info

## Database

### Initialize

```bash
python scripts/init_db.py
```

### Check Health

```bash
python scripts/health_check.py
```

### Schema

Run migrations manually:

```bash
# PostgreSQL CLI
psql postgresql://spriteforge:spriteforge@localhost:5432/spriteforge

# View schema
\dt
\d assets
```

## Configuration

Edit `.env`:

| Var | Default | Notes |
|-----|---------|-------|
| `OPENAI_API_KEY` | (required) | ChatGPT API key |
| `STORAGE_BACKEND` | `local` | `local`, `s3`, or `replit` |
| `BATCH_SIZE` | `5` | Generations per batch |
| `MAX_RETRY_ATTEMPTS` | `3` | API retries |
| `BACKGROUND_REMOVAL_ENABLED` | `true` | Requires `rembg` package |

### Optional: Background Removal

Install rembg for background removal:

```bash
pip install rembg
```

If not installed, background removal is skipped gracefully.

## Storage Backends

### Local (Development)

```
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=/data/storage
```

### S3 (Production)

```
STORAGE_BACKEND=s3
S3_BUCKET=spriteforge-assets
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
```

### Replit

Coming soon—placeholder in place.

## Project Structure

```
app/
  pages/           ← Streamlit pages (Manifest, Generate, Review, Gallery, Export, Settings)
  models/          ← SQLAlchemy ORM
  services/        ← Business logic (GenerationService, PostProcessService, AtlasPacker)
  main.py          ← Streamlit entry point

storage/
  base.py          ← Abstract backend interface
  local.py         ← Local filesystem
  s3.py            ← S3-compatible
  replit.py        ← Replit (placeholder)

tests/             ← Unit tests for models, storage, services

scripts/
  init_db.py       ← Initialize database
  health_check.py  ← Health check

docker-compose.yml ← Local dev setup
Dockerfile         ← Container image

ARCHITECTURE.md    ← System design (required reading)
```

## Key Files to Understand

1. **ARCHITECTURE.md** - System design, data flows, schema rationale
2. **app/models/*** - ORM definitions (start here to understand data)
3. **app/services/generation.py** - ChatGPT API wrapper
4. **app/services/post_process.py** - Image cleanup and alignment
5. **app/services/atlas_packer.py** - Sprite sheet generation

## Common Tasks

### Add a New Asset

1. **Manifest page** → Create asset entry
2. **Settings page** → Create style anchor with prompts
3. **Generate page** → Batch generate
4. **Review page** → Approve best candidate
5. **Export page** → Download updated atlas

### Regenerate a Category

1. **Settings** → Unlock anchor, update prompt
2. **Generate** → Batch regenerate category
3. **Review** → Compare and approve selective updates
4. **Atlas rebuilds automatically** when generation is approved

### Debug Generation

Check `/data/storage/generated/` for:
- Raw outputs from ChatGPT API
- Costs and retry logs

## Performance Notes

- Batch generations of 5-20 per API call for efficiency
- Atlas packing is fast (<1s for typical 50-100 assets)
- Post-processing per asset takes 1-2s (depends on image size)

## Troubleshooting

### Database Won't Connect

```bash
python scripts/health_check.py
```

### Streamlit Not Starting

```bash
streamlit run app/main.py --logger.level=debug
```

### Generation Cost Unexpectedly High

Check `GenerationCost` table:

```sql
SELECT asset_id, SUM(cost_usd) FROM generation_costs
JOIN generations ON generation_costs.generation_id = generations.id
GROUP BY asset_id ORDER BY 2 DESC;
```

## Next Milestone

Once the workflow pages are complete:

1. Create CI/CD pipeline (GitHub Actions)
2. Build Docker image and push to registry
3. Deploy to Fly.io / Railway for cloud testing
4. Gather feedback on workflows
5. Plan v1 release

## Questions?

See ARCHITECTURE.md for design decisions.
Open an issue on GitHub.
