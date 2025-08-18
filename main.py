import cmd
from os.path import join
import redis
import threading
import time
import atexit
import signal
import sys
from domain_orchestrator import DomainOrchestrator

# TODO: Per the Redis docuemntation, once a client is subscribed to a redis stream, it cannot execute any other commmands
# Thereby it might be worthwile to make it such that when attempting to look at the output of a redis stream we generate a new subprocess
# TODO: In the python redis docmentaiton there seems to be only one


class PyWebC2Shell(cmd.Cmd):
    intro = "Welcome to pyWebC2 Interactive Shell. Type help or ? to list commands.\n"
    prompt = "pyWebC2> "

    def __init__(self):
        super().__init__()
        self.dorch = DomainOrchestrator()
        # Redis client to be able to subscribe to the streams that are output
        self.redis_client = redis.Redis()
        self.pubsub = self.redis_client.pubsub()
        self.monitoring = False
        self.monitor_thread = None
        # Reload all of the previously stored applications
        self.dorch.startup_applications()

        # Register cleanup functions for graceful shutdown
        self._register_shutdown_handlers()

    def do_create(self, line):
        """Create a new domain: create <domain_name> [port]"""
        args = line.split()
        if not args:
            print("Usage: create <domain_name> [port]")
            return

        domain_name = args[0]
        port = int(args[1]) if len(args) > 1 else None
        self.dorch.create_domain(domain_name, ".com", port)

    def do_remove(self, line):
        """Remove a domain: remove <domain_name>"""
        if not line.strip():
            print("Usage: remove <domain_name>")
            return

        self.dorch.remove_domain(line.strip())

    def do_list(self, line):
        """List all active domains"""
        print("Active domains:", self.dorch.domainDictionary)

    def do_pause(self, line):
        """Pause a running domain: pause <domain_name>"""
        if not line.strip():
            print("Usage: pause <domain_name>")
            return

        self.dorch.pause_domain(line.strip())

    def do_resume(self, line):
        """Resume a paused domain: resume <domain_name>"""
        if not line.strip():
            print("Usage: resume <domain_name>")
            return

        self.dorch.resume_domain(line.strip())

    def do_exit(self, line):
        """Exit the shell and save all of the items"""
        self.dorch.shutdown_applications()
        return True

    def do_quit(self, line):
        """Exit the shell"""
        self.dorch.shutdown_applications()
        return True

    def do_listen(self, line):
        """listens to a broadcasting redis stream in order to obtain messages"""
        args = line.strip().split()

        # List the available streams to lisen to, these are all active domains that are currently running
        available_streams = [
            domain
            for domain, (
                _,
                _,
                status,
                _,
            ) in self.dorch.domainDictionary.items()
            if status == "running"
        ]

        # Append the all stream to the list of the available streams if more than two streams exist
        if len(available_streams) > 2:
            available_streams.append("all")

        if not args:
            print("Stream that wanted to be monitored was not inputted")
            print("Use listen -l to see a list of the available streams to listen to")
            return

        # Flag that lists all of hte available streams
        if args[0] == "-l":
            if available_streams:
                print("Available streams:")
                print(*available_streams, sep="\n")
                return
            else:
                print(
                    "No active domains. Use 'create <domain>' to create a domain or resume <domain> to resume a previous isntance"
                )
                return

        # Flag that can be used to access the log of a given stream
        if args[0] == "h":
            pass

        # After these checks, it is assumed that the user passed in a domain to check, so:
        if args[0] in available_streams:
            stream_name = args[0]
            print(f"Listening to stream '{stream_name}'. Press Ctrl+C to stop.")

            try:
                last_id = "$"  # Start from new messages only
                while True:
                    # Get new messages from the stream
                    messages = self.redis_client.xread(
                        {stream_name: last_id}, count=1, block=1000
                    )

                    if messages:
                        for stream, msgs in messages:  # type: ignore
                            for msg_id, fields in msgs:
                                message_data = fields[b"message"].decode("utf-8")
                                print(f"[{stream_name}] {message_data}")
                                last_id = msg_id

            except KeyboardInterrupt:
                print(f"\nStopped listening to Redis stream '{stream_name}'")

    # All this below code handles shutdowns in the case of an error or any other keyboard interruption. So that any actively running servers shut off appropriately
    def _register_shutdown_handlers(self):
        """Register handlers to ensure graceful shutdown on various exit scenarios"""
        # Register atexit handler for normal Python exit
        atexit.register(self._cleanup_on_exit)

        # Register signal handlers for abrupt termination
        signal.signal(signal.SIGINT, self._signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, self._signal_handler)  # Termination signal

    def _cleanup_on_exit(self):
        """Cleanup function called on exit"""
        try:
            print("\nPerforming graceful shutdown...")
            self.dorch.shutdown_applications()
            print("Shutdown complete.")
        except Exception as e:
            print(f"Error during shutdown: {e}")

    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        print(f"\nReceived signal {signum}. Shutting down gracefully...")
        self._cleanup_on_exit()
        sys.exit(0)


def main():
    PyWebC2Shell().cmdloop()


if __name__ == "__main__":
    main()
