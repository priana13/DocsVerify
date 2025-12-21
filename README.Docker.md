# Docker Setup untuk DocsVerify

## 📋 Daftar File Docker yang Dibuat

| File | Deskripsi |
|------|-----------|
| `Dockerfile` | Multi-stage build untuk production-ready image |
| `docker-compose.yml` | Development & basic production setup |
| `docker-compose.prod.yml` | Advanced production setup dengan resource limits |
| `.dockerignore` | Files yang dikecualikan dari Docker build |
| `.env.example` | Template environment variables |
| `Makefile` | Convenient commands untuk Docker operations |
| `DOCKER_SETUP.md` | Detailed setup guide |

## 🚀 Quick Start

### 1. Clone Repository
```bash
cd /home/priana/Data/Project/DocsVerify
```

### 2. Build Docker Image
```bash
# Menggunakan Makefile (recommended)
make build

# Atau menggunakan docker-compose langsung
docker-compose build
```

### 3. Run Container
```bash
# Menggunakan Makefile
make up

# Atau menggunakan docker-compose
docker-compose up -d
```

### 4. Verify Container Berjalan
```bash
# Check status
make status

# View logs
make logs-f

# Test API
make test
```

### 5. Akses Aplikasi
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📚 Makefile Commands

```bash
make help          # Tampilkan semua commands
make build         # Build image
make up            # Start container
make down          # Stop container
make logs          # View logs (last 100 lines)
make logs-f        # Follow logs (realtime)
make restart       # Restart container
make test          # Test API health
make shell         # Access container shell
make clean         # Remove all Docker resources
make rebuild       # Rebuild from scratch
make status        # Show container status
make docs          # Show documentation URLs
```

## 🔧 Configuration

### Environment Variables

Create `.env` dari template:

```bash
cp .env.example .env
```

Edit `.env` sesuai kebutuhan:

```env
LOG_LEVEL=debug
API_TITLE=Akta Name Validation API
API_VERSION=1.0.0
HOST=0.0.0.0
PORT=8000
```

### Production Setup

Gunakan `docker-compose.prod.yml` untuk production:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Features:
- Resource limits (CPU: 2 cores, Memory: 2GB)
- Environment variables dari `.env`
- Volume mounts untuk uploads dan logs
- Health checks
- Restart policy

## 📁 Volume Mounts

| Host | Container | Deskripsi |
|------|-----------|-----------|
| `./uploads` | `/app/uploads` | File uploads |
| `./logs` | `/app/logs` | Application logs |

Buat folder-folder ini terlebih dahulu:

```bash
mkdir -p uploads logs
```

## 🐳 Dockerfile Details

**Multi-stage Build:**
1. **Builder stage**: Install semua dependencies
2. **Final stage**: Copy hanya yang diperlukan untuk runtime

**Benefits:**
- Image size lebih kecil (~500MB vs 1.5GB)
- Faster deployments
- Security (mengurangi attack surface)

**Installed Packages:**
- `python:3.11-slim` - Base image
- `tesseract-ocr` - OCR engine
- `tesseract-ocr-ind` - Indonesian language support
- `poppler-utils` - PDF processing

## 🏥 Health Check

Container memiliki built-in health check:

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/', timeout=5)"]
  interval: 30s      # Check every 30 seconds
  timeout: 10s       # Timeout after 10 seconds
  retries: 3         # Fail after 3 retries
  start_period: 10s  # Grace period saat startup
```

Check status:

```bash
docker-compose ps
# Lihat STATUS column untuk health status
```

## 🔒 Security Best Practices

1. **Don't expose port langsung**
   - Gunakan reverse proxy (nginx, traefik)
   - Gunakan container orchestration (Docker Swarm, Kubernetes)

2. **Environment variables**
   - Store credentials di `.env`
   - Add `.env` ke `.gitignore`

3. **CORS Configuration**
   - Jangan gunakan `["*"]` di production
   - Specify allowed origins

4. **Network isolation**
   - Gunakan docker networks
   - Restrict port access

## 🐛 Troubleshooting

### Container tidak start
```bash
# Check logs
make logs

# Rebuild
make rebuild
```

### Port 8000 sudah terpakai
```bash
# Check port usage
lsof -i :8000

# Atau ubah port di docker-compose.yml
# ports:
#   - "8001:8000"
```

### OCR tidak bekerja
```bash
# Access container shell
make shell

# Test tesseract
tesseract --version

# Install if missing
apt-get update && apt-get install -y tesseract-ocr
```

### Memory/CPU issues
```bash
# Monitor container resource usage
docker stats docsverify

# Adjust limits di docker-compose.yml atau docker-compose.prod.yml
```

## 📊 Monitoring

### View Logs
```bash
# Last 50 lines
docker-compose logs docsverify -n 50

# Follow realtime
docker-compose logs -f docsverify

# Filter by time
docker-compose logs --since 10m
```

### Resource Usage
```bash
docker stats docsverify
```

### Container Info
```bash
docker-compose ps
docker inspect docsverify_docsverify
```

## 🧹 Cleanup

### Stop container tanpa remove
```bash
docker-compose stop
```

### Stop dan remove
```bash
docker-compose down
```

### Remove everything (including volumes)
```bash
docker-compose down -v
```

### Remove unused images
```bash
docker image prune -a
```

## 📈 Performance Optimization

1. **Image size**: Multi-stage build mengurangi ~70%
2. **Build cache**: `.dockerignore` optimize layer caching
3. **Resource limits**: Prevent runaway processes

## 🔄 CI/CD Integration

### Build image untuk registry
```bash
docker build -t username/docsverify:latest .
docker push username/docsverify:latest
```

### Pull dari registry
```bash
docker pull username/docsverify:latest
docker run -p 8000:8000 username/docsverify:latest
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Tesseract Documentation](https://github.com/UB-Mannheim/tesseract/wiki)

## 💡 Next Steps

1. ✅ Build image: `make build`
2. ✅ Start container: `make up`
3. ✅ Test API: `make test`
4. ✅ View docs: `make docs`
5. ✅ Read logs: `make logs-f`

Happy containerizing! 🎉
