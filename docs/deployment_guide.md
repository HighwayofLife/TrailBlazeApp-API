# Deployment Guide

## Quick Start

```bash
# Build production images
make build-prod

# Deploy to production
make deploy

# View production logs
make logs-prod
```

## Environment Setup

### Required Variables

```bash
# API Server
API_HOST=api.trailblaze.app
API_PORT=443
API_DEBUG=false

# Database
DB_HOST=db.trailblaze.app
DB_NAME=trailblaze_prod
DB_USER=trailblaze
DB_PASSWORD=secure_password

# Redis
REDIS_HOST=redis.trailblaze.app
REDIS_PORT=6379

# Security
SECRET_KEY=your_secure_key
ALLOWED_ORIGINS=https://trailblaze.app
```

### Managing Secrets

1. Create `.env.prod`:
```bash
make create-env-prod
```

2. Update secrets:
```bash
make update-secrets
```

## Database Management

### Migrations

```bash
# Create migration
make create-migration msg="Add user table"

# Backup database
make backup-db

# Apply migrations
make migrate-prod
```

### Backups

```bash
# Create backup
make backup-db

# List backups
make list-backups

# Restore from backup
make restore-db backup=backup_2024_03_21.sql
```

## Deployment Steps

1. Build production images:
```bash
make build-prod
```

2. Run pre-deployment checks:
```bash
make pre-deploy-check
```

3. Deploy:
```bash
make deploy
```

4. Verify deployment:
```bash
make verify-deploy
```

## Monitoring

### Logs

```bash
# View all logs
make logs-prod

# View specific service
make logs-api
make logs-db
make logs-redis
```

### Health Checks

```bash
# Check all services
make health-check

# Check specific service
make health-api
make health-db
make health-redis
```

## Maintenance

### Common Tasks

```bash
# Restart services
make restart-prod

# Update dependencies
make update-deps

# Clear cache
make clear-cache
```

### Scaling

```bash
# Scale API servers
make scale-api replicas=3

# Scale workers
make scale-workers replicas=2
```

## Rollback Procedures

1. Revert to previous version:
```bash
make rollback
```

2. Verify rollback:
```bash
make verify-deploy
```

3. Monitor logs:
```bash
make logs-prod
```

## Troubleshooting

### Common Issues

1. Database connection:
```bash
make check-db-connection
```

2. Redis connection:
```bash
make check-redis-connection
```

3. API health:
```bash
make health-api
```

### Emergency Procedures

1. Stop all services:
```bash
make stop-prod
```

2. Start essential services:
```bash
make start-essential
```

3. Restore from backup:
```bash
make restore-db backup=latest
```