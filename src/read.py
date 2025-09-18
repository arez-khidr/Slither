# File that handles the reading from redis streams and lists
import signal
from datetime import datetime

# TODO: It would be a cool idea to maybe have it such that the user could "merge" any two given streams by adding mor than one domain! 1:Will


def read_live_stream(redis_client, stream_name):
    """
    Read from a Redis stream in real-time and display messages with timestamps

    Args:
        redis_client: Redis client instance
        stream_name: Name of the stream to read from
    """
    # Save the original SIGINT handler and temporarily replace with default
    original_sigint_handler = signal.signal(signal.SIGINT, signal.default_int_handler)

    try:
        last_id = "$"  # Start from new messages only
        while True:
            # Get new messages from the stream
            messages = redis_client.xread({stream_name: last_id}, count=1, block=1000)

            if messages:
                format_message_entries(messages)

    except KeyboardInterrupt:
        print(f"\nStopped listening to broadcast stream '{stream_name}'")
    finally:
        # Restore the original SIGINT handler
        signal.signal(signal.SIGINT, original_sigint_handler)


def read_last_n_entries(redis_client, stream_name, count):
    """
    Read the last n entries from a Redis stream

    Args:
        redis_client: Redis client instance
        stream_name: Name of the stream to read from
        count: Number of recent entries to retrieve
    """
    try:
        # Use XRANGE to get entries in chronological order
        if count == 0:
            # Get all messages from the stream
            messages = redis_client.xrange(stream_name, min="-", max="+")
        else:
            # Get specific number of entries (first n messages)
            messages = redis_client.xrange(stream_name, count=count)

        if not messages:
            print(f"No messages found in stream '{stream_name}'")
            return

        print(f"Last {len(messages)} messages from stream '{stream_name}':")
        print("-" * 50)

        format_message_entries(messages)

    except Exception as e:
        print(f"Error reading from stream '{stream_name}': {e}")


def format_message_entries(messages):
    """
    Formats messages in reverse chronological order

    Args:
        messages: Messages that are output from the redis_stream for either the command results or the agent modification results
    """

    for _, fields in messages:
        command_data = fields[b"command"].decode("utf-8")
        result_data = fields[b"result"].decode("utf-8")
        message_data = f"Command: {command_data} | Result: {result_data}"

        # Decode and format timestamp
        timestamp = float(fields[b"ts"].decode("utf-8"))
        formatted_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

        # Decode domain
        domain = fields[b"domain"].decode("utf-8")

        # Display with formatted timestamp and domain
        print(f"[{formatted_time}] [{domain}] {message_data}")
