#!/bin/bash
set -e

echo "🧪 Running tests for DataScience Assistant"
echo ""

# Backend tests
echo "Testing Backend..."
cd backend
python -m pytest tests/ -v --cov=app --cov-report=term-missing

echo ""
echo "✅ All tests passed!"
