#!/bin/bash

# Exit if any command fails
set -e

echo "🔍 Checking git status..."
git status

echo "📦 Adding changes..."
git add .

echo "📝 Committing..."
git commit -m "Update Jupyter notebook: daily progress"

echo "🚀 Pushing to GitHub..."
git push

echo "✅ Push completed successfully!"
