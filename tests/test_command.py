import pytest
from unittest.mock import Mock, call
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from command import queue_commands, get_queued_commands


class TestCommand:
    def test_queue_commands(self, mocker):
        # Mock the redis-client and the lpush
        mock_redis_client = mocker.Mock()

        # Mock the functions
        mock_redis_client.lpush.return_value = 1

        # Commands to be inserted
        commands = ["ls", "pwd", "cd Desktop"]

        # Call the function

        result = queue_commands("testing.com", mock_redis_client, commands)

        # Assertion
        assert result is True

        mock_redis_client.lpush.assert_has_calls(
            [
                call("testing.com:pending", "ls"),
                call("testing.com:pending", "pwd"),
                call("testing.com:pending", "cd Desktop"),
            ]
        )

        assert mock_redis_client.lpush.call_count == 3

    def test_get_queued_commands(self, mocker):
        # Mock the redis client
        mock_redis_client = mocker.Mock()
        mock_redis_client.llen.return_value = 3
        mock_redis_client.rpop.side_effect = ["cd Desktop", "pwd", "ls"]

        commands = get_queued_commands("testing.com", mock_redis_client)

        assert commands == ["cd Desktop", "pwd", "ls"]


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
