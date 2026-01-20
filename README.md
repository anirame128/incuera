# Incuera

Session replay analytics platform with AI-powered video analysis. Record user sessions, generate replay videos, and get AI insights.

## Architecture

```
incuera/
├── backend/           # FastAPI + Python backend
├── frontend/          # Next.js admin dashboard
├── ecommerce-demo/    # Demo e-commerce app with SDK integration
└── packages/sdk/      # @incuera/sdk - client recording library
```

## Tech Stack

| Component | Technologies |
|-----------|-------------|
| **Backend** | FastAPI, SQLAlchemy, PostgreSQL (Supabase), ARQ (Redis), Playwright |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui |
| **SDK** | TypeScript, rrweb |
| **AI Analysis** | OpenRouter API (Molmo 2) |
| **Storage** | Supabase Storage |

## Quick Start

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase and Redis credentials

# Run migrations (in Supabase SQL editor)
# Execute files in backend/migrations/ in order

# Start server
uvicorn app.main:app --reload --port 8000

# Start worker (separate terminal)
arq app.workers.config.WorkerSettings
```

### 2. Frontend Setup

```bash
cd frontend/incuera-frontend
npm install
cp .env.local.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

### 3. SDK – Local pack (for ecommerce-demo and dev)

The demo app installs `@incuera/sdk` from a **local tarball** (no symlink). Create it once, then whenever the SDK changes:

```bash
cd packages/sdk
npm run pack:local
# Creates dist-pkg/incuera-sdk-local.tgz
```

### 4. Demo App (Optional)

```bash
# One-time: pack the SDK (see above), then install
cd ecommerce-demo
npm install
cp .env.example .env.local
# Set NEXT_PUBLIC_INCUERA_API_KEY and NEXT_PUBLIC_INCUERA_API_HOST
npm run dev
```

After SDK changes: run `npm run pack:local` in `packages/sdk`, then `npm install` in `ecommerce-demo`.

## Environment Variables

### Backend (.env)

```bash
# Database (Supabase)
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:6543/postgres

# Auth
SECRET_KEY=your-secret-key

# Redis (for job queue)
REDIS_URL=redis://localhost:6379

# Storage (Supabase)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SECRET_KEY=your-service-role-key

# AI Analysis (Optional)
MOLMO_ENABLED=true
MOLMO_API_KEY=sk-or-v1-xxx  # OpenRouter API key
MOLMO_API_MODEL=allenai/molmo-2-8b:free
```

### Frontend (.env.local)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Core Features

### Session Recording
- Integrates rrweb for browser event capture
- Automatic event batching (100 events or 10s interval)
- Minimum 30s session duration filter

### Video Generation
- Headless Playwright renders rrweb replays
- 1280x720 resolution, configurable FPS
- Thumbnail and keyframe extraction
- Uploaded to Supabase Storage

### AI Analysis (Molmo 2)
- Session summary generation
- Interaction heatmaps
- Conversion funnel tracking
- Error event detection
- Action counting

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions/start` | POST | Register session metadata |
| `/api/ingest` | POST | Receive event batches |
| `/api/sessions/end` | POST | Signal session end, trigger video generation |
| `/api/sessions` | GET | List sessions for project |
| `/api/sessions/{id}` | GET | Get session details |
| `/api/sessions/{id}/analysis` | GET | Get AI analysis results |
| `/api/projects` | CRUD | Project management |
| `/api/api-keys` | CRUD | API key management |

## SDK Usage

```typescript
import Incuera from '@incuera/sdk';

const incuera = new Incuera({
  apiKey: 'your-api-key',
  apiHost: 'https://api.incuera.com',
});

// Start recording
incuera.init();

// Identify user (optional)
incuera.identify('user-123', 'user@example.com');

// Stop recording
incuera.stop();
```

## Database Schema

- **users** - Platform users
- **projects** - Tracked websites/apps
- **api_keys** - Authentication keys (hashed)
- **sessions** - Recording sessions with video URLs and analysis
- **events** - rrweb event data (JSONB)

## Deployment

### Backend
- **Railway/Render**: Set env vars, run `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Worker**: Run `arq app.workers.config.WorkerSettings` separately

### Frontend
- **Vercel**: Connect repo, set `NEXT_PUBLIC_API_URL`

## Development

```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Worker
cd backend && arq app.workers.config.WorkerSettings

# Frontend
cd frontend/incuera-frontend && npm run dev

# SDK (when changing packages/sdk): build and pack for local install
cd packages/sdk && npm run pack:local

# Demo (uses @incuera/sdk from packages/sdk/dist-pkg/incuera-sdk-local.tgz)
cd ecommerce-demo && npm install && npm run dev
```

### SDK ↔ app separation

- **Dev**: ecommerce-demo depends on `file:../packages/sdk/dist-pkg/incuera-sdk-local.tgz`. Run `npm run pack:local` in `packages/sdk` after SDK changes, then `npm install` in ecommerce-demo. The tarball is a real install (no symlink).
- **Production**: Publish `@incuera/sdk` to npm (or a private registry), then set `"@incuera/sdk": "^0.1.0"` in the app.

## License

Proprietary
