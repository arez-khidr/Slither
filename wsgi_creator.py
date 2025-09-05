# WSGI server utilities for creating and managing domain-specific servers
import subprocess
import os
import signal


class WSGICreator:
    def __init__(self, redis_client, template_folder=None, wsgi_folder: str = "wsgi"):
        self.redis_client = redis_client
        self.template_folder = template_folder
        self.wsgi_folder = wsgi_folder

    def create_wsgi_server(self, app, port, workers=8):
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
        self._create_wsgi_file(domain, port, workers)

        # Run the generated wsgi file directly
        safe_domain = domain.replace(".", "_")
        wsgi_file_path = f"{self.wsgi_folder}/wsgi_{safe_domain}.py"
        process = subprocess.Popen(
            ["python", wsgi_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        print(f"WSGI server started for {domain} on port {port} (PID: {process.pid})")
        return process.pid

    def stop_server_by_port(self, port, domain=None):
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

    def is_server_running(self, port):
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
            # print(f"Return code: {result.returncode}")
            # print(f"Stdout: '{result.stdout}'")
            # print(f"Stdout stripped: '{result.stdout.strip()}'")
            # print(f"Final result: {result.returncode == 0 and result.stdout.strip()}")
            return result.returncode == 0 and bool(result.stdout.strip())
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def reboot_server(self, domain, port):
        """
        Reboot a server from existing WSGI file

        Args
            domain: Domain name to restart

        Returns:
            int: New process ID, or None if failed
        """
        safe_domain = domain.replace(".", "_")
        wsgi_file_path = f"{self.wsgi_folder}/wsgi_{safe_domain}.py"

        if not os.path.exists(wsgi_file_path):
            print(f"WSGI file not found for domain {domain}")
            return None
        if self.is_server_running(port):
            print("Server is currently running, cannot reboot a running server")
            return None

        # NOTE: Start start_new_session here is true to ensure separation of the parent and the child processes!
        process = subprocess.Popen(
            ["python", wsgi_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        print(f"Restarted server for {domain} (PID: {process.pid})")
        return process.pid

    def delete_wsgi_files(self, domain):
        """
        Delete WSGI files for a domain

        Args:
            domain: Domain name to clean up
        """
        safe_domain = domain.replace(".", "_")
        wsgi_file_path = f"{self.wsgi_folder}/wsgi_{safe_domain}.py"

        if os.path.exists(wsgi_file_path):
            os.remove(wsgi_file_path)
            print(f"Deleted WSGI file for {domain}")

    def _create_wsgi_file(self, domain, port, workers=8):
        """Create domain-specific wsgi file, this function also creates the Flask Application that is associated with a given wsgi:
        Args:
            domain - the associated domain with the wsgi server and the flask application
            port - the associated port with the wsgi server
            workers - the amount of workers that handle this domain"""

        os.makedirs(self.wsgi_folder, exist_ok=True)

        safe_domain = domain.replace(".", "_")

        # Get redis connection info from the current client
        redis_host = getattr(
            self.redis_client.connection_pool, "connection_kwargs", {}
        ).get("host", "localhost")
        redis_port = getattr(
            self.redis_client.connection_pool, "connection_kwargs", {}
        ).get("port", 6379)

        print(f"This is the redis_host {redis_host}")
        print(f"This is the redis_port {redis_port} ")

        # Get absolute path to project directory this is needed during testing so the flask_application class can be found
        project_dir = os.path.dirname(os.path.abspath(__file__))

        wsgi_content = f"""# Import the FlaskApplication class
import sys
import os
import redis
sys.path.append('{project_dir}')
from flask_application import FlaskApplication

# Create Redis client using same connection info as parent
redis_client = redis.Redis(host='{redis_host}', port={redis_port})

# Create a Flask application instance for {domain} domain
flask_app_instance = FlaskApplication('{domain}', redis_client, '{self.template_folder}')
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

        wsgi_file_path = f"{self.wsgi_folder}/wsgi_{safe_domain}.py"
        with open(wsgi_file_path, "w") as f:
            f.write(wsgi_content)
