# Import the FlaskApplication class
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask_application import FlaskApplication

# Create a Flask application instance for localhost2 domain
flask_app_instance = FlaskApplication('localhost2')
app = flask_app_instance.get_app()

if __name__ == "__main__":
    import sys
    from gunicorn.app.wsgiapp import WSGIApplication
    
    # Set default arguments for Gunicorn
    sys.argv = [
        'gunicorn',
        '--bind', '127.0.0.1:8001',
        '--workers', '4',
        '--timeout', '30',
        '--max-requests', '1000',
        '--access-logfile', '-',
        '--error-logfile', '-',
        'wsgi_localhost2:app'
    ]
    
    WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]").run()
