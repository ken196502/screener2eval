#!/bin/bash

# Build and test Docker deployment script for macOS

set -e

echo "🚀 Starting Docker build and deployment..."

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t trading-app:latest .

echo "✅ Docker image built successfully!"

# Stop and remove existing container if running
echo "🛑 Stopping existing container..."
docker stop trading-app 2>/dev/null || true
docker rm trading-app 2>/dev/null || true

# Run the container
echo "🔄 Starting new container..."
docker run -d \
  --name trading-app \
  -p 2611:2611 \
  -v "$(pwd)/demo_trading.db:/app/backend/demo_trading.db" \
  trading-app:latest

echo "⏳ Waiting for container to start..."
sleep 5

# Test the deployment
echo "🧪 Testing deployment..."
if curl -f http://localhost:2611/api/health >/dev/null 2>&1; then
    echo "✅ Health check passed!"
    echo "🌐 Application is running at: http://localhost:2611"
    echo "📊 API documentation available at: http://localhost:2611/docs"
else
    echo "❌ Health check failed!"
    echo "📋 Container logs:"
    docker logs trading-app
    exit 1
fi

echo "🎉 Deployment successful!"
echo ""
echo "📝 Useful commands:"
echo "  View logs: docker logs -f trading-app"
echo "  Stop app:  docker stop trading-app"
echo "  Remove:    docker rm trading-app"