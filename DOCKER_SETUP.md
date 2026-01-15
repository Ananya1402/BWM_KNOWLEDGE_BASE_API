# Docker Setup Guide for BWM Knowledge Base API

## What is OOB (Out Of Box)?
**OOB** means the application works immediately after setup without any additional manual configuration. Just download, run one command, and everything works automatically.

---

## Prerequisites

- **Docker** (version 20.10+)
- **Docker Compose** (version 2.0+)
- **OpenAI API Key** (get from https://platform.openai.com/api-keys)
- Git

**Installation guides:**
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Docker Compose](https://docs.docker.com/compose/install/)

---

## Quick Start (3 Steps)

### Step 1: Clone the Repository
```bash
git clone https://github.com/Ananya1402/BWM_KNOWLEDGE_BASE_API.git
cd BWM_KNOWLEDGE_BASE_API
```

### Step 2: Configure Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# Windows
notepad .env
# macOS/Linux
nano .env
```

**Update these values in `.env`:**
```env
OPENAI_API_KEY=sk-your_actual_key_here
```

### Step 3: Run the Application
```bash
# Start all services (database + API)
docker-compose up -d

# View logs
docker-compose logs -f app
```

**That's it!** Your application is now running. 🎉

---

## Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| API | http://localhost:8000 | Main API endpoint |
| API Documentation | http://localhost:8000/docs | Interactive Swagger UI |
| API Alternative Docs | http://localhost:8000/redoc | ReDoc documentation |
| Health Check | http://localhost:8000/health | Application health status |
| PostgreSQL | localhost:5432 | Database (internal only) |

---

## Environment Variables Explained

Create/edit `.env` file in root directory:

```env
# OpenAI Configuration (REQUIRED)
OPENAI_API_KEY=sk-...your_key...

# Database Configuration (auto-configured in Docker)
# Leave as-is when using docker-compose
DATABASE_URL=postgresql://postgres:postgres@db:5432/rag_kb

# Chroma Vector Database Storage
CHROMA_PERSIST_DIR=./chroma_db

# LLM Model Configuration
LLM_MODEL=gpt-4o                    # GPT-4 Optimized
EMBED_MODEL=text-embedding-3-small  # Embedding model

# Application Settings
ENV=development                       # development or production
DEBUG=False                         # Enable debug mode (not for production)
SQLALCHEMY_ECHO=False              # Log SQL queries

# Optional: Gemini API (if used)
# GEMINI_API_KEY=your_gemini_api_key_here
```

---

## How It Works

### Architecture
```
┌─────────────────────────────────────┐
│     Your Local Machine              │
├─────────────────────────────────────┤
│  Docker Container 1: FastAPI App    │
│  - RAG Application                  │
│  - Alembic Migrations (auto-run)    │
│  - Port: 8000                       │
├─────────────────────────────────────┤
│  Docker Container 2: PostgreSQL DB  │
│  - Persistent Storage               │
│  - Port: 5432 (internal)            │
├─────────────────────────────────────┤
│  Docker Volume: Chroma DB           │
│  - Vector Database Storage          │
│  - Path: ./chroma_db                │
└─────────────────────────────────────┘
```

### Automatic Migrations
When the app container starts, it automatically:
1. Waits for PostgreSQL to be ready
2. Runs Alembic migrations (`alembic upgrade head`)
3. Starts the FastAPI application

**No manual migration commands needed!**

---

## Common Commands

```bash
# Start services in background
docker-compose up -d

# View logs from app container
docker-compose logs -f app

# View logs from database
docker-compose logs -f db

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes database!)
docker-compose down -v

# Rebuild containers after code changes
docker-compose up --build -d

# Execute command in app container
docker-compose exec app bash

# Check database health
docker-compose exec db pg_isready -U postgres

# View all running containers
docker ps

# Remove all stopped containers
docker container prune
```

---

## Troubleshooting

### Application won't start
```bash
# Check logs
docker-compose logs app

