# Manages the addition and the removal of routing in the nginx.conf file, as well as reloads
import subprocess
import os


class NGINXController:
    def __init__(self):
        # The path that needs to be called in order to have the application be passed
        # Hardcoded path for macOS Homebrew nginx servers directory
        self.nginx_servers_path = "/opt/homebrew/etc/nginx/servers/"

    def add_NGINX_path(self, domain, port):
        """Creates an individual nginx config file for the domain"""

        # Create nginx directory if it doesn't exist
        os.makedirs("nginx", exist_ok=True)

        # Create the server block content for this domain
        server_block = f"""server {{
    listen 80;
    server_name {domain};
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Client max body size
    client_max_body_size 50M;
    
    # Proxy settings
    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }}
    
    # Static files (if you add any)
    location /static/ {{
        root /Users/arezkhidr/Desktop/pyWebC2;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }}
    
    # Favicon
    location /favicon.ico {{
        access_log off;
        log_not_found off;
        return 404;
    }}
}}
"""

        # Write to individual nginx file for this domain
        nginx_file_path = f"nginx/nginx_{domain}.conf"
        with open(nginx_file_path, "w") as file:
            file.write(server_block)

        print(f"Created nginx config file for '{domain}' on port {port}")

        # Copy to nginx servers directory and reload
        self._copy_nginx_file(domain)
        self._reload_NGINX()

        return True

    def remove_nginx_path(self, domain):
        """Removes nginx config for a specific domain by deleting its files"""
        try:
            # TODO: Add a better print statement such to warn the user for the reason why thye are being asked to input a password
            # Remove local nginx file
            local_file = f"nginx/nginx_{domain}.conf"
            if os.path.exists(local_file):
                os.remove(local_file)
                print(f"Deleted local nginx config: {local_file}")

            # Remove from nginx servers directory
            server_file = f"{self.nginx_servers_path}nginx_{domain}.conf"
            remove_result = subprocess.run(
                ["sudo", "rm", server_file], capture_output=True, text=True
            )

            if remove_result.returncode == 0:
                print(f"Removed nginx config for '{domain}' from servers directory")
                self._reload_NGINX()
                return True
            else:
                print(f"Warning: Could not remove server file: {remove_result.stderr}")
                return False

        except Exception as e:
            print(f"Error removing nginx config for {domain}: {e}")
            return False

    def _copy_nginx_file(self, domain):
        """Copies individual domain nginx file to servers directory"""
        try:
            local_file = f"nginx/nginx_{domain}.conf"
            server_file = f"{self.nginx_servers_path}nginx_{domain}.conf"

            copy_result = subprocess.run(
                ["sudo", "cp", local_file, server_file], capture_output=True, text=True
            )

            if copy_result.returncode == 0:
                print(f"Copied {local_file} to servers directory")
                return True
            else:
                print(f"Failed to copy nginx config: {copy_result.stderr}")
                return False

        except Exception as e:
            print(f"Error copying nginx config: {e}")
            return False

    def _reload_NGINX(self):
        """Reloads the current nginx.conf configuration, this should be called whenever a new instance is added or removed"""
        try:
            # Test nginx configuration first
            test_result = subprocess.run(
                ["sudo", "nginx", "-t"], capture_output=True, text=True
            )

            if test_result.returncode != 0:
                print(f"Nginx config test failed: {test_result.stderr}")
                return False

            # Reload nginx if test passes
            reload_result = subprocess.run(
                ["sudo", "nginx", "-s", "reload"], capture_output=True, text=True
            )

            if reload_result.returncode == 0:
                print("Nginx reloaded successfully")
                return True
            else:
                print(f"Nginx reload failed: {reload_result.stderr}")
                return False

        except Exception as e:
            print(f"Error reloading nginx: {e}")
            return False
