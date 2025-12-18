#!/bin/bash
# Quick start script for the Django development server

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run migrations (in case database is not set up)
python manage.py migrate

# Start the development server
echo "Starting Django development server..."
echo "Open http://localhost:8000 in your browser"
python manage.py runserver
