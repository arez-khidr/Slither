import typer
import typer_shell
from domain_orchestrator import DomainOrchestrator
import redis
from typing_extensions import Annotated

# Libraries that are used to handle graceful shutdowns
import signal
import atexit
import sys


class PyWebC2Shell:
    def __init__(self) -> None:
        # Initialize the typer shell as part of the class
        self.app = typer_shell.make_typer_shell()
        self.dorch = DomainOrchestrator()
        # Redis client to be able to subscribe to the streams that are output
        self.redis_client = redis.Redis()
        self.monitoring = False
        self.monitor_thread = None
        # Reload all of the previously stored applications
        self.dorch.startup_applications()
        # Register the shutdown handlers
        self._register_shutdown_handlers()
        # NOTE: Any new commands that are added MUST be registered here otherwise they will not run
        self.app.command()(self.create)
        self.app.command()(self.remove)
        self.app.command()(self.list)
        self.app.command()(self.pause)
        self.app.command()(self.resume)
        self.app.command()(self.listen)

    def create(
        self,
        domain: str,
        port: Annotated[
            int,
            typer.Option(help="The port number you would like the domain to run from"),
        ] = 8000,
    ):
        """Create a new domain: create <domain> [port]"""
        print("Usage: create <domain> [port]")

        self.dorch.create_domain(domain, ".com", port)

    def remove(self, domain: str):
        """Remove a domain: remove <domain>"""
        self.dorch.remove_domain(domain)

    def list(self):
        """List all active domains"""
        print("Active domains:", self.dorch.domainDictionary)

    def pause(self, domain: str):
        """Pause a running domain: pause <domain>"""
        self.dorch.pause_domain(domain)

    def resume(self, domain: str):
        """Resume a paused domain: resume <domain>"""
        self.dorch.resume_domain(domain)

    def run(self):
        """Runs the typer app as we are calling it inside of a class"""
        self.app()

    def listen(self, domain):
        """listens to a broadcasting redis stream in order to obtain messages for a specific domain"""

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
        #         if len(available_streams) > 2:
        #             available_streams.append("all")
        #
        #         # Flag that lists all of hte available streams
        # #        if args[0] == "-l":
        #             if available_streams:
        #                 print(*available_streams, sep="\n")
        #                 return
        #             else:
        #                 print(
        #                     "No active domains. Use 'create <domain>' to create a domain or resume <domain> to resume a previous isntance"
        #                 )
        #                 return
        #
        #         # Flag that can be used to access the log of a given stream
        #         if args[0] == "-h":
        #             if args[1] in available_streams:
        #                 pass
        #             else:
        #                 print(
        #                     f"{args[1]}, is not a valid stream, Syntax is listen -h <channel>"
        #                 )
        #
        # After these checks, it is assumed that the user passed in a domain to check, so:
        stream_name = domain
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

    ## Functions for the graceful shutting down of the application in the case of an error ##

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
    shell = PyWebC2Shell()
    # Run application for typer shell
    shell.run()


if __name__ == "__main__":
    main()
