#!/bin/bash
# Local sharing script for QaAI Legal Assistant
# Allows internal team to test on local devices via ngrok

set -e

echo "🚀 Setting up QaAI Legal Assistant for local sharing..."

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok not found. Please install it:"
    echo "   macOS: brew install ngrok"
    echo "   Linux: snap install ngrok"
    echo "   Windows: Download from https://ngrok.com/download"
    exit 1
fi

# Check if API is running
if ! curl -f http://localhost:8000/health &> /dev/null; then
    echo "⚠️  API not running on port 8000. Starting it..."
    
    # Activate virtual environment and start API
    source venv_linux/bin/activate
    python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 &
    API_PID=$!
    
    echo "⏳ Waiting for API to start..."
    sleep 5
    
    # Check if API started successfully
    if ! curl -f http://localhost:8000/health &> /dev/null; then
        echo "❌ Failed to start API"
        kill $API_PID 2>/dev/null || true
        exit 1
    fi
    
    echo "✅ API started successfully"
fi

# Start web server if not running
if ! curl -f http://localhost:5173 &> /dev/null; then
    echo "⚠️  Web server not running on port 5173. Starting it..."
    cd apps/web
    npm run dev &
    WEB_PID=$!
    cd ../..
    
    echo "⏳ Waiting for web server to start..."
    sleep 5
    
    echo "✅ Web server started successfully"
fi

# Create ngrok tunnel for the web app
echo "🌐 Creating public tunnel..."
ngrok http 5173 --log stdout > ngrok.log 2>&1 &
NGROK_PID=$!

# Wait for ngrok to start
sleep 3

# Extract the public URL
PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for tunnel in data['tunnels']:
        if tunnel['proto'] == 'https':
            print(tunnel['public_url'])
            break
except:
    pass
")

if [ -z "$PUBLIC_URL" ]; then
    echo "❌ Failed to get ngrok URL. Check ngrok.log for details"
    kill $NGROK_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo "🎉 QaAI Legal Assistant is now accessible at:"
echo "   $PUBLIC_URL"
echo ""
echo "📱 Share this URL with your team for testing on any device"
echo ""
echo "ℹ️  This tunnel will remain active until you press Ctrl+C"
echo "   Logs are saved to ngrok.log"
echo ""

# Wait for user to stop
trap 'echo ""; echo "🛑 Stopping tunnel..."; kill $NGROK_PID 2>/dev/null || true; exit 0' INT
wait $NGROK_PID