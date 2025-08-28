import os
import sys
from tempfile import template

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import flask_application
import pytest
from unittest.mock import Mock, patch
from flask_application import FlaskApplication
import fakeredis
import command
from time import time


class TestFlaskApplication:
    # Creating a fake redis_client

    @pytest.fixture
    def fake_redis_client(request):
        redis_client = fakeredis.FakeRedis()
        yield redis_client

    def test_template_folder_is_created(self):
        # Create the required mocks for the params of the FlaskApplication class
        domain = "test.example.com"
        excepted_template_folder = f"templates/{domain}"

        # Path the call that makes hte directory

        with (
            patch("flask_application.os.makedirs") as mock_makedirs,
            patch(
                "flask_application.FlaskApplication._create_index_html"
            ) as mock_create_index_html,
        ):
            # Run the test
            app = FlaskApplication(
                domain=domain,  # Use defaults for the below values
                redis_client=None,
                template_folder=None,
            )
            # Assertion
            mock_makedirs.assert_called_once_with(
                excepted_template_folder, exist_ok=True
            )

            # Index html should be called
            mock_create_index_html.assert_called_once()

    def test_index_html_is_not_overwritten(self):
        # The index.html should be created if it does not exist in the template folder
        domain = "test.example.com"

        with (
            patch("flask_application.os.makedirs") as mock_makedirs,
            patch(
                "flask_application.os.path.exists", return_value=True
            ) as mock_path_exists,
            patch(
                "flask_application.FlaskApplication._create_index_html"
            ) as mock_create_index_html,
        ):
            app = FlaskApplication(domain=domain)

            # Assert that the makedirs was called
            mock_makedirs.assert_called_once()

            # Assert that the OS path was called
            mock_path_exists.assert_called_once()

            # Assert that create was not called
            mock_create_index_html.assert_not_called()

    def test_beacon_request_with_available_commands(self, fake_redis_client, tmp_path):
        domain = "test.example.com"

        # Decalre the flask application using the fake redis
        app = FlaskApplication(
            domain=domain,
            redis_client=fake_redis_client,
            template_folder=tmp_path,  # tmp_path is a fixture that is used by pytest that automatically handles the teardown of opwerations
        )

        commands = ["ls", "pwd"]

        # Make sure that commands are queued into the redis_client
        command.queue_commands(
            domain=domain, redis_client=fake_redis_client, commands=commands
        )

        # Example url that is called so we can test it
        fake_url = f"https://{domain}.com/fjioawejfoew/jfioewajfo/test.woff"

        # Make sure that the folder and the file were created
        assert os.path.exists(tmp_path)
        assert os.path.exists(os.path.join(tmp_path, "index.html"))

        # Use a real http request (in the agent tests this should be using the agent)
        # At the moment this is using the test client for flask applications
        # Going to have the client send the following format for now
        with app.get_app().test_client() as client:
            response = client.get(fake_url)

            json_data = response.get_json()
            # We expect the response to be our commands that we have taken so assert there
            assert response.status_code == 200
            assert json_data["commands"] == commands

    def test_beacon_request_with_no_available_commands(
        self, fake_redis_client, tmp_path
    ):
        domain = "test.example.com"
        # Decalre the flask application using the fake redis

        app = FlaskApplication(
            domain=domain,
            redis_client=fake_redis_client,
            template_folder=tmp_path,  # tmp_path is a fixture that is used by pytest that automatically handles the teardown of opwerations
        )

        # Example url that is called so we can test it
        fake_url = f"https://{domain}.com/fjioawejfoew/jfioewajfo/test.woff"

        # Make sure that the folder and the file were created
        assert os.path.exists(tmp_path)
        assert os.path.exists(os.path.join(tmp_path, "index.html"))

        with app.get_app().test_client() as client:
            response = client.get(fake_url)

            json_data = response.get_json()
            # We expect the response to be our commands that we have taken so assert there
            assert response.status_code == 404
            assert json_data["status"] == "No data available"

    def test_beacon_results_with_success(self, fake_redis_client, tmp_path):
        """Sends over results from a beacon and tests whether the application is able to handle them"""

        domain = "test.example.com"
        # Decalre the flask application using the fake redis

        app = FlaskApplication(
            domain=domain,
            redis_client=fake_redis_client,
            template_folder=tmp_path,  # tmp_path is a fixture that is used by pytest that automatically handles the teardown of opwerations
        )

        commands = ["pwd", "ls"]

        command_results = [
            "/johnnybgoode/chuckBerry/Desktop",
            "test.txt \n songs.txt \n dog.jpg",
        ]

        # Example url that is called so we can test it

        fake_url = f"https://{domain}.com/fjioawejfoew/jfioewajfo/test.css"

        # Make sure that the folder and the file were created
        assert os.path.exists(tmp_path)
        assert os.path.exists(os.path.join(tmp_path, "index.html"))

        with app.get_app().test_client() as client:
            response = client.post(
                fake_url,
                json={"results": command_results, "commands": commands},
            )

            json_data = response.get_json()
            # We expect the response to be our commands that we have taken so assert there
            assert response.status_code == 200  # Confirmation that they were recieved
            assert json_data["status"] == "received"

        stream_key = f"{domain}:results"
        stream_data = fake_redis_client.xread({stream_key: 0})

        assert len(stream_data[0][1]) == 2

        messages = stream_data[0][1]

        assert messages[0][1][b"command"].decode() == commands[0]
        assert messages[0][1][b"result"].decode() == command_results[0]
        assert messages[0][1][b"domain"].decode() == domain

        assert messages[1][1][b"command"].decode() == commands[1]
        assert messages[1][1][b"result"].decode() == command_results[1]
        assert messages[1][1][b"domain"].decode() == domain

    ##TODO: Do the same tests but with the agents as well! For a FULL integration test


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
