# NOTE: This is a newer agent file to handle more advanced beacon and session communication
# At some point the agent_html.py will be reintegrated in some form here
import time
import random
from flask import request
import requests
import time


# Honestly probably the smart thing would be to just copy from what they have in sliver, as those are likely mapped to go use cases
# For now though:

# .css - Key exchange (to be implemented once we add encryption)
# .png - close session messages
# .woff - Gets information on a beacon request
# .js - session messages


# TODO: Make it such that the agent sends using a protobuf, rather than a json, using json for now as honestly it is just easier. I ain't trying to be an attacker
class Agent:
    def __init__(self, domains: list[str], mode: str = "b"):
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

        # NOTE: Other things that can be added here in the future
        # encoders - the type of encoders that are used/available
        # url params - different url paramters to obfuscate

        # Timers that dictate the agents communication and timeouts
        # Inspired by the timeouts that are used in MITRE Caldera

        self.beacon_inter = 60

        # How long the agent waits for an unreachable server before terminating itself
        # If there is a backup domain, the agent will switch to that domain
        self.watchdog_timer = 7000

    def check_in(self):
        """Obtains any available commands if there are any, if no commands are available it fails"""

        # Generate a session
        self.session = requests.Session()

        # TODO: In the future, this request is going to require: encryption, nonce and obfuscation

        try:
            response = self.session.get(f"http://{self.activeDomain}")
            response.raise_for_status()

            # If there was no raise for status, then we know that there are commands

        except requests.exceptions.Timeout:
            print("Request timed out")
        except requests.exceptions.ConnectionError:
            print("Connection error occurred")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

        return None

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
        self.session = "s"
        return


agent = Agent(domains=["localhost2.com"])
while agent.is_alive():
    # Beacon mode
    if agent.is_beacon():
        # Send a check in request

        # Execute commands from that request if any

        # Send results back

        # Agent goes to sleep
        time.sleep(sleep_interval)
