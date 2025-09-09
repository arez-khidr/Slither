# Import the FlaskApplication class
import sys
import os
import redis
sys.path.append('/Users/arezkhidr/Desktop/pyWebC2')
from flask_application import FlaskApplication

# Create Redis client using same connection info as parent
redis_client = redis.Redis(host='localhost', port=6379)

# Create a Flask application instance for localhost2 domain
flask_app_instance = FlaskApplication('localhost2', redis_client, 'None')
app = flask_app_instance.get_app()

if __name__ == "__main__":
    import sys
    from gunicorn.app.wsgiapp import WSGIApplication
    
    # Set default arguments for Gunicorn
    sys.argv = [
        'gunicorn',
        '--bind', '127.0.0.1:8003',
        '--workers', '8',
        '--timeout', '10',
        '--max-requests', '1000',
        '--access-logfile', '-',
        '--error-logfile', '-',
        'wsgi_localhost2:app'
    ]
    
    WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]").run()
