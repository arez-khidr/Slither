# WSGI server utilities for creating and managing domain-specific servers
import subprocess
import os
import signal

def create_wsgi_server(app, port, workers=4):
    """
    Create a domain-specific WSGI server
    
    Args:
        app: Flask application instance
        port: Port number to run on
        workers: Number of gunicorn workers
        
    Returns:
        int: Process ID of started server
    """
    domain = app.config.get('DOMAIN', 'unknown')
    
    # Generate domain-specific wsgi file
    _create_wsgi_file(domain, port, workers)
    
    # Run the generated wsgi file directly
    wsgi_file_path = f"wsgi/wsgi_{domain}.py"
    process = subprocess.Popen(
        ['python', wsgi_file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True
    )
    
    print(f"WSGI server started for {domain} on port {port} (PID: {process.pid})")
    #Return the pid so that it can be stored for future modification and persistence purposes
    return process.pid

def stop_server_by_pid(pid, domain=None):
    """
    Stop a WSGI server by process ID
    
    Args:
        pid: Process ID to terminate
        domain: Domain name (for logging purposes)
    """
    try:
        # Try graceful termination first
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped server{' for ' + domain if domain else ''} (PID: {pid})")
        return True
    except ProcessLookupError:
        print(f"Process {pid} not found{' for domain ' + domain if domain else ''}")
        return False
    except PermissionError:
        print(f"Permission denied stopping process {pid}")
        return False

def is_server_running(pid):
    """
    Check if a server process is still running
    
    Args:
        pid: Process ID to check
        
    Returns:
        bool: True if process is running, False otherwise
    """
    try:
        # Send signal 0 to check if process exists
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we don't have permission to signal it
        return True

def restart_server(domain):
    """
    Restart a server from existing WSGI file
    
    Args:
        domain: Domain name to restart
        
    Returns:
        int: New process ID, or None if failed
    """
    wsgi_file_path = f"wsgi/wsgi_{domain}.py"
    
    if not os.path.exists(wsgi_file_path):
        print(f"WSGI file not found for domain {domain}")
        return None
    
    process = subprocess.Popen(
        ['python', wsgi_file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True
    )
    
    print(f"Restarted server for {domain} (PID: {process.pid})")
    return process.pid

def delete_wsgi_files(domain):
    """
    Delete WSGI files for a domain
    
    Args:
        domain: Domain name to clean up
    """
    wsgi_file_path = f"wsgi/wsgi_{domain}.py"
    
    if os.path.exists(wsgi_file_path):
        os.remove(wsgi_file_path)
        print(f"Deleted WSGI file for {domain}")

def _create_wsgi_file(domain, port, workers):
    """Create domain-specific wsgi file"""
    os.makedirs("wsgi", exist_ok=True)
    
    wsgi_content = f'''# Import the FlaskApplication class
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask_application import FlaskApplication

# Create a Flask application instance for {domain} domain
flask_app_instance = FlaskApplication('{domain}')
app = flask_app_instance.get_app()

if __name__ == "__main__":
    import sys
    from gunicorn.app.wsgiapp import WSGIApplication
    
    # Set default arguments for Gunicorn
    sys.argv = [
        'gunicorn',
        '--bind', '127.0.0.1:{port}',
        '--workers', '{workers}',
        '--timeout', '30',
        '--max-requests', '1000',
        '--access-logfile', '-',
        '--error-logfile', '-',
        'wsgi_{domain}:app'
    ]
    
    WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]").run()
'''
    
    wsgi_file_path = f"wsgi/wsgi_{domain}.py"
    with open(wsgi_file_path, 'w') as f:
        f.write(wsgi_content) 