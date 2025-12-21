# DocsVerify - Docker Setup Guide

## Prasyarat

- Docker (v20.10+)
- Docker Compose (v2.0+)

## Quick Start

### 1. Build dan Run dengan Docker Compose

```bash
# Build image
docker-compose build

# Run container
docker-compose up -d

# Check logs
docker-compose logs -f docsverify
```

### 2. Akses Aplikasi

- **API**: http://localhost:8000
- **API Docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8000/redoc

### 3. Test Health Check

```bash
curl http://localhost:8000/
```

## Commands

### Development

```bash
# Jalankan container dengan rebuild
docker-compose up --build

# Stop container
docker-compose down

# View logs
docker-compose logs -f docsverify

# Rebuild image
docker-compose build --no-cache
```

### Production

```bash
# Jalankan di background
docker-compose up -d

# Update dan restart
docker-compose up -d --build

# Stop dan remove
docker-compose down -v
```

## File Uploads

File uploads dapat disimpan di folder `uploads/` di host machine. Folder ini sudah di-mount ke container.

```bash
# Buat folder uploads jika belum ada
mkdir -p uploads
```

## Troubleshooting

### Container fails to start

```bash
# Check logs
docker-compose logs docsverify

# Rebuild image
docker-compose build --no-cache
```

### Port 8000 already in use

Edit `docker-compose.yml` dan ubah port:

```yaml
ports:
  - "8001:8000"  # Host port 8001 ke container port 8000
```

### OCR tidak bekerja

Pastikan tesseract-ocr dan tesseract-ocr-ind sudah ter-install dengan benar:

```bash
# Check inside container
docker-compose exec docsverify apt-get update && apt-get install -y tesseract-ocr
```

## Environment Variables

Buat file `.env` dari template `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` sesuai kebutuhan.

## Advanced Configuration

### Multi-stage Build

Dockerfile menggunakan multi-stage build untuk optimasi ukuran image:
- **Builder stage**: Install dependencies dan compile
- **Final stage**: Hanya runtime dependencies

### Health Check

Container memiliki health check bawaan yang memeriksa endpoint API setiap 30 detik.

```bash
# Check container health
docker-compose ps
```

## Cleanup

```bash
# Remove stopped containers
docker-compose down

# Remove images
docker image rm docsverify_docsverify

# Remove all unused Docker resources
docker system prune -a
```

## Performance Tips

1. **Increase memory**: Edit `docker-compose.yml`
   ```yaml
   environment:
     - PYTHONUNBUFFERED=1
   ```

2. **Use `.env` file**: Store sensitive config outside code

3. **Cache optimization**: `.dockerignore` sudah ter-konfigurasi

## Security

- Jangan expose port 8000 langsung ke production, gunakan reverse proxy (nginx, traefik, dll)
- Ganti `CORS_ORIGINS=["*"]` dengan domain spesifik
- Gunakan environment variables untuk sensitive data
