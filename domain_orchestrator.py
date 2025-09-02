from flask_application import FlaskApplication
from wsgi_creator import WSGICreator
from nginx_controller import NGINXController
import socket
import subprocess
import os
import shutil
import json
from datetime import datetime
import redis


class DomainOrchestrator:
    """
    Class that handles all of the functions required to generate a new 'domain' including:
    - Generating a new flask app and corresponding index.html
    - Generating a new wsgi server for said flask application
    - Generating adding the routing to the nginx server
    - Updating the nginx server config
    """

    def __init__(
        self,
        domain_storage: str = "domains.json",
        redis_client=redis.Redis(),
        template_folder=None,
        wsgi_folder: str = "wsgi",
        nginx_conf_folder: str = "nginx",
    ):
        """Creates the domain orchestrator object with the following parameters
        Args:
            domainDictionary - dictionary that stores the current status of domains while the application is running
            domain_storage - the file path to the json file that handles saving and persisitence operations
            redis_client - Redis client for Flask applications
            template_folder - Base template folder for Flask applications
            wsgi_folder - Folder where WSGI files are stored"""
        self.domainDictionary = {}
        self.domain_storage = domain_storage
        self.redis_client = redis_client
        self.template_folder = template_folder
        self.wsgi_folder = wsgi_folder
        self.nginx_conf_folder = nginx_conf_folder

        # Create an nginx_controlelr instance
        self.nginx_controller = NGINXController(nginx_conf_path=nginx_conf_folder)

        # Create WSGICreator instance
        self.wsgi_creator = WSGICreator(
            redis_client=self.redis_client,
            template_folder=self.template_folder,
            wsgi_folder=self.wsgi_folder,
        )

    # TODO: Have it such that the user just inputs an entire FQDN and we parse out the other components?? (We parse components for naming purposes)
    # AS what would I do in the isntance of a subdomain 1
    def create_domain(self, domain: str, top_level_domain: str, preferred_port=None):
        """
        Completes all the set up for a provided domain, including the flask application, WSGI server,
        and adding routing to nginx

        Args:
            domain - The name of the domain (ex. google, twitch)
            top_level_domain - The top level domain (ex. .com, .tv)
            preferred_port - Optional preferred port (will find available if not provided or unavailable)

        Returns:
            tuple: (success: bool, port: int, message: str)
        """
        # Check if domain already exists
        if domain in self.domainDictionary:
            print(
                "Domain provided already is in use, shut down the server running that domain or provide a different domain"
            )
            return False

        # Find an available port
        if preferred_port and self.is_port_available(preferred_port, domain):
            port = preferred_port
        else:
            port = self.find_available_port()
            if port is None:
                print("No available ports found")
                return False

        try:
            # Create the flask application corresponding to the domain
            flask_application = FlaskApplication(domain, self.redis_client)
            app = flask_application.get_app()

            # Create a corresponding WSGI server in a new file
            pid = self.wsgi_creator.create_wsgi_server(app, port)

            # Update the nginx.conf file as well in reference
            nginx_controller = self.nginx_controller
            nginx_controller.add_NGINX_path(domain, port)

            # Store the domain information in our domain dictionary if successfull
            self.domainDictionary[domain] = (
                port,
                pid,
                "running",
                datetime.now().isoformat(),
            )

            print(f"Domain '{domain}' created successfully on port {port}")
            self._store_domains()
            return True

        except Exception as e:
            # Clean up on failure
            if domain in self.domainDictionary:
                self.domainDictionary.pop(domain)
            print(f"Failed to create domain '{domain}': {str(e)}")
            return False

    def remove_domain(self, domain):
        """Remove a domain and clean up all associated resources"""
        if domain not in self.domainDictionary:
            print(f"Domain '{domain}' not found")
            return False

        # Get domain information
        port, pid, status, date_created = self.domainDictionary[domain]

        # Stop the WSGI server if running
        if status == "running" and self.wsgi_creator.is_server_running(port):
            self.wsgi_creator.stop_server_by_port(port, domain)

        # Remove nginx configuration
        nginx_controller = self.nginx_controller
        nginx_controller.remove_nginx_path(domain)

        # Delete the website template files
        template_dir = f"templates/{domain}"
        if os.path.exists(template_dir):
            # Remove the directory and all its contents
            shutil.rmtree(template_dir)
            print(f"Deleted template directory for {domain}")

        # Delete WSGI files
        self.wsgi_creator.delete_wsgi_files(domain)

        # Remove from domain dictionary
        del self.domainDictionary[domain]

        print(f"Domain '{domain}' removed successfully")
        self._store_domains()
        return True

    def pause_domain(self, domain, resume: bool = False):
        """Stops a server as it is currently running, however the metadata persists so it can be restarted

        Args:
            domain: Domain to be paused
            resume: Bool, set to True if the domain that w are pausing should be given the resume status rather than the paused status"""
        if domain not in self.domainDictionary:
            print(f"Domain '{domain}' not found")
            return False

        port, pid, status, date_created = self.domainDictionary[domain]

        if status != "running":
            print(f"Domain '{domain}' is not currently running (status: {status})")
            return False

        # Stop the server process
        if self.wsgi_creator.is_server_running(port):
            self.wsgi_creator.stop_server_by_port(port, domain)

        if resume:
            self.domainDictionary[domain] = (port, None, "resume", date_created)
        # Upkdate metadata to paused state (keep port reserved, clear PID)
        else:
            self.domainDictionary[domain] = (port, None, "paused", date_created)

        print(f"Domain '{domain}' paused successfully")
        self._store_domains()
        return True

    def resume_domain(self, domain):
        """Restarts a paused domain using existing WSGI file"""
        if domain not in self.domainDictionary:
            print(f"Domain '{domain}' not found")
            return False

        port, pid, status, date_created = self.domainDictionary[domain]

        if status != "paused" and status != "resume":
            print(f"Domain '{domain}' is not paused (status: {status})")
            return False

        # Check if port is still available
        if not self.is_port_available(port, domain):
            print(f"Port {port} is no longer available for domain '{domain}'")
            return False

        # Restart the server using existing WSGI file
        new_pid = self.wsgi_creator.reboot_server(domain, port)

        if new_pid:
            # Update metadata back to running state
            self.domainDictionary[domain] = (port, new_pid, "running", date_created)
            print(f"Domain '{domain}' resumed successfully on port {port}")
            self._store_domains()
            return True
        else:
            print(f"Failed to resume domain '{domain}'")
            # In this case, if we failed to resume on startup, we should also modify the status to paused
            self.domainDictionary[domain] = (port, new_pid, "paused", date_created)
            self._store_domains()
            return False

    def shutdown_domains(self):
        """shutdown all of the current running domains and store them inside of a json file"""
        # Iterate through all of the domains inside of the domain dictionary
        for domain, (port, pid, status, date_created) in self.domainDictionary.items():
            # Pause the domain if it is not already paused
            if status != "paused":
                self.pause_domain(domain, resume=True)

        # Store the dictionary inside of a json file
        self._store_domains()

        return True

    def startup_domains(self):
        """Can be called by the user to return all of the applications that were previously saved"""
        # TODO: If a process was previously running when it was shutdown, it should also be started up once hte application goes on again
        # Load the domains.json file into a dictionary

        if self._load_domains():
            # Startup all the domains that were previously running on shutdown
            for domain, (
                _,
                _,
                status,
                _,
            ) in self.domainDictionary.items():
                if status == "resume":
                    self.resume_domain(domain)

            return True

        # Otherwise no applications were able to be started up so return false
        return False

    def _load_domains(self):
        """Loads all of the previously stored domains from the domains.json file into the dictionary"""
        try:
            with open(self.domain_storage, "r") as f:
                loaded_data = json.load(f)
                # Convert lists back to tuples for consistency
                self.domainDictionary = {
                    domain: tuple(info) for domain, info in loaded_data.items()
                }
            # print("Domain configuration loaded from domains.json")
            return True
        except FileNotFoundError:
            print("No previous domain configuration found (domains.json not found)")
            return False
        except Exception as e:
            print(f"Error loading domains: {e}")
            return False

    def _store_domains(self):
        """Stores all of the domains in a json for future usage"""
        try:
            with open(self.domain_storage, "w") as f:
                json.dump(self.domainDictionary, f, indent=2)
            print("Domain configuration saved to domains.json")
        except Exception as e:
            print(f"Error saving domains: {e}")

    def is_port_available(self, port, domain=None):
        """
        Check if a port is available by testing both system-wide usage
        and our internal WSGI server tracking

        Args:
            domain (str): Domain that we are currently checking this for.
            port (int): Port number to check

        Returns:
            bool: True if port is available, False otherwise
        """
        # Check if port is already used by our domains
        for existing_domain, (existing_port, _, _, _) in self.domainDictionary.items():
            if existing_port == port:
                # If a different domain is using this port, it's not available
                if not domain or existing_domain != domain:
                    print(
                        f"Port {port} is currently in use by domain '{existing_domain}'"
                    )
                    return False
                # If same domain, continue to bind test below

        # Check if port is available system-wide using socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", port))
                return True
        except OSError:
            print(f"Error encountered while seeing if {port} was available for usage")
            return False

    def find_available_port(self, start_port=8000, max_attempts=100):
        """
        Find an available port starting from start_port

        Args:
            start_port (int): Port to start checking from
            max_attempts (int): Maximum number of ports to check

        Returns:
            int: Available port number, or None if no port found
        """
        for port in range(start_port, start_port + max_attempts):
            if self.is_port_available(port):
                return port
        return None

    # NOTE: This function returns as a dictionary to allow for easier lookup for other functions in main
    # If you want to print this using the print_domains function below, wrap as a list!

    def get_all_domains(self):
        """Get all domains in the dictionary"""
        return self.domainDictionary.copy()

    def get_running_domains(self):
        """Get all domains with running status"""
        return [
            (domain, info)
            for domain, info in self.domainDictionary.items()
            if info[2] == "running"
        ]

    def get_paused_domains(self):
        """Get all domains with paused status"""
        return [
            (domain, info)
            for domain, info in self.domainDictionary.items()
            if info[2] == "paused"
        ]

    def print_domains(self, domains_list):
        """
        Print domain information in a formatted way

        Args:
            domains_list: List of (domain, info) tuples
        """
        if not domains_list:
            print("No domains found.")
            return

        for domain, (port, pid, status, date_created) in domains_list:
            print(f"Domain: {domain}")
            print(f"  Port: {port}")
            print(f"  PID: {pid if pid else 'N/A'}")
            print(f"  Status: {status}")
            print(f"  Created: {date_created}")
            print()  # Empty line for spacing
