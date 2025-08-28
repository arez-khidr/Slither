import pytest
import os
import subprocess
import signal
import socket
from unittest.mock import Mock, patch, mock_open, MagicMock
import fakeredis
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import wsgi_creator
from flask_application import FlaskApplication


def get_free_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class TestWSGICreator:
    # Create a fake flask application to use
    @pytest.fixture
    def fake_app(self, tmp_path):
        redis_client = fakeredis.FakeRedis()

        app = FlaskApplication(
            domain="testing.com",
            redis_client=redis_client,
            template_folder=tmp_path,  # tmp_path is a fixture that is used by pytest that automatically handles the teardown of opwerations
        )

        yield app

    # Test the creation of a wsgi server (we assume this will always run with a domain that is not pased beforehand)
    def test_create_wsgi_app(self, fake_app):
        test_port = get_free_port()

        pid = wsgi_creator.create_wsgi_server(
            app=fake_app.get_app(), port=test_port, workers=8
        )

        expected_wsgi_path = "wsgi/wsgi_testing_com.py"
        assert os.path.exists(expected_wsgi_path)

        with open(expected_wsgi_path, "r") as f:
            content = f.read()
            assert "testing.com" in content
            assert f"127.0.0.1:{test_port}" in content
            assert "--workers', '8'" in content
            assert "FlaskApplication" in content

        wsgi_creator.stop_server_by_port(test_port, "testing.com")
        wsgi_creator.delete_wsgi_files("testing.com")

    def test_create_and_teardown_by_port(self, fake_app):
        test_port = get_free_port()

        wsgi_creator.create_wsgi_server(
            app=fake_app.get_app(), port=test_port, workers=4
        )
        wsgi_path = "wsgi/wsgi_testing_com.py"

        assert os.path.exists(wsgi_path)

        result = wsgi_creator.stop_server_by_port(test_port, "testing.com")
        assert result is True

        wsgi_creator.delete_wsgi_files("testing.com")
        assert not os.path.exists(wsgi_path)

    def test_is_server_running(self, fake_app):
        test_port = get_free_port()

        assert wsgi_creator.is_server_running(test_port) is False

        wsgi_creator.create_wsgi_server(
            app=fake_app.get_app(), port=test_port, workers=2
        )

        # Wait longer for gunicorn to fully start and bind to port
        time.sleep(2)

        assert wsgi_creator.is_server_running(test_port) is True

        wsgi_creator.stop_server_by_port(test_port, "testing.com")
        wsgi_creator.delete_wsgi_files("testing.com")

        # Wait longer for gunicorn to shut down
        time.sleep(2)

        assert wsgi_creator.is_server_running(test_port) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
