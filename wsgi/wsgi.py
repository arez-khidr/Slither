# Import the FlaskApplication class
from flask_application import FlaskApplication

# Create a Flask application instance for localhost domain
flask_app_instance = FlaskApplication('localhost')
app = flask_app_instance.get_app()

if __name__ == "__main__":
    import sys
    from gunicorn.app.wsgiapp import WSGIApplication
    
    # Set default arguments for Gunicorn
    sys.argv = [
        'gunicorn',
        '--bind', '127.0.0.1:8000',
        '--workers', '4',
        '--timeout', '30',
        '--max-requests', '1000',
        '--access-logfile', '-',
        '--error-logfile', '-',
        'wsgi:app'
    ]
    
    WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]").run()