# Creates a wsgi server that runs for each application so that there are instances that can be easily referenced   
import subprocess
import os

class WSGICreator:

    def __init__(self, app):
        self.flask_app = app
        self.process = None
        self.domain = app.config.get('DOMAIN', 'unknown')
        self.wsgi_file_path = None

    def run_server(self, port, workers=4):
        # Generate domain-specific wsgi file
        self.wsgi_file_path = f"wsgi/wsgi_{self.domain}.py"
        self._create_wsgi_file(port, workers)
        
        # Run gunicorn as subprocess
        cmd = [
            'gunicorn',
            '--bind', f'127.0.0.1:{port}',
            '--workers', str(workers),
            '--timeout', '30',
            '--max-requests', '1000',
            '--access-logfile', '-',
            '--error-logfile', '-',
            f'wsgi.wsgi_{self.domain}:app'
        ]
        
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print(f"WSGI server started for {self.domain} on port {port} (PID: {self.process.pid})")
        return self.process
    
    def _create_wsgi_file(self, port, workers):
        """Create domain-specific wsgi file"""
        os.makedirs("wsgi", exist_ok=True)
        
        wsgi_content = f'''# Import the FlaskApplication class
from flask_application import FlaskApplication

# Create a Flask application instance for {self.domain} domain
flask_app_instance = FlaskApplication('{self.domain}')
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
        'wsgi_{self.domain}:app'
    ]
    
    WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]").run()
'''
        
        with open(self.wsgi_file_path, 'w') as f:
            f.write(wsgi_content)
    
    def stop_server(self):
        """Stop the Gunicorn server"""
        if self.process and self.process.poll() is None:
            print(f"Stopping server for {self.domain} (PID: {self.process.pid})")
            self.process.terminate()
            
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("Force killing server")
                self.process.kill()
                self.process.wait()
            
            print(f"Server for {self.domain} stopped")
        else:
            print(f"Server for {self.domain} is not running")

    def delete_server(self): 
        """Deletes the WSGI server and all of its corresponding files"""

        #If the server is running go ahead and stop it

        if self.isRunning(): 
            self.stop_server 

        else: 
            #Delete the corresponding wsgi file 
            # Delete the reference to the file in the nginx ilfe 
            pass 



    def is_running(self):
        """Check if the server is still running"""
        return self.process and self.process.poll() is None 