# Common cause: Database not ready
# Solution: Wait 10-15 seconds and retry
docker-compose restart app
```

### Database connection errors
```bash
# Check if database is running
docker-compose logs db

# Restart database
docker-compose restart db
```

### Port already in use
```bash
# Find process using port 8000
# macOS/Linux
lsof -i :8000

# Windows
netstat -ano | findstr :8000

# Change ports in docker-compose.yml
# Change "8000:8000" to "8001:8000"
```

### Migrations failed
```bash
# View detailed logs
docker-compose logs app

# Manually run migrations (if needed)
docker-compose exec app alembic upgrade head
```

### Reset everything (⚠️ DELETES DATA)
```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Rebuild from scratch
docker-compose up --build -d
```

---

## For Production Deployment

When deploying to production servers:

1. **Use environment variables for sensitive data:**
   ```bash
   export OPENAI_API_KEY=sk-...
   docker-compose up -d
   ```

2. **Use a remote PostgreSQL database** instead of the docker one:
   ```yaml
   # Update DATABASE_URL in .env
   DATABASE_URL=postgresql://user:password@your-db-host:5432/rag_kb
   
   # Remove 'db' service from docker-compose.yml
   ```

3. **Enable HTTPS:**
   - Use Nginx/Caddy as reverse proxy
   - Configure SSL certificates

4. **Set DEBUG=False** in .env

5. **Use strong passwords** for PostgreSQL

---

## Pushing to Docker Hub

To share your image on Docker Hub:

```bash
# Login to Docker Hub
docker login

# Build and tag image
docker build -t yourusername/bwm-rag-api:latest .

# Push to Docker Hub
docker push yourusername/bwm-rag-api:latest

# Others can now pull and run:
docker pull yourusername/bwm-rag-api:latest
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  yourusername/bwm-rag-api:latest
```

---

## File Structure

```
BWM_KNOWLEDGE_BASE_API/
├── .env                          # Environment variables (your local config)
├── .env.example                  # Template for environment variables
├── docker-compose.yml            # Docker Compose configuration
├── Dockerfile                    # Docker image build instructions
├── DOCKER_SETUP.md              # This file
├── requirements.txt             # Python dependencies
├── alembic/                     # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 20260102_230537_cf50b784129b_create_initial_tables.py
│       └── 20260104_193631_96c6ad85e6be_changed_ids_to_uuid_format.py
├── app/
│   ├── main.py
│   ├── config.py
│   └── ...
├── chroma_db/                   # Vector database (auto-created)
└── uploads/                     # Uploaded files (auto-created)
```

---

## FAQ

**Q: Do I need to install Python locally?**  
A: No! Docker handles everything.

**Q: Can I use a different database?**  
A: Yes, update `DATABASE_URL` in `.env` to point to your database.

**Q: How do I add new Python packages?**  
A: Add to `requirements.txt`, then run `docker-compose up --build -d`

**Q: Can others use this without Docker?**  
A: Yes, they can install locally, but Docker is recommended for consistency.

**Q: Is my data persistent?**  
A: Yes! Database data is stored in a Docker volume. It persists even if containers stop.

**Q: How do I backup my database?**  
```bash
docker-compose exec db pg_dump -U postgres rag_kb > backup.sql
```

**Q: How do I restore from backup?**  
```bash
docker-compose exec -T db psql -U postgres rag_kb < backup.sql
```

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Docker logs: `docker-compose logs -f`
3. Open an issue on GitHub

---

## Summary

| Aspect | Details |
|--------|---------|
| **Setup Time** | ~2 minutes |
| **Manual Config** | Only OPENAI_API_KEY needed |
| **Automatic** | Migrations, database setup, app startup |
| **Data Persistence** | ✅ Yes (Docker volumes) |
| **Development Ready** | ✅ Yes (includes hot-reload setup option) |
| **Production Ready** | ✅ Yes (with SSL + remote DB) |

---

**Made with ❤️ for seamless containerization!**