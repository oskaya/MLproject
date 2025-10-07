# Guard Vision V2 - Docker Deployment Guide

## Quick Start

### 1. Setup Environment
```bash
# Copy environment template
cp .env.example .env

# Edit the .env file with your actual values
nano .env
```

### 2. Required Environment Variables
```bash
# GitHub OAuth (Required)
GITHUB_CLIENT_ID=your-github-oauth-client-id
GITHUB_CLIENT_SECRET=your-github-oauth-client-secret

# Security
SECRET_KEY=your-super-secret-production-key

# Authorization
ALLOWED_GITHUB_USERS=user1,user2,user3
ALLOWED_GITHUB_ORG=your-organization
```

### 3. Start Services
```bash
# Start ML API and Web Application
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Start Camera (Separate Process)
```bash
# In a separate terminal or as a service
python camera_app.py
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   ML API        │    │   Web App        │    │   Camera App    │
│   (Container)   │    │   (Container)    │    │   (Script)      │
│   Port: 8000    │◄───┤   Port: 5000     │◄───┤   External      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Management Commands

```bash
# Build and start
docker-compose up --build -d

# Stop services
docker-compose down

# View logs
docker-compose logs web-app
docker-compose logs ml-api

# Restart web app only
docker-compose restart web-app

# Update and restart
git pull
docker-compose up --build -d
```

## Production Deployment

### 1. Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. SSL Certificate (Let's Encrypt)
```bash
sudo certbot --nginx -d your-domain.com
```

### 3. Systemd Service (for camera_app.py)
```ini
[Unit]
Description=Guard Vision V2 Camera Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/mlproject2
ExecStart=/path/to/python camera_app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Container Issues
```bash
# Check container status
docker ps -a

# View container logs
docker logs guard-vision-web
docker logs guard-vision-ml

# Access container shell
docker exec -it guard-vision-web bash
```

### Network Issues
```bash
# Check network connectivity
docker network ls
docker network inspect mlproject2_guard-vision-network
```

### ML API Health Check
```bash
curl http://localhost:8000/health
```

### Web App Health Check
```bash
curl http://localhost:5000/api/camera/status
```