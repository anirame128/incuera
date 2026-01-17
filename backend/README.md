# Incuera Backend API

Python FastAPI backend for receiving and storing session replay data from the Incuera SDK.

## Setup

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your Supabase credentials:

```bash
cp .env.example .env
```

**Get your Supabase connection string:**
1. Go to your [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Go to Settings → Database
4. Copy the **Connection Pooling** connection string (recommended for serverless)
   - Use port **6543** for transaction mode (recommended)
   - Or port **5432** for session mode

**Important:** 
- For serverless deployments (Vercel, Railway, etc.), use the **pooler connection** (port 6543)
- For stationary servers (VMs, long-running containers), you can use the direct connection

### 3. Set Up Database

#### Option A: Using Supabase Dashboard (Recommended)

1. Go to [Supabase SQL Editor](https://app.supabase.com/project/_/sql)
2. Run the migration SQL (see `migrations/initial_schema.sql`)

#### Option B: Using Alembic (Advanced)

```bash
# Initialize Alembic (if not already done)
alembic init migrations

# Create a new migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

### 4. Run the Server

**Development:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## API Endpoints

### POST `/api/ingest`
Receives session events from the SDK.

**Headers:**
- `X-API-Key`: Your API key

**Body:**
```json
{
  "sessionId": "session_1234567890_abc123",
  "events": [...],
  "timestamp": 1234567890
}
```

### POST `/api/sessions/start`
Creates a new session record.

**Headers:**
- `X-API-Key`: Your API key

**Body:**
```json
{
  "sessionId": "session_1234567890_abc123",
  "userId": "user_123",
  "userEmail": "user@example.com",
  "metadata": {
    "url": "https://example.com",
    "referrer": "https://google.com",
    "userAgent": "Mozilla/5.0...",
    "screen": {"width": 1920, "height": 1080},
    "viewport": {"width": 1920, "height": 937},
    "timestamp": 1234567890
  }
}
```

## Database Schema

The backend uses the following tables:

- **users**: Website owners
- **projects**: Websites/apps being tracked
- **api_keys**: API keys for authentication
- **sessions**: User sessions
- **events**: rrweb events for each session

### Row Level Security (RLS)

**RLS is enabled on all tables** for security best practices. The backend uses direct database connections with the `postgres` role, which bypasses RLS by default. This means:

- ✅ Your backend API works normally (bypasses RLS)
- ✅ Protection against accidental `anon` key usage
- ✅ Protection if Supabase REST API is accidentally exposed
- ✅ Defense-in-depth security layer

The RLS policies deny all access except for the `service_role`/`postgres` role, ensuring only your backend can access the data.

## Supabase Best Practices

This backend follows Supabase recommendations:

1. **Connection Pooling**: Uses NullPool for serverless deployments
2. **Transaction Mode**: Uses port 6543 for better connection management
3. **Security**: API keys are hashed using SHA-256
4. **Performance**: Bulk inserts for events, indexed queries

## Deployment

### Railway
1. Connect your GitHub repo
2. Set environment variables in Railway dashboard
3. Deploy!

### Render
1. Create a new Web Service
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables

### Vercel (Serverless)
Use the Vercel Python runtime. The connection pooling is essential here.

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black app/
isort app/
```

## Troubleshooting

### Connection Issues
- Make sure you're using the **pooler connection string** for serverless
- Check that your Supabase project is active
- Verify your database password is correct

### API Key Issues
- Ensure API keys are generated and stored in the database
- Check that the `X-API-Key` header is being sent
- Verify the API key hasn't expired
