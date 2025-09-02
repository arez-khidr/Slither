import pytest
import time
import agent
import command
# NOTE: In order for these tests to work, you need to modify your dns resolution to resolve to localhost for the following domains
# running.com
# paused1.com
# paused2.com
# resume.com


class TestAgent:
    ## CHECK IN TESTS # #

    # For the check in there are the following scenarios that should be mocked and tested for:
    # SUCCESS - Commands are available and they can be passed
    # Failure - A timeout exception occurs
    # Failure = a connection error occurs
    # HTTP error occurs - This either is an error OR it simply means that there are no commands avialbale
    # A Request exception occurs

    def test_getting_commands_with_flask_application(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)
        expected_commands = ["echo hello", "echo fart"]

        # Insert commands into the domain
        command.queue_commands(
            domain="testing.com",
            redis_client=fake_redis_client,
            commands=expected_commands,
        )

        # Assert that the commands were added to Redis
        queue_key = "testing.com:pending"
        assert fake_redis_client.llen(queue_key) == 2
        assert fake_redis_client.lindex(queue_key, 0).decode() == expected_commands[1]
        assert fake_redis_client.lindex(queue_key, 1).decode() == expected_commands[0]

        # Have the agent reach out to the domain
        # Time out before the agent checks in
        time.sleep(1)

        commands = agent._check_in()

        assert expected_commands == commands

    def test_getting_and_executing_commands_with_flask_application(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)
        expected_commands = ["echo hello", "echo fart"]
        # \n as stdout include a newline by default, and I don't want to strip for potentially larger, multi-line outputs (ls)
        expected_results = ["hello\n", "fart\n"]

        # Insert commands into the domain
        command.queue_commands(
            domain="testing.com",
            redis_client=fake_redis_client,
            commands=expected_commands,
        )

        # Assert that the commands were added to Redis
        queue_key = "testing.com:pending"
        assert fake_redis_client.llen(queue_key) == 2

        # The order is in reverse here, as for redis lists we push to hte front, and pop out the end in a queue fashion,
        assert fake_redis_client.lindex(queue_key, 0).decode() == expected_commands[1]
        assert fake_redis_client.lindex(queue_key, 1).decode() == expected_commands[0]

        # Have the agent reach out to the domain
        # Time out before the agent checks in
        time.sleep(1)

        commands = agent._check_in()
        assert expected_commands == commands

        results = agent._execute_commands(commands)
        assert expected_results == results

        fake_redis_client.flushall()

    def test_getting_and_executing_commands_with_flask_application_and_sending_result(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)
        expected_commands = ["echo hello", "echo fart"]
        # \n as stdout include a newline by default, and I don't want to strip for potentially larger, multi-line outputs (ls)
        expected_results = ["hello\n", "fart\n"]
        # Insert commands into the domain
        command.queue_commands(
            domain="testing.com",
            redis_client=fake_redis_client,
            commands=expected_commands,
        )

        # Assert that the commands were added to Redis
        queue_key = "testing.com:pending"
        assert fake_redis_client.llen(queue_key) == 2

        # The order is in reverse here, as for redis lists we push to hte front, and pop out the end in a queue fashion,
        assert fake_redis_client.lindex(queue_key, 0).decode() == expected_commands[1]
        assert fake_redis_client.lindex(queue_key, 1).decode() == expected_commands[0]

        # Have the agent reach out to the domain
        # Time out before the agent checks in
        time.sleep(1)

        # Run the beacon chain

        chain_result = agent.execute_beacon_chain()
        assert chain_result is True

        time.sleep(1)
        # Ensure that the commands and their outputs were stored into the redis_stream, meaning they were executed and sent
        stream_key = "testing.com:results"

        # Check stream length - should have 2 entries (one for each command)
        stream_length = fake_redis_client.xlen(stream_key)
        assert stream_length == 2

        # Get all entries from the stream
        entries = fake_redis_client.xrange(stream_key)
        assert len(entries) == 2

        # Extract commands and results from stream entries
        stream_commands = []
        stream_results = []
        for entry_id, fields in entries:
            stream_commands.append(fields[b"command"].decode())
            stream_results.append(fields[b"result"].decode())
            assert fields[b"domain"] == b"testing.com"

        # Verify the commands and results match our expected values
        # Note: Redis lists are FIFO (first in, first out) when using RPOP
        # SException occurred during processing of request from ('127.0.0.1', 59224)Traceback (most recent call last):  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 95, in handle    self.data = self.reader.load()                ~~~~~~~~~~~~~~~~^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 38, in load    array[i] = self.load()               ~~~~~~~~~^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 43, in load    raise ValueError()ValueErrorDuring handling of the above exception, another exception occurred:Traceback (most recent call last):  File "/opt/homebrew/Cellar/python@3.13/3.13.3/Frameworks/Python.framework/Versions/3.13/lib/python3.13/socketserver.py", line 697, in process_request_thread    self.finish_request(request, client_address)    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^  File "/opt/homebrew/Cellar/python@3.13/3.13.3/Frameworks/Python.framework/Versions/3.13/lib/python3.13/socketserver.py", line 362, in finish_request    self.RequestHandlerClass(request, client_address, self)    ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  File "/opt/homebrew/Cellar/python@3.13/3.13.3/Frameworks/Python.framework/Versions/3.13/lib/python3.13/socketserver.py", line 766, in __init__    self.handle()    ~~~~~~~~~~~^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 102, in handle    self.writer.dump(e)    ~~~~~~~~~~~~~~~~^^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 75, in dump    self.writer.write(f"-{value.args[0]}\r\n".encode())                          ~~~~~~~~~~^^^IndexError: tuple index out of range--------------------------------------------------------------------------------Exception occurred during processing of request from ('127.0.0.1', 59227)Traceback (most recent call last):  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 95, in handle    self.data = self.reader.load()                ~~~~~~~~~~~~~~~~^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 38, in load    array[i] = self.load()               ~~~~~~~~~^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 43, in load    raise ValueError()ValueErrorDuring handling of the above exception, another exception occurred:Traceback (most recent call last):  File "/opt/homebrew/Cellar/python@3.13/3.13.3/Frameworks/Python.framework/Versions/3.13/lib/python3.13/socketserver.py", line 697, in process_request_thread    self.finish_request(request, client_address)    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^  File "/opt/homebrew/Cellar/python@3.13/3.13.3/Frameworks/Python.framework/Versions/3.13/lib/python3.13/socketserver.py", line 362, in finish_request    self.RequestHandlerClass(request, client_address, self)    ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  File "/opt/homebrew/Cellar/python@3.13/3.13.3/Frameworks/Python.framework/Versions/3.13/lib/python3.13/socketserver.py", line 766, in __init__    self.handle()    ~~~~~~~~~~~^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 102, in handle    self.writer.dump(e)    ~~~~~~~~~~~~~~~~^^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 75, in dump    self.writer.write(f"-{value.args[0]}\r\n".encode())                          ~~~~~~~~~~^^^IndexError: tuple index out of range--------------------------------------------------------------------------------Exception occurred during processing of request from ('127.0.0.1', 59229)Traceback (most recent call last):  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 95, in handle    self.data = self.reader.load()                ~~~~~~~~~~~~~~~~^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 38, in load    array[i] = self.load()               ~~~~~~~~~^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 43, in load    raise ValueError()ValueErrorDuring handling of the above exception, another exception occurred:Traceback (most recent call last):  File "/opt/homebrew/Cellar/python@3.13/3.13.3/Frameworks/Python.framework/Versions/3.13/lib/python3.13/socketserver.py", line 697, in process_request_thread    self.finish_request(request, client_address)    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^  File "/opt/homebrew/Cellar/python@3.13/3.13.3/Frameworks/Python.framework/Versions/3.13/lib/python3.13/socketserver.py", line 362, in finish_request    self.RequestHandlerClass(request, client_address, self)    ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  File "/opt/homebrew/Cellar/python@3.13/3.13.3/Frameworks/Python.framework/Versions/3.13/lib/python3.13/socketserver.py", line 766, in __init__    self.handle()    ~~~~~~~~~~~^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 102, in handle    self.writer.dump(e)    ~~~~~~~~~~~~~~~~^^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 75, in dump    self.writer.write(f"-{value.args[0]}\r\n".encode())                          ~~~~~~~~~~^^^IndexError: tuple index out of range--------------------------------------------------------------------------------Exception occurred during processing of request from ('127.0.0.1', 59230)Traceback (most recent call last):  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 95, in handle    self.data = self.reader.load()                ~~~~~~~~~~~~~~~~^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 38, in load    array[i] = self.load()               ~~~~~~~~~^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 43, in load    raise ValueError()ValueErrorDuring handling of the above exception, another exception occurred:Traceback (most recent call last):  File "/opt/homebrew/Cellar/python@3.13/3.13.3/Frameworks/Python.framework/Versions/3.13/lib/python3.13/socketserver.py", line 697, in process_request_thread    self.finish_request(request, client_address)    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^  File "/opt/homebrew/Cellar/python@3.13/3.13.3/Frameworks/Python.framework/Versions/3.13/lib/python3.13/socketserver.py", line 362, in finish_request    self.RequestHandlerClass(request, client_address, self)    ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  File "/opt/homebrew/Cellar/python@3.13/3.13.3/Frameworks/Python.framework/Versions/3.13/lib/python3.13/socketserver.py", line 766, in __init__    self.handle()    ~~~~~~~~~~~^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 102, in handle    self.writer.dump(e)    ~~~~~~~~~~~~~~~~^^^  File "/Users/arezkhidr/Desktop/pyWebC2/webC2/lib/python3.13/site-packages/fakeredis/_tcp_server.py", line 75, in dump    self.writer.write(f"-{value.args[0]}\r\n".)
        assert set(stream_commands) == set(expected_commands)
        # Checking the stripped results because fake redis for some reaosn does not accept anything that has a newline character inputted
        expected_results = [result.strip() for result in expected_results]
        assert stream_results == expected_results

        fake_redis_client.flushall()

    def test_getting_and_not_executing_commands_with_flask_application(
        self, agent, fake_dorch, fake_redis_client
    ):
        """
        Tests when commands are received but unable to be properly executed
        """
        fake_dorch.startup_domains()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)

        failing_commands = [
            "invalid-command-that-does-not-exist",
            "ls /nonexistent/directory",
        ]

        # Insert failing commands into the domain
        command.queue_commands(
            domain="testing.com",
            redis_client=fake_redis_client,
            commands=failing_commands,
        )

        # Assert that the commands were added to Redis
        queue_key = "testing.com:pending"
        assert fake_redis_client.llen(queue_key) == 2
        assert fake_redis_client.lindex(queue_key, 0).decode() == failing_commands[1]
        assert fake_redis_client.lindex(queue_key, 1).decode() == failing_commands[0]

        # Have the agent reach out to the domain
        time.sleep(1)

        # Run the beacon chain - commands should be received but execution will fail
        chain_result = agent.execute_beacon_chain()
        assert (
            chain_result is True
        )  # Chain still succeeds, error messages are sent back

        time.sleep(1)
        stream_key = "testing.com:results"

        stream_length = fake_redis_client.xlen(stream_key)
        assert stream_length == 2

        entries = fake_redis_client.xrange(stream_key)
        assert len(entries) == 2

        # Extract commands and results from stream entries
        stream_commands = []
        stream_results = []
        for entry_id, fields in entries:
            stream_commands.append(fields[b"command"].decode())
            stream_results.append(fields[b"result"].decode())
            assert fields[b"domain"] == b"testing.com"

        # Verify the commands match our expected failing commands
        assert set(stream_commands) == set(failing_commands)

        for result in stream_results:
            assert len(result.strip()) > 0  # Should have error output
            assert any(
                error_word in result.lower()
                for error_word in ["not found", "no such", "error"]
            )

        fake_redis_client.flushall()

