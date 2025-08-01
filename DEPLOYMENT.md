# QaAI Legal Assistant Deployment Guide

This guide covers multiple deployment options for the QaAI Legal Assistant system.

## Prerequisites

1. **API Keys Required:**
   - OpenAI API key (for GPT models)
   - Anthropic API key (for Claude models)

2. **GitHub Repository:**
   - Create a new repository at https://github.com/new
   - Repository name: `qaai-legal-assistant`
   - Make it public
   - Don't initialize with README (we have our own)

## Quick Deployment Options

### Option 1: Railway (Recommended - Free Tier Available)

1. **Connect to Railway:**
   - Go to https://railway.app
   - Sign up/login with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your `qaai-legal-assistant` repository

2. **Configure Environment Variables:**
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   PORT=8000
   ENVIRONMENT=production
   DATABASE_URL=sqlite:///./data/qaai.db
   ```

3. **Deploy:**
   - Railway will automatically detect the `railway.json` config
   - Build and deployment happen automatically
   - Your app will be available at: `https://your-app-name.up.railway.app`

### Option 2: Render (Free Tier Available)

1. **Connect to Render:**
   - Go to https://render.com
   - Sign up/login with GitHub
   - Click "New" → "Web Service"
   - Connect your GitHub repository

2. **Configure:**
   - Name: `qaai-legal-assistant`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python -m uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT`

3. **Environment Variables:**
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   PYTHONPATH=/opt/render/project/src
   ENVIRONMENT=production
   DATABASE_URL=sqlite:///./data/qaai.db
   ```

### Option 3: Fly.io

1. **Install Fly CLI:**
   ```bash
   # macOS
   brew install flyctl
   
   # Linux/Windows - see https://fly.io/docs/getting-started/installing-flyctl/
   ```

2. **Deploy:**
   ```bash
   fly auth login
   fly launch --no-deploy
   fly secrets set OPENAI_API_KEY=your_key_here ANTHROPIC_API_KEY=your_key_here
   fly deploy
   ```

### Option 4: Docker + Cloud Platform

1. **Build Docker Image:**
   ```bash
   docker build -t qaai-legal-assistant .
   ```

2. **Run Locally:**
   ```bash
   docker run -p 8000:8000 \
     -e OPENAI_API_KEY=your_key_here \
     -e ANTHROPIC_API_KEY=your_key_here \
     qaai-legal-assistant
   ```

3. **Deploy to Cloud:**
   - Push to Docker Hub, AWS ECR, or Google Container Registry
   - Deploy to AWS ECS, Google Cloud Run, or Azure Container Instances

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT models |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude models |
| `PORT` | No | Port to run on (default: 8000) |
| `ENVIRONMENT` | No | Environment (development/production) |
| `DATABASE_URL` | No | SQLite database path |
| `LOG_LEVEL` | No | Logging level (INFO/DEBUG/ERROR) |
| `CORS_ORIGINS` | No | Allowed CORS origins |

## Health Check

Once deployed, verify your application is running:

```bash
curl https://your-deployment-url/health
```

Should return:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "models_available": "7/7"
}
```

## API Documentation

Your deployed API will have interactive documentation at:
- Swagger UI: `https://your-deployment-url/docs`
- ReDoc: `https://your-deployment-url/redoc`

## Testing the Deployment

1. **Basic Health Check:**
   ```bash
   curl https://your-deployment-url/health
   ```

2. **Test Assistant API:**
   ```bash
   curl -X POST "https://your-deployment-url/api/assistant/query-sync" \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "What is DIFC employment law?",
       "mode": "assist",
       "knowledge": {
         "jurisdiction": "DIFC"
       }
     }'
   ```

## Sharing with Colleagues

Once deployed, share these links with your colleagues:

1. **Main Application:** `https://your-deployment-url`
2. **API Documentation:** `https://your-deployment-url/docs`
3. **Health Status:** `https://your-deployment-url/health`

## Troubleshooting

### Common Issues:

1. **Build Failures:**
   - Check that all dependencies are in `requirements.txt`
   - Verify Python version compatibility (3.9+)

2. **Runtime Errors:**
   - Check environment variables are set correctly
   - Verify API keys are valid and have sufficient credits

3. **Performance Issues:**
   - Consider upgrading to paid tier for better resources
   - Monitor memory usage (may need optimization for free tiers)

### Logs:

Check deployment logs in your platform's dashboard:
- Railway: Project → Deployments → View Logs
- Render: Service → Logs
- Fly.io: `fly logs`

## Next Steps

1. **Custom Domain:** Configure a custom domain in your platform's settings
2. **SSL/HTTPS:** Automatically provided by most platforms
3. **Monitoring:** Set up monitoring and alerting
4. **Scaling:** Upgrade to paid plans for production workloads

## Production Considerations

For production deployments, consider:

1. **Database:** Upgrade to PostgreSQL for better performance
2. **File Storage:** Use cloud storage (AWS S3, Google Cloud Storage)
3. **Caching:** Add Redis for session management
4. **Load Balancing:** Multiple instances for high availability
5. **Monitoring:** Application performance monitoring (APM)
6. **Security:** Rate limiting, API authentication
7. **Backup:** Regular database and file backups