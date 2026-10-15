"""Local v4 supermarket demo, using the existing ignored Atlas credentials.

For hosted deployments, configure MONGO_URI, MONGO_DB=vibecart_ai and a stable
SECRET_KEY on the server, then serve run_supermarket:app with a WSGI server.
"""
import os
import secrets
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values
from app import create_app


def supermarket_app():
    root = Path(__file__).resolve().parents[2]
    config = dotenv_values(root / 'VibeCart_AI' / 'MongoDB' / '.env')
    uri = os.environ.get('MONGO_URI') or config.get('MONGO_URI')
    if not uri or urlparse(uri).hostname != 'vibecart-ai-free.odqe25w.mongodb.net':
        raise RuntimeError('Configure the authorized VibeCart Atlas URI before starting.')
    return create_app({'DATA_MODE': 'v4', 'MONGO_URI': uri, 'MONGO_DB': 'vibecart_ai',
        'SECRET_KEY': os.environ.get('SECRET_KEY') or secrets.token_hex(32),
        'ENABLE_CHECKOUT': False, 'AI_RECOMMENDATIONS_ENABLED': False, 'AI_SUMMARY_ENABLED': False})


app = supermarket_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
