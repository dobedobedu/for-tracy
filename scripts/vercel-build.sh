#!/bin/bash
set -e

# Build frontend
cd frontend
npm install
npm run build
cd ..

# Create Vercel Build Output API structure
mkdir -p .vercel/output/static
mkdir -p .vercel/output/functions/api/index.func

# Copy static frontend build
cp -r frontend/dist/* .vercel/output/static/

# Copy Python function files
cp -r api .vercel/output/functions/api/index.func/
cp -r server .vercel/output/functions/api/index.func/
cp -r store .vercel/output/functions/api/index.func/
cp -r engine .vercel/output/functions/api/index.func/
cp requirements.txt .vercel/output/functions/api/index.func/
cp pyproject.toml .vercel/output/functions/api/index.func/

# Create function config
cat > .vercel/output/functions/api/index.func/.vc-config.json << 'EOF'
{
  "runtime": "python3.12",
  "handler": "api/index.handler",
  "launcherType": "Python",
  "maxDuration": 30
}
EOF

# Create main config
cat > .vercel/output/config.json << 'EOF'
{
  "version": 3,
  "routes": [
    { "src": "/api/(.*)", "dest": "/api/index" },
    { "src": "/(.*)", "dest": "/index.html" }
  ]
}
EOF

echo "Build output created successfully"
