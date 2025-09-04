import pytest
from unittest.mock import Mock, call
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from command import queue_commands, get_queued_commands, queue_agent_modification_commands, get_queued_agent_modification_commands


class TestCommand:
    @pytest.mark.unit
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

    @pytest.mark.unit
    def test_get_queued_commands(self, mocker):
        # Mock the redis client
        mock_redis_client = mocker.Mock()
        mock_redis_client.llen.return_value = 3
        mock_redis_client.rpop.side_effect = ["cd Desktop", "pwd", "ls"]

        commands = get_queued_commands("testing.com", mock_redis_client)

        assert commands == ["cd Desktop", "pwd", "ls"]

    @pytest.mark.unit
    def test_get_queued_commands_commands_empty(self, mocker):
        mock_redis_client = mocker.Mock()
        mock_redis_client.llen.return_value = 0

        commands = get_queued_commands("testing.com", mock_redis_client)

        # Assert that it is an empty lsit, using if statements this will evaluate to None
        assert commands == []

    @pytest.mark.unit
    def test_queue_agent_modification_commands(self, mocker):
        # Mock the redis-client and the lpush
        mock_redis_client = mocker.Mock()
        
        # Mock the functions
        mock_redis_client.lpush.return_value = 1
        
        # Agent modification commands to be inserted
        modification_commands = ["set_beacon_timer:30", "change_mode:l", "set_domain:backup.com"]
        
        # Call the function
        result = queue_agent_modification_commands("testing.com", mock_redis_client, modification_commands)
        
        # Assertion
        assert result is True
        
        mock_redis_client.lpush.assert_has_calls(
            [
                call("testing.com:mod_pending", "set_beacon_timer:30"),
                call("testing.com:mod_pending", "change_mode:l"),
                call("testing.com:mod_pending", "set_domain:backup.com"),
            ]
        )
        
        assert mock_redis_client.lpush.call_count == 3

    @pytest.mark.unit
    def test_get_queued_agent_modification_commands(self, mocker):
        # Mock the redis client
        mock_redis_client = mocker.Mock()
        mock_redis_client.llen.return_value = 3
        mock_redis_client.rpop.side_effect = ["set_domain:backup.com", "change_mode:l", "set_beacon_timer:30"]
        
        commands = get_queued_agent_modification_commands("testing.com", mock_redis_client)
        
        assert commands == ["set_domain:backup.com", "change_mode:l", "set_beacon_timer:30"]

    @pytest.mark.unit
    def test_get_queued_agent_modification_commands_empty(self, mocker):
        mock_redis_client = mocker.Mock()
        mock_redis_client.llen.return_value = 0
        
        commands = get_queued_agent_modification_commands("testing.com", mock_redis_client)
        
        # Assert that it is an empty list
        assert commands == []

    @pytest.mark.unit
    def test_queue_agent_modification_commands_redis_error(self, mocker):
        # Mock redis client that raises RedisError
        mock_redis_client = mocker.Mock()
        mock_redis_client.lpush.side_effect = Exception("Redis connection failed")
        
        modification_commands = ["set_beacon_timer:30"]
        
        result = queue_agent_modification_commands("testing.com", mock_redis_client, modification_commands)
        
        # Should return False on error
        assert result is False

    @pytest.mark.unit
    def test_get_queued_agent_modification_commands_redis_error(self, mocker):
        # Mock redis client that raises error
        mock_redis_client = mocker.Mock()
        mock_redis_client.llen.side_effect = Exception("Redis connection failed")
        
        commands = get_queued_agent_modification_commands("testing.com", mock_redis_client)
        
        # Should return empty list on error
        assert commands == []
