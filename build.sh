#!/bin/bash
# Local build script for frontend

echo "Building frontend for deployment..."

# Navigate to frontend directory
cd frontend

# Install dependencies
echo "Installing npm dependencies..."
npm install

# Build the React app
echo "Building React app..."
npm run build

echo "✓ Frontend built successfully to backend/static/"
echo "✓ Ready to commit and push to Railway"
