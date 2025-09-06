import pytest
import os
import subprocess
import signal
import socket
from unittest.mock import Mock, patch, mock_open, MagicMock
import fakeredis
import time

from wsgi_creator import WSGICreator
from flask_application import FlaskApplication
from tests.conftest import get_free_port


class TestWSGICreator:

    @pytest.mark.integration
    def test_create_wsgi_app_integration(self, wsgi_creator, fake_app):
        test_port = get_free_port()

        pid = wsgi_creator.create_wsgi_server(
            app=fake_app.get_app(), port=test_port, workers=8
        )

        expected_wsgi_path = f"{wsgi_creator.wsgi_folder}/wsgi_testing_com.py"
        assert os.path.exists(expected_wsgi_path)

        with open(expected_wsgi_path, "r") as f:
            content = f.read()
            assert "testing.com" in content
            assert f"127.0.0.1:{test_port}" in content
            assert "--workers', '8'" in content
            assert "FlaskApplication" in content

        wsgi_creator.stop_server_by_port(test_port, "testing.com")
        wsgi_creator.delete_wsgi_files("testing.com")

    @pytest.mark.integration
    def test_create_and_teardown_by_port_integration(self, wsgi_creator, fake_app):
        test_port = get_free_port()

        wsgi_creator.create_wsgi_server(
            app=fake_app.get_app(), port=test_port, workers=4
        )
        wsgi_path = f"{wsgi_creator.wsgi_folder}/wsgi_testing_com.py"

        assert os.path.exists(wsgi_path)

        result = wsgi_creator.stop_server_by_port(test_port, "testing.com")
        assert result is True

        wsgi_creator.delete_wsgi_files("testing.com")
        assert not os.path.exists(wsgi_path)

    @pytest.mark.integration
    def test_is_server_running_integration(self, wsgi_creator, fake_app):
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

    @pytest.mark.integration
    def test_restart_server_integration(self, wsgi_creator, fake_app):
        # testing for an appliction that was previously paused, meaning it has an existing wsgi file but not started
        # Create the wsgi file
        test_port = get_free_port()
        app = fake_app.get_app()
        domain = app.config.get("DOMAIN", "unknown")

        wsgi_creator._create_wsgi_file(domain, test_port)

        assert wsgi_creator.is_server_running(test_port) is False

        # restart
        wsgi_creator.reboot_server(domain, test_port)
        # Wait longer for gunicorn to shut down
        time.sleep(2)

        assert wsgi_creator.is_server_running(test_port) is True
        
        # Cleanup
        wsgi_creator.stop_server_by_port(test_port, domain)
        wsgi_creator.delete_wsgi_files(domain)
