# backend/setup_project.sh
#!/bin/bash

# checkpoint

# Create virtual environment
python -m venv venv

# Activate virtual environment
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
else
    source venv/Scripts/activate
fi

# Install dependencies
pip install -r requirements.txt

# Create .env file for API key if it doesn't exist
if [ ! -f .env ]; then
    echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
    echo "Please edit the .env file and add your Gemini API key."
fi

# Run migrations
python manage.py makemigrations chat
python manage.py migrate

# Create a superuser for the admin panel
python manage.py createsuperuser --noinput --username admin --email admin@example.com

# Run the server with the Daphne ASGI server to properly handle WebSockets
daphne -p 8000 wikidata_web.asgi:application