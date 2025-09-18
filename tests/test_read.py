import pytest
import os
import sys
from unittest.mock import patch, MagicMock
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from read import read_last_n_entries


class TestReadLastNEntries:
    @pytest.mark.unit
    def test_read_last_n_entries_with_messages(self, fake_redis_client, capsys):
        """Test reading last n entries when messages exist"""
        stream_name = "test_domain:results"

        # Add some test messages
        fake_redis_client.xadd(
            stream_name, {"message": "msg1", "ts": str(time.time()), "domain": "test"}
        )
        fake_redis_client.xadd(
            stream_name, {"message": "msg2", "ts": str(time.time()), "domain": "test"}
        )
        fake_redis_client.xadd(
            stream_name, {"message": "msg3", "ts": str(time.time()), "domain": "test"}
        )

        read_last_n_entries(fake_redis_client, stream_name, 2)

        captured = capsys.readouterr()
        assert "Last 2 messages from stream" in captured.out
        assert "-" * 50 in captured.out

    @pytest.mark.unit
    def test_read_last_n_entries_empty_stream(self, fake_redis_client, capsys):
        """Test reading from empty stream"""
        stream_name = "empty_stream"

        read_last_n_entries(fake_redis_client, stream_name, 5)

        captured = capsys.readouterr()
        assert "No messages found in stream 'empty_stream'" in captured.out

    @pytest.mark.unit
    def test_read_last_n_entries_zero_count_no_exception_escapes(
        self, fake_redis_client
    ):
        """Test that function handles zero count error internally"""
        stream_name = "test_domain:results"
        fake_redis_client.xadd(
            stream_name, {"message": "test", "ts": str(time.time()), "domain": "test"}
        )

        # This should not raise any exception to the caller
        try:
            read_last_n_entries(fake_redis_client, stream_name, 0)
            # If we get here, the function handled the error gracefully
            assert True
        except Exception:
            pytest.fail("Error escaped the call")

    @pytest.mark.unit
    def test_read_last_n_entries_negative_count_no_exception_escapes(
        self, fake_redis_client
    ):
        """Test that function handles negative count error internally"""
        stream_name = "test_domain:results"
        fake_redis_client.xadd(
            stream_name, {"message": "test", "ts": str(time.time()), "domain": "test"}
        )

        # This should not raise any exception to the caller
        try:
            read_last_n_entries(fake_redis_client, stream_name, -5)
            # If we get here, the function handled the error gracefully
            assert True
        except Exception:
            pytest.fail("Error escaped the call")

    @pytest.mark.unit
    def test_read_last_n_entries_count_larger_than_available(
        self, fake_redis_client, capsys
    ):
        """Test requesting more messages than available"""
        stream_name = "test_domain:results"
        fake_redis_client.xadd(
            stream_name,
            {"message": "only_message", "ts": str(time.time()), "domain": "test"},
        )

        read_last_n_entries(fake_redis_client, stream_name, 10)

        captured = capsys.readouterr()
        assert "Last 1 messages from stream" in captured.out

    @pytest.mark.unit
    def test_read_last_n_entries_redis_error(self, fake_redis_client, capsys):
        """Test handling Redis errors"""
        stream_name = "test_stream"

        # Mock xrange to raise an exception
        fake_redis_client.xrange = MagicMock(
            side_effect=Exception("Redis connection error")
        )

        read_last_n_entries(fake_redis_client, stream_name, 5)

        captured = capsys.readouterr()
        assert (
            "Error reading from stream 'test_stream': Redis connection error"
            in captured.out
        )

