import pytest
import os
from unittest.mock import Mock, patch, mock_open, MagicMock
import sys

from redis.commands.core import DataAccessCommands

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import time
import command
import agent
from domain_orchestrator import DomainOrchestrator
from threading import Thread
import fakeredis
import redis
import socket
# NOTE: In order for these tests to work, you need to modify your dns resolution to resolve to localhost for the following domains
# running.com
# paused1.com
# paused2.com
# resume.com


def get_free_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class TestAgent:
    @pytest.fixture
    def agent(self):
        """Creates an agent to be used with the tests"""
        return agent.Agent(domains=["testing.com"])

    ## CHECK IN TESTS # #

    # For the check in there are the following scenarios that should be mocked and tested for:
    # SUCCESS - Commands are available and they can be passed
    # Failure - A timeout exception occurs
    # Failure = a connection error occurs
    # HTTP error occurs - This either is an error OR it simply means that there are no commands avialbale
    # A Request exception occurs
    #
    # The following fake redis cleint runs on a server, this is the default for any testing that is done
    @pytest.fixture
    def fake_redis_client(request):
        server_port = get_free_port()
        server_address = ("127.0.0.1", server_port)
        server = fakeredis.TcpFakeServer(
            server_address=server_address, server_type="redis"
        )
        t = Thread(target=server.serve_forever, daemon=True)
        t.start()
        redis_client = redis.Redis(host=server_address[0], port=server_address[1])
        yield redis_client
        # Shutdown steps - daemon thread will clean up automatically
        server.shutdown()

    @pytest.fixture
    def fake_dorch(self, tmp_path, fake_redis_client):
        # Create a domain orchestrator to manage the application
        # Create a fake domains.json as well located ina temporary storage

        domain_storage = os.path.join(tmp_path, "domains.json")
        fake_dorch = DomainOrchestrator(
            domain_storage=domain_storage, redis_client=fake_redis_client
        )
        # Initialize the fake domains for the domain dictionary
        # fake_dorch.domainDictionary = {
        #     "testing.com": (49152, 123, "resume", "2024-01-01"),
        # }
        fake_dorch.create_domain(
            "testing.com", top_level_domain="", preferred_port=49152
        )
        return fake_dorch

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

        # Clean up the applications
        fake_dorch.shutdown_domains()

    def test_getting_and_executing_commands_with_flask_application(self):
        pass

    def test_getting_and_not_executing_commands_with_flask_application(self):
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--full-trace"])
