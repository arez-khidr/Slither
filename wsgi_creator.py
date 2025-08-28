# WSGI server utilities for creating and managing domain-specific servers
import subprocess
import os
import signal


# NOTE: When proceesses are created for the wsgi servers. all utilize the start_new_session = true to create them as separate(and not child processes)
# TODO: Get rid of using pid its not needed at all
def create_wsgi_server(app, port, workers=8):
    """
    Create a domain-specific WSGI server

    Args:
        app: Flask application instance
        port: Port number to run on
        workers: Number of gunicorn workers

    Returns:
        int: Process ID of started server
    """
    domain = app.config.get("DOMAIN", "unknown")

    # Generate domain-specific wsgi file
    _create_wsgi_file(domain, port, workers)

    # Run the generated wsgi file directly
    safe_domain = domain.replace(".", "_")
    wsgi_file_path = f"wsgi/wsgi_{safe_domain}.py"
    process = subprocess.Popen(
        ["python", wsgi_file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    print(f"WSGI server started for {domain} on port {port} (PID: {process.pid})")
    # Return the pid so that it can be stored for future modification and persistence purposes
    return process.pid


def stop_server_by_port(port, domain=None):
    """
    Stop all processes using a specific port

    Args:
        port: Port number to clear
        domain: Domain name (for logging purposes)
    """
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], capture_output=True, text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            killed_count = 0

            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    killed_count += 1
                    print(f"Killed process {pid} using port {port}")
                except (ProcessLookupError, ValueError):
                    continue

            if killed_count > 0:
                print(
                    f"Cleared {killed_count} processes from port {port}{' for ' + domain if domain else ''}"
                )
                return True

        print(f"No processes found using port {port}")
        return True

    except FileNotFoundError:
        print("lsof command not found - cannot kill processes by port")
        return False
    except Exception as e:
        print(f"Error stopping processes on port {port}: {e}")
        return False


def is_server_running(port):
    """
    Check if a server is running on the specified port

    Args:
        port: Port number to check

    Returns:
        bool: True if server is running on port, False otherwise
    """
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], capture_output=True, text=True
        )
        print(f"Return code: {result.returncode}")
        print(f"Stdout: '{result.stdout}'")
        print(f"Stdout stripped: '{result.stdout.strip()}'")
        print(f"Final result: {result.returncode == 0 and result.stdout.strip()}")
        return result.returncode == 0 and bool(result.stdout.strip())
    except FileNotFoundError:
        return False
    except Exception:
        return False


def restart_server(domain):
    """
    Restart a server from existing WSGI file

    Args:
        domain: Domain name to restart

    Returns:
        int: New process ID, or None if failed
    """
    safe_domain = domain.replace(".", "_")
    wsgi_file_path = f"wsgi/wsgi_{safe_domain}.py"

    if not os.path.exists(wsgi_file_path):
        print(f"WSGI file not found for domain {domain}")
        return None

    process = subprocess.Popen(
        ["python", wsgi_file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    print(f"Restarted server for {domain} (PID: {process.pid})")
    return process.pid


def delete_wsgi_files(domain):
    """
    Delete WSGI files for a domain

    Args:
        domain: Domain name to clean up
    """
    safe_domain = domain.replace(".", "_")
    wsgi_file_path = f"wsgi/wsgi_{safe_domain}.py"

    if os.path.exists(wsgi_file_path):
        os.remove(wsgi_file_path)
        print(f"Deleted WSGI file for {domain}")


def _create_wsgi_file(domain, port, workers):
    """Create domain-specific wsgi file"""
    os.makedirs("wsgi", exist_ok=True)

    safe_domain = domain.replace(".", "_")

    wsgi_content = f"""# Import the FlaskApplication class
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
        '--timeout', '10',
        '--max-requests', '1000',
        '--access-logfile', '-',
        '--error-logfile', '-',
        'wsgi_{safe_domain}:app'
    ]
    
    WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]").run()
"""

    wsgi_file_path = f"wsgi/wsgi_{safe_domain}.py"
    with open(wsgi_file_path, "w") as f:
        f.write(wsgi_content)
