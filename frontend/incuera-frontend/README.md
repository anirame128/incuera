# Incuera Dashboard

Admin dashboard for managing Incuera projects, API keys, and viewing session data.

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.local.example .env.local
   ```
   
   Edit `.env.local` and set:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

4. **Access the dashboard:**
   - Open http://localhost:3000 (or the port shown in terminal)
   - Login with test credentials: `test@incuera.com` / `testpassword123`

## Features

- **Login/Authentication**: Simple email/password login
- **Projects Dashboard**: View all your projects
- **API Key Management**: Create and manage API keys for each project
- **Session Viewing**: View recorded sessions (coming soon)

## Backend Requirements

Make sure the backend API is running on `http://localhost:8000` before using the dashboard.

## Development

The dashboard uses:
- Next.js 16 (App Router)
- TypeScript
- Tailwind CSS
- Client-side routing and API routes
