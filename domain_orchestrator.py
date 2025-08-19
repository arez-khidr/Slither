from flask_application import FlaskApplication
from wsgi_creator import (
    create_wsgi_server,
    stop_server_by_pid,
    is_server_running,
    restart_server,
    delete_wsgi_files,
)
from nginx_controller import NGINXController
import socket
import subprocess
import os
import shutil
import json
from datetime import datetime


class DomainOrchestrator:
    """
    Class that handles all of the functions required to generate a new 'domain' including:
    - Generating a new flask app and corresponding index.html
    - Generating a new wsgi server for said flask application
    - Generating adding the routing to the nginx server
    - Updating the nginx server config
    """

    def __init__(self):
        # A dictionary that stores all of the values of any corresponding application. So that on a new loading of the program it can be booted
        # Format is as follows domainDictionary[domain] = [port, pid, status, date created]
        # This is to be written to a json on application close
        self.domainDictionary = {}

    # TODO: Have it such that the user just inputs an entire FQDN and we parse out the other components?? (We parse components for naming purposes)
    # AS what would I do in the isntance of a subdomain 1
    def create_domain(
        self, domain_name: str, top_level_domain: str, preferred_port=None
    ):
        """
        Completes all the set up for a provided domain, including the flask application, WSGI server,
        and adding routing to nginx

        Args:
            domain_name - The name of the domain (ex. google, twitch)
            top_level_domain - The top level domain (ex. .com, .tv)
            preferred_port - Optional preferred port (will find available if not provided or unavailable)

        Returns:
            tuple: (success: bool, port: int, message: str)
        """
        # Check if domain already exists
        if domain_name in self.domainDictionary:
            print(
                "Domain provided already is in use, shut down the server running that domain or provide a different domain"
            )
            return False

        # Find an available port
        if preferred_port and self.is_port_available(preferred_port):
            port = preferred_port
        else:
            port = self.find_available_port()
            if port is None:
                print("No available ports found")
                return False

        try:
            print("Inside of the domain try ")
            # Create the flask application corresponding to the domain
            flask_application = FlaskApplication(domain_name)
            app = flask_application.get_app()

            # Create a corresponding WSGI server in a new file
            pid = create_wsgi_server(app, port)

            # Update the nginx.conf file as well in reference
            nginx_controller = NGINXController()
            nginx_controller.add_NGINX_path(domain_name, port)

            # Store the domain information in our domain dictionary if successfull
            self.domainDictionary[domain_name] = (
                port,
                pid,
                "running",
                datetime.now().isoformat(),
            )

            print(f"Domain '{domain_name}' created successfully on port {port}")
            return True

        except Exception as e:
            # Clean up on failure
            if domain_name in self.domainDictionary:
                self.domainDictionary.pop(domain_name)
            print(f"Failed to create domain '{domain_name}': {str(e)}")
            return False

    def remove_domain(self, domain):
        """Remove a domain and clean up all associated resources"""
        if domain not in self.domainDictionary:
            print(f"Domain '{domain}' not found")
            return False

        # Get domain information
        port, pid, status, date_created = self.domainDictionary[domain]

        # Stop the WSGI server if running
        if status == "running" and is_server_running(pid):
            stop_server_by_pid(pid, domain)

        # Remove nginx configuration
        nginx_controller = NGINXController()
        nginx_controller.remove_nginx_path(domain)

        # Delete the website template files
        template_dir = f"templates/{domain}"
        if os.path.exists(template_dir):
            # Remove the directory and all its contents
            shutil.rmtree(template_dir)
            print(f"Deleted template directory for {domain}")

        # Delete WSGI files
        delete_wsgi_files(domain)

        # Remove from domain dictionary
        del self.domainDictionary[domain]

        print(f"Domain '{domain}' removed successfully")
        return True

    def pause_domain(self, domain):
        """Stops a server as it is currently running, however the metadata persists so it can be restarted"""
        if domain not in self.domainDictionary:
            print(f"Domain '{domain}' not found")
            return False

        port, pid, status, date_created = self.domainDictionary[domain]

        if status != "running":
            print(f"Domain '{domain}' is not currently running (status: {status})")
            return False

        # Stop the server process
        if pid and is_server_running(pid):
            stop_server_by_pid(pid, domain)

        # Update metadata to paused state (keep port reserved, clear PID)
        self.domainDictionary[domain] = (port, None, "paused", date_created)

        print(f"Domain '{domain}' paused successfully")
        return True

    def resume_domain(self, domain):
        """Restarts a paused domain using existing WSGI file"""
        if domain not in self.domainDictionary:
            print(f"Domain '{domain}' not found")
            return False

        port, pid, status, date_created = self.domainDictionary[domain]

        if status != "paused":
            print(f"Domain '{domain}' is not paused (status: {status})")
            return False

        # Check if port is still available
        if not self.is_port_available(port):
            print(f"Port {port} is no longer available for domain '{domain}'")
            return False

        # Restart the server using existing WSGI file
        new_pid = restart_server(domain)

        if new_pid:
            # Update metadata back to running state
            self.domainDictionary[domain] = (port, new_pid, "running", date_created)
            print(f"Domain '{domain}' resumed successfully on port {port}")
            return True
        else:
            print(f"Failed to resume domain '{domain}'")
            return False

    def shutdown_applications(self):
        """shutdown all of the current running applications and store them inside of a json file"""
        # Iterate through all of the domains inside of the domain dictionary
        for domain, (port, pid, status, date_created) in self.domainDictionary.items():
            # Pause the domain if it is not already paused
            if status != "paused":
                self.pause_domain(domain)

        # Store the dictionary inside of a json file
        self._store_domains()

        return True

    def startup_applications(self):
        """Can be called by the user to return all of the applications that were previously saved"""
        # TODO: If a process was previously running when it was shutdown, it should also be started up once hte application goes on again
        # Load the domains.json file into a dictionary
        if self._load_domains():
            return True

        # Otherwise no applications were able to be started up so return false
        return False

    def _load_domains(self):
        """Loads all of the previously stored domains from the domains.json file into the dictionary"""
        try:
            with open("domains.json", "r") as f:
                self.domainDictionary = json.load(f)
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
            with open("domains.json", "w") as f:
                json.dump(self.domainDictionary, f, indent=2)
            print("Domain configuration saved to domains.json")
        except Exception as e:
            print(f"Error saving domains: {e}")

    def is_port_available(self, port):
        """
        Check if a port is available by testing both system-wide usage
        and our internal WSGI server tracking

        Args:
            port (int): Port number to check

        Returns:
            bool: True if port is available, False otherwise
        """
        # First check if we're already using this port internally (connected to a domain, whether in use or not )
        ports_in_use = [port for port, _, _, _ in self.domainDictionary.values()]

        # TODO: Make the message that comes if the port is reserved by the application that is trying to start it a bit clearer
        if port in ports_in_use:
            print(f"{port} is currently in use by the ")

        # Since that passed, now double check if port is available system-wide using socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", port))
                return True
        except OSError:
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
