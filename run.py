"""
Scent Australia Lead Generation AI Backend
Main entry point for the Flask application
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import create_app

app = create_app()

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', '1') == '1'
    
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║     Scent Australia Lead Generation AI Backend               ║
    ║     Running on http://{host}:{port}                          ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host=host, port=port, debug=debug)

