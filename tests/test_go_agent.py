import pytest
import threading
from time import sleep, time
import command
import subprocess
import os


class TestGoAgent:
    # NOTE: All of the tests below test that agents repsonse in the test_agent.go file.
    # Ensuring that the server recieved the proper communications is validated here.
    @pytest.mark.integration
    def test_check_in(self, fake_dorch, fake_redis_client):
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

        sleep(1)

        # Assert that the output from the go commands is true
        result = subprocess.run(
            [
                "go",
                "test",
                "-tags=integration",
                "-run",
                "TestAgentIntegrationTestSuite/TestBeaconIn",
            ],
            cwd=os.path.join(os.path.dirname(__file__), "..", "agent"),
            capture_output=True,
            text=True,
        )
        # Not calling assert directly as we want to get the output
        # Printing os we can cee the return value
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")

        assert result.returncode == 0
