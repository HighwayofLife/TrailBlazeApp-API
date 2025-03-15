# Deployment Guide

### Additional Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| PORT | Port for the API server | 8000 | No |
| CORS_ORIGINS | Comma-separated list of allowed origins | * | No |
| SECRET_KEY | Secret key for token encryption | None | Yes (if auth enabled) |
| SCRAPER_SCHEDULE | Cron expression for scraper schedule | 0 0 * * * | No |

### Managing Secrets

For production deployments, use secure methods for managing secrets:

- **Azure**: Use Azure Key Vault
- **AWS**: Use AWS Secrets Manager
- **GCP**: Use Google Secret Manager

Never commit secrets to the repository.

## Database Migration in Production

Before deploying an update that includes database schema changes:

1. **Create and test migrations locally:**

```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

2. **Backup the production database:**

```bash
pg_dump -U username -d trailblaze > backup.sql
```

3. **Apply migrations in production:**

```bash
# When using Docker
docker-compose exec api alembic upgrade head

# When using Kubernetes
kubectl exec -it <pod-name> -- alembic upgrade head

# When using cloud services
# Use the appropriate command or console to run migrations
```

4. **Verify the migration was successful:**

```bash
# When using Docker
docker-compose exec api alembic current

# When using Kubernetes
kubectl exec -it <pod-name> -- alembic current
```

## Continuous Deployment

### GitHub Actions Workflow

Create a `.github/workflows/deploy.yml` file:

```yaml
name: Deploy

on:
  push:
    branches: [ main ]
    
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
          
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run tests
      run: |
        pytest
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    # Add deployment steps based on your platform
    # Example for Azure:
    - name: Azure login
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}
        
    - name: Build and push to ACR
      uses: azure/docker-login@v1
      with:
        login-server: ${{ secrets.REGISTRY_LOGIN_SERVER }}
        username: ${{ secrets.REGISTRY_USERNAME }}
        password: ${{ secrets.REGISTRY_PASSWORD }}
    
    - run: |
        docker build -t ${{ secrets.REGISTRY_LOGIN_SERVER }}/trailblaze-api:${{ github.sha }} .
        docker push ${{ secrets.REGISTRY_LOGIN_SERVER }}/trailblaze-api:${{ github.sha }}
        
    - name: Deploy to Azure Container Apps
      uses: azure/CLI@v1
      with:
        inlineScript: |
          az containerapp update \
            --name trailblaze-api \
            --resource-group trailblaze \
            --image ${{ secrets.REGISTRY_LOGIN_SERVER }}/trailblaze-api:${{ github.sha }}
```

## Security Considerations

### Security Best Practices

1. **TLS/SSL**: Always use HTTPS in production
2. **API Key Management**: Securely store and rotate API keys
3. **Network Security**:
   - Use private networks when possible
   - Implement proper firewall rules
   - Use VPC/VNET for cloud deployments
4. **Container Security**:
   - Use minimal base images
   - Scan images for vulnerabilities
   - Run containers as non-root users

### Setting Up HTTPS

1. **Using Nginx as a Reverse Proxy:**

```nginx
server {
    listen 80;
    server_name api.trailblazeapp.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name api.trailblazeapp.com;
    
    ssl_certificate /etc/letsencrypt/live/api.trailblazeapp.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.trailblazeapp.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

2. **Using Let's Encrypt for SSL Certificates:**

```bash
# Install certbot
apt-get update
apt-get install certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d api.trailblazeapp.com
```

## Monitoring and Logging

### Logging Configuration

Configure logging in your production environment:

```bash
# Set environment variables
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Monitoring Tools

1. **Prometheus and Grafana**:
   - Install Prometheus for metrics collection
   - Set up Grafana dashboards for visualization

2. **Cloud Provider Monitoring**:
   - Azure: Application Insights
   - AWS: CloudWatch
   - GCP: Cloud Monitoring

### Alerting

Set up alerts for:
- High error rates
- Elevated response times
- Low disk space
- High CPU usage

## Rollback Procedures

### Rolling Back a Deployment

1. **Docker Compose Rollback:**

```bash
# Tag your images with version numbers
docker-compose down
docker-compose -f docker-compose.yml -f docker-compose.previous.yml up -d
```

2. **Kubernetes Rollback:**

```bash
kubectl rollout undo deployment/trailblaze-api
```

3. **Cloud Service Rollback:**

```bash
# Azure Container Apps
az containerapp revision list --name trailblaze-api --resource-group trailblaze
az containerapp revision activate --name trailblaze-api --resource-group trailblaze --revision previous-revision-name

# AWS ECS
aws ecs update-service --cluster trailblaze --service trailblaze-api --task-definition previous-task-definition

# Google Cloud Run
gcloud run services update-traffic trailblaze-api --to-revisions=previous-revision=100
```

### Database Rollback

If a migration fails:

1. **Roll back to the previous migration:**

```bash
alembic downgrade -1
```

2. **Restore from backup if necessary:**

```bash
psql -U username -d trailblaze < backup.sql
```

Ensure that the following services are running:
- `db`: PostgreSQL database
- `api`: FastAPI application
- `scraper`: Scraper service
- `manage`: Management tasks