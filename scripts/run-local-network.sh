#!/bin/bash
# Run QaAI Legal Assistant accessible on local network
# Allows team members on same WiFi to test the application

set -e

echo "🚀 Starting QaAI Legal Assistant for local network access..."

# Get local IP address
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    LOCAL_IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1 || echo "localhost")
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    LOCAL_IP=$(hostname -I | awk '{print $1}' || echo "localhost")
else
    LOCAL_IP="localhost"
fi

echo "📍 Local IP: $LOCAL_IP"

# Activate virtual environment
source venv_linux/bin/activate

# Start API server on all interfaces
echo "🔧 Starting API server..."
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for API to start
echo "⏳ Waiting for API to start..."
sleep 5

# Check if API started
if ! curl -f http://localhost:8000/health &> /dev/null; then
    echo "❌ Failed to start API"
    kill $API_PID 2>/dev/null || true
    exit 1
fi

echo "✅ API running at http://$LOCAL_IP:8000"

# Start web server
echo "🔧 Starting web server..."
cd apps/web
npm run dev -- --host 0.0.0.0 --port 5173 &
WEB_PID=$!
cd ../..

# Wait for web server
echo "⏳ Waiting for web server to start..."
sleep 5

echo ""
echo "🎉 QaAI Legal Assistant is now running!"
echo ""
echo "📱 Access URLs:"
echo "   Local:   http://localhost:5173"
echo "   Network: http://$LOCAL_IP:5173"
echo ""
echo "👥 Share the Network URL with team members on the same WiFi"
echo ""
echo "ℹ️  Press Ctrl+C to stop both servers"
echo ""

# Wait for user to stop and cleanup
trap 'echo ""; echo "🛑 Stopping servers..."; kill $API_PID $WEB_PID 2>/dev/null || true; exit 0' INT
wait