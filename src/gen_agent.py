# Generates the agent configuration and the agent executable
import json
import subprocess
import os
from typing import List


# TODO: In the future this is where the pre-shared key for encryption will be handled
def gen_agent_config(
    domains: List[str], beacon_timer: int, watchdog_timer: int, agent_folder: str
) -> bool:
    """
    Generates the agent config with the required parameters

    ARGS:
        domains - A List of C2 Server domains
        beacon_timer - Beacon interval timer in seconds
        watchdog_timer - Watchdog timeout in seconds
        agent_folder - the path where the config file should be written

    Returns:
        status - bool of whether the file was written to or not
    """
    agent_config = {
        "domains": domains,
        "beacon_timer": beacon_timer,
        "watchdog_timer": watchdog_timer,
    }

    try:
        # Load URL obfuscation parameters from agent_url_params.json
        url_params_path = "../agent/agent_url_params.json"
        with open(url_params_path, "r") as f:
            url_params = json.load(f)

        # Merge agent config with URL parameters
        complete_config = {**agent_config, **url_params}

        os.makedirs(os.path.dirname(agent_folder), exist_ok=True)
        config_path = os.path.join(agent_folder, "agent_config.json")

        with open(config_path, "w") as f:
            json.dump(complete_config, f, indent=2)

        print(f"Agent config written to {config_path}")

        return True

    except FileNotFoundError:
        print("URL Parameter file was not found")
        return False
    except json.JSONDecodeError:
        print("Invalid JSON in agent/agent_url_params.json")
        return False
    except Exception as e:
        print(f"Error generating config: {e}")
        return False


def gen_agent_executable():
    """
    Takes the current agent_config.json file and generates an agent executable from it
    """
