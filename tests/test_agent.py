import pytest
import threading
from time import sleep, time
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

    @pytest.mark.integration
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
        sleep(1)

        commands = agent._check_in()

        assert expected_commands == commands

    @pytest.mark.integration
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
        sleep(1)

        commands = agent._check_in()
        assert expected_commands == commands

        results = agent._execute_commands(commands)
        assert expected_results == results

        fake_redis_client.flushall()

    @pytest.mark.integration
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
        sleep(1)

        # Run the beacon chain

        chain_result = agent.execute_beacon_chain()
        assert chain_result is True

        sleep(1)
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

    @pytest.mark.integration
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

        command.queue_commands(
            domain="testing.com",
            redis_client=fake_redis_client,
            commands=failing_commands,
        )

        queue_key = "testing.com:pending"
        assert fake_redis_client.llen(queue_key) == 2
        assert fake_redis_client.lindex(queue_key, 0).decode() == failing_commands[1]
        assert fake_redis_client.lindex(queue_key, 1).decode() == failing_commands[0]

        sleep(1)

        # Run the beacon chain - commands should be received but execution will fail
        chain_result = agent.execute_beacon_chain()
        assert (
            chain_result is True
        )  # Chain still succeeds, error messages are sent back

        sleep(1)
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

    @pytest.mark.integration
    def test_getting_long_polling_commands_with_flask_application(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()
        agent._set_long_poll()

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
        sleep(1)

        commands = agent._long_poll()

        assert expected_commands == commands

    def test_long_polling_commands_not_available_with_flask_application(
        self, agent, fake_redis_client, fake_dorch
    ):
        agent._set_long_poll()
        fake_dorch.startup_domains()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)

        # Time out before the agent checks in
        sleep(1)
        start = time()
        commands = agent._long_poll()
        end = time()

        # Assert that they waited the default time before hte server cut out connection 10 seconds
        elapsed_time = end - start
        assert elapsed_time == pytest.approx(10, abs=0.5)  # 10 sec +_0.5s
        assert commands is None

    def test_long_polling_commands_not_available_immediately_with_flask_application(
        self, agent, fake_redis_client, fake_dorch
    ):
        fake_dorch.startup_domains()
        agent._set_long_poll()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)
        expected_commands = ["echo hello", "echo fart"]

        def queue_commands_after_delay():
            # Insert commands into the domain
            sleep(4)
            command.queue_commands(
                domain="testing.com",
                redis_client=fake_redis_client,
                commands=expected_commands,
            )

        thread = threading.Thread(target=queue_commands_after_delay, daemon=True)

        # Set a start time:
        start = time()
        # Time out before the agent checks in
        sleep(1)

        thread.start()
        commands = agent._long_poll()

        end = time()
        elapsed_time = end - start
        assert expected_commands == commands
        assert elapsed_time == pytest.approx(5.0, abs=1)  # 5 seconds +- a second

        # Wait for thread to complete with timeout
        thread.join(timeout=1.0)
        if thread.is_alive():
            print("Warning: Thread did not complete in time")

    @pytest.mark.integration
    def test_long_polling_full_execution_one_cycle(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()
        agent._set_long_poll()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)
        expected_commands = ["echo hello", "echo world"]
        expected_results = ["hello\n", "world\n"]

        command.queue_commands(
            domain="testing.com",
            redis_client=fake_redis_client,
            commands=expected_commands,
        )

        queue_key = "testing.com:pending"
        assert fake_redis_client.llen(queue_key) == 2
        assert fake_redis_client.lindex(queue_key, 0).decode() == expected_commands[1]
        assert fake_redis_client.lindex(queue_key, 1).decode() == expected_commands[0]

        sleep(1)

        poll_result = agent.execute_poll_sequence()
        assert poll_result is True

        sleep(1)
        stream_key = "testing.com:results"

        stream_length = fake_redis_client.xlen(stream_key)
        assert stream_length == 2

        entries = fake_redis_client.xrange(stream_key)
        assert len(entries) == 2

        stream_commands = []
        stream_results = []
        for entry_id, fields in entries:
            stream_commands.append(fields[b"command"].decode())
            stream_results.append(fields[b"result"].decode())
            assert fields[b"domain"] == b"testing.com"

        assert set(stream_commands) == set(expected_commands)
        expected_results = [result.strip() for result in expected_results]
        assert stream_results == expected_results

        fake_redis_client.flushall()

    @pytest.mark.integration
    def test_long_polling_full_execution_two_cycle(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()
        agent._set_long_poll()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)

        # First cycle commands
        first_commands = ["echo cycle1", "pwd"]
        first_expected_results = ["cycle1\n", "/Users/arezkhidr/Desktop/pyWebC2\n"]

        # Second cycle commands
        second_commands = ["echo cycle2", "ls"]

        # First execution cycle
        command.queue_commands(
            domain="testing.com",
            redis_client=fake_redis_client,
            commands=first_commands,
        )

        queue_key = "testing.com:pending"
        assert fake_redis_client.llen(queue_key) == 2

        sleep(1)
        poll_result_1 = agent.execute_poll_sequence()
        assert poll_result_1 is True

        # Second execution cycle
        command.queue_commands(
            domain="testing.com",
            redis_client=fake_redis_client,
            commands=second_commands,
        )

        assert fake_redis_client.llen(queue_key) == 2

        sleep(1)
        poll_result_2 = agent.execute_poll_sequence()
        assert poll_result_2 is True

        sleep(1)
        stream_key = "testing.com:results"

        # Should have 4 entries total (2 from each cycle)
        stream_length = fake_redis_client.xlen(stream_key)
        assert stream_length == 4

        entries = fake_redis_client.xrange(stream_key)
        assert len(entries) == 4

        stream_commands = []
        stream_results = []
        for entry_id, fields in entries:
            stream_commands.append(fields[b"command"].decode())
            stream_results.append(fields[b"result"].decode())
            assert fields[b"domain"] == b"testing.com"

        # Verify all commands from both cycles are present
        all_expected_commands = first_commands + second_commands
        assert set(stream_commands) == set(all_expected_commands)

        # Verify first cycle results are present
        first_expected_results = [result.strip() for result in first_expected_results]
        assert any(result == first_expected_results[0] for result in stream_results)

        fake_redis_client.flushall()

    @pytest.mark.integration
    def test_long_polling_with_no_commands_available(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()
        agent._set_long_poll()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)

        sleep(1)
        poll_result = agent.execute_poll_sequence()
        assert poll_result is False

        stream_key = "testing.com:results"
        stream_length = fake_redis_client.xlen(stream_key)
        assert stream_length == 0

    @pytest.mark.integration
    def test_beacon_chain_with_no_commands_available(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()
        agent._set_beacon()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)

        sleep(1)
        beacon_result = agent.execute_beacon_chain()
        assert beacon_result is False

        stream_key = "testing.com:results"
        stream_length = fake_redis_client.xlen(stream_key)
        assert stream_length == 0

    @pytest.mark.integration
    def test_long_polling_with_connection_error(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()
        agent._set_long_poll()
        agent.activeDomain = "nonexistent.domain"

        fake_redis_client.flushall()

        sleep(1)
        poll_result = agent.execute_poll_sequence()
        assert poll_result is False

        stream_key = "testing.com:results"
        stream_length = fake_redis_client.xlen(stream_key)
        assert stream_length == 0

    @pytest.mark.integration
    def test_beacon_chain_with_connection_error(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()
        agent._set_beacon()
        agent.activeDomain = "nonexistent.domain"

        fake_redis_client.flushall()

        sleep(1)
        beacon_result = agent.execute_beacon_chain()
        assert beacon_result is False

        stream_key = "testing.com:results"
        stream_length = fake_redis_client.xlen(stream_key)
        assert stream_length == 0

    @pytest.mark.integration
    def test_long_polling_with_server_down(self, agent, fake_dorch, fake_redis_client):
        fake_dorch.startup_domains()
        agent._set_long_poll()

        fake_redis_client.flushall()
        fake_dorch.shutdown_domains()

        sleep(1)
        poll_result = agent.execute_poll_sequence()
        assert poll_result is False

        stream_key = "testing.com:results"
        stream_length = fake_redis_client.xlen(stream_key)
        assert stream_length == 0

    @pytest.mark.integration
    def test_beacon_chain_with_server_down(self, agent, fake_dorch, fake_redis_client):
        fake_dorch.startup_domains()
        agent._set_beacon()

        fake_redis_client.flushall()
        fake_dorch.shutdown_domains()

        sleep(1)
        beacon_result = agent.execute_beacon_chain()
        assert beacon_result is False

        stream_key = "testing.com:results"
        stream_length = fake_redis_client.xlen(stream_key)
        assert stream_length == 0

    @pytest.mark.integration
    def test_getting_agent_modification_commands_with_flask_application(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)
        expected_modification_commands = [
            "set_beacon_timer:30",
            "change_mode:l",
            "set_domain:backup.com",
        ]

        # Insert agent modification commands into the domain
        command.queue_agent_modification_commands(
            domain="testing.com",
            redis_client=fake_redis_client,
            commands=expected_modification_commands,
        )

        # Assert that the modification commands were added to Redis
        mod_queue_key = "testing.com:mod_pending"
        assert fake_redis_client.llen(mod_queue_key) == 3
        # With lpush + rpop (FIFO): first command pushed is at index 2, last at index 0
        assert (
            fake_redis_client.lindex(mod_queue_key, 2).decode()
            == expected_modification_commands[0]
        )
        assert (
            fake_redis_client.lindex(mod_queue_key, 1).decode()
            == expected_modification_commands[1]
        )
        assert (
            fake_redis_client.lindex(mod_queue_key, 0).decode()
            == expected_modification_commands[2]
        )

        # Have the agent reach out to the domain for modification commands
        sleep(1)

        agent.modification_check = True  # Set modify mode to allow the call
        modification_commands = agent.get_modification_commands()

        assert expected_modification_commands == modification_commands

        fake_redis_client.flushall()

    @pytest.mark.integration
    def test_sending_agent_modification_command_results_with_flask_application(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)

        modification_commands = ["watchdog:5000", "change_mode:l", "kill"]
        command_results = [
            "Watchdog timer set to 5000 seconds",
            "Switched to long-poll mode",
            "Agent terminated",
        ]

        sleep(1)

        result = agent._send_modification_command_results(
            modification_commands, command_results
        )
        assert result is True

        sleep(1)
        stream_key = "testing.com:mod_results"

        stream_length = fake_redis_client.xlen(stream_key)
        assert stream_length == 3

        entries = fake_redis_client.xrange(stream_key)
        assert len(entries) == 3

        stream_commands = []
        stream_results = []
        for entry_id, fields in entries:
            stream_commands.append(fields[b"command"].decode())
            stream_results.append(fields[b"result"].decode())
            assert fields[b"domain"] == b"testing.com"

        assert set(stream_commands) == set(modification_commands)
        assert set(stream_results) == set(command_results)

        fake_redis_client.flushall()

    @pytest.mark.integration
    def test_agent_modification_commands_are_detected_and_executed_during_beacon(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)

        regular_commands = ["echo hello", "echo world"]
        modification_commands = ["watchdog:3000", "change_mode:l"]

        # Queue regular execution commands and agent modification commands
        command.queue_commands(
            domain="testing.com",
            redis_client=fake_redis_client,
            commands=regular_commands,
        )

        command.queue_agent_modification_commands(
            domain="testing.com",
            redis_client=fake_redis_client,
            commands=modification_commands,
        )

        sleep(1)

        # Execute beacon chain - should process regular commands and detect modification flag
        beacon_result = agent.execute_beacon_chain()
        assert beacon_result is True

        # Verify modification flag was detected
        assert agent.is_modify() is True

        # Process the modification commands
        mod_result = agent.apply_modification_commands()
        assert mod_result is not None

        # Verify agent state changes from modification commands
        assert agent.watchdog_timer == 3000
        assert agent.mode == "l"

        # Verify modification check is reset to false after processing
        assert agent.is_modify() is False

        sleep(1)

        # Check regular command results were stored
        regular_stream_key = "testing.com:results"
        regular_stream_length = fake_redis_client.xlen(regular_stream_key)
        assert regular_stream_length == 2

        # Check modification command results were sent to flask application
        mod_stream_key = "testing.com:mod_results"
        mod_stream_length = fake_redis_client.xlen(mod_stream_key)
        assert mod_stream_length == 2

        fake_redis_client.flushall()

    @pytest.mark.integration
    def test_agent_modification_commands_are_detected_and_executed_during_long_polling(
        self, agent, fake_dorch, fake_redis_client
    ):
        fake_dorch.startup_domains()
        agent._set_long_poll()

        fake_redis_client.flushall()
        running_domains = fake_dorch.get_running_domains()
        assert any(domain == "testing.com" for domain, _ in running_domains)

        regular_commands = ["echo test", "pwd"]
        modification_commands = ["beacon:45", "domain_add:backup.example.com"]

        # Queue regular execution commands and agent modification commands
        command.queue_commands(
            domain="testing.com",
            redis_client=fake_redis_client,
            commands=regular_commands,
        )

        command.queue_agent_modification_commands(
            domain="testing.com",
            redis_client=fake_redis_client,
            commands=modification_commands,
        )

        sleep(1)

        # Execute poll sequence - should process regular commands and detect modification flag
        poll_result = agent.execute_poll_sequence()
        assert poll_result is True

        # Verify modification flag was detected
        assert agent.is_modify() is True

        # Process the modification commands
        mod_result = agent.apply_modification_commands()
        assert mod_result is not None

        # Verify agent state changes from modification commands
        assert agent.beacon_inter == 45
        assert "backup.example.com" in agent.domains

        # Verify modification check is reset to false after processing
        assert agent.is_modify() is False

        sleep(1)

        # Check regular command results were stored
        regular_stream_key = "testing.com:results"
        regular_stream_length = fake_redis_client.xlen(regular_stream_key)
        assert regular_stream_length == 2

        # Check modification command results were sent to flask application
        mod_stream_key = "testing.com:mod_results"
        mod_stream_length = fake_redis_client.xlen(mod_stream_key)
        assert mod_stream_length == 2

        fake_redis_client.flushall()

    ##TESTING AGENT MODIFICATION COMMANDS ##
    @pytest.mark.unit
    def test_parse_modification_commands_valid_strings(self, agent):
        """Test _parse_modification_commands parsing logic only"""

        unparsed_commands = [
            "set_beacon_timer:120",
            "watchdog:5000",
            "kill",
            "change_mode:l",
            "domain_add:test.example.com",
        ]

        parsed_commands = agent._parse_modification_commands(unparsed_commands)

        expected_parsed = [
            ("set_beacon_timer", "120"),
            ("watchdog", "5000"),
            ("kill", None),
            ("change_mode", "l"),
            ("domain_add", "test.example.com"),
        ]

        assert len(parsed_commands) == 5

    @pytest.mark.unit
    def test_parse_modification_commands_valid_strings_bad_formatting(self, agent):
        """Test _parse_modification_commands parsing logic only"""

        unparsed_commands = [
            "set_beacon_timer :   120  ",
            "   watchdog:5000  ",
            "kill",
            "change_mode : l",
            "domain_add:test.example.com",
        ]

        parsed_commands = agent._parse_modification_commands(unparsed_commands)

        expected_parsed = [
            ("set_beacon_timer", "120"),
            ("watchdog", "5000"),
            ("kill", None),
            ("change_mode", "l"),
            ("domain_add", "test.example.com"),
        ]

        assert len(parsed_commands) == 5
        assert parsed_commands == expected_parsed

    @pytest.mark.unit
    def test_handle_modification_command_with_valid_commands(self, agent):
        result = agent._handle_modification_command("watchdog", "5000")
        assert result == "Watchdog timer set to 5000 seconds"
        assert agent.watchdog_timer == 5000

        result = agent._handle_modification_command("domain_add", "new.example.com")
        assert result == "Domain 'new.example.com' added successfully"
        assert "new.example.com" in agent.domains

        result = agent._handle_modification_command("beacon", "120")
        assert result == "Beacon interval set to 120 seconds"
        assert agent.beacon_inter == 120

        result = agent._handle_modification_command("change_mode", "l")
        assert result == "Switched to long-poll mode"
        assert agent.mode == "l"

        if "testing.com" not in agent.domains:
            agent.domains.append("testing.com")
        result = agent._handle_modification_command("domain_active", "testing.com")
        assert result == "Active domain set to testing.com"
        assert agent.activeDomain == "testing.com"

        agent.domains.append("temp.example.com")
        result = agent._handle_modification_command("domain_remove", "temp.example.com")
        assert result == "Removed domain: temp.example.com"
        assert "temp.example.com" not in agent.domains

        result = agent._handle_modification_command("kill", None)
        assert result == "Agent terminated"
        assert agent.stayAlive is False

    @pytest.mark.unit
    def test_handle_modification_command_with_invalid_commands(self, agent):
        results = []

        try:
            agent._handle_modification_command("invalid_command", "value")
        except Exception as e:
            results.append(str(e))

        try:
            agent._handle_modification_command("nonexistent", "test")
        except Exception as e:
            results.append(str(e))

        try:
            agent._handle_modification_command("", "value")
        except Exception as e:
            results.append(str(e))

        try:
            agent._handle_modification_command("watchdog", "invalid")
        except Exception as e:
            results.append(str(e))

        try:
            agent._handle_modification_command("beacon", "-5")
        except Exception as e:
            results.append(str(e))

        try:
            agent._handle_modification_command("change_mode", "x")
        except Exception as e:
            results.append(str(e))

        try:
            agent._handle_modification_command("domain_add", "")
        except Exception as e:
            results.append(str(e))

        try:
            agent._handle_modification_command("domain_active", "nonexistent.com")
        except Exception as e:
            results.append(str(e))

        assert len(results) == 8
        assert all(isinstance(result, str) for result in results)
        assert "Unknown modification command: invalid_command" in results[0]
        assert "Unknown modification command: nonexistent" in results[1]
        assert "Unknown modification command: " in results[2]
