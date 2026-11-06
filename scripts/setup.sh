#!/bin/bash
set -e

echo "🚀 Setting up DataScience Assistant"
echo ""

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required"; exit 1; }

echo "✅ Prerequisites check passed"
echo ""

# Check .env file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys"
    exit 0
fi

# Verify API keys are set
if grep -q "your_gemini_api_key_here" .env; then
    echo "⚠️  Please set GEMINI_API_KEY in .env file"
    exit 1
fi

echo "✅ Configuration verified"
echo ""

# Build and start services
echo "🐳 Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Health check
echo ""
echo "🔍 Checking service health..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend health check failed"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Services:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "View logs: docker-compose logs -f"
echo "Stop:      docker-compose down"
