import os
import flask_application
import pytest
from unittest.mock import Mock, patch
from flask_application import FlaskApplication
import fakeredis
import command
from time import time, sleep
import threading


class TestFlaskApplication:
    ##CREATION FUNCTION TESTS ##

    @pytest.mark.unit
    def test_template_folder_is_created(self, fake_redis_client):
        # Create the required mocks for the params of the FlaskApplication class
        domain = "test.example.com"
        excepted_template_folder = f"../templates/{domain}"

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
                redis_client=fake_redis_client,
                template_folder=None,
            )
            # Assertion
            mock_makedirs.assert_called_once_with(
                excepted_template_folder, exist_ok=True
            )

            # Index html should be called
            mock_create_index_html.assert_called_once()

    @pytest.mark.unit
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

    @pytest.mark.integration
    def test_beacon_request_with_available_commands_integration(
        self, flask_app, fake_redis_client, tmp_path
    ):
        domain = "test.example.com"
        commands = ["ls", "pwd"]

        # Make sure that commands are queued into the redis_client
        command.queue_commands(
            domain=domain, redis_client=fake_redis_client, commands=commands
        )

        # Example url that is called so we can test it
        fake_url = f"https://{domain}/fjioawejfoew/jfioewajfo/test.woff"

        # Make sure that the folder and the file were created
        assert os.path.exists(tmp_path)
        assert os.path.exists(os.path.join(tmp_path, "index.html"))

        # Use a real http request (in the agent tests this should be using the agent)
        # At the moment this is using the test client for flask applications
        # Going to have the client send the following format for now
        with flask_app.get_app().test_client() as client:
            response = client.get(fake_url)

            json_data = response.get_json()
            # We expect the response to be our commands that we have taken so assert there
            assert response.status_code == 200
            assert json_data["commands"] == commands

    @pytest.mark.integration
    def test_beacon_request_with_no_available_commands_integration(
        self, flask_app, tmp_path
    ):
        domain = "test.example.com"

        # Example url that is called so we can test it
        fake_url = f"https://{domain}/fjioawejfoew/jfioewajfo/test.woff"

        # Make sure that the folder and the file were created
        assert os.path.exists(tmp_path)
        assert os.path.exists(os.path.join(tmp_path, "index.html"))

        with flask_app.get_app().test_client() as client:
            response = client.get(fake_url)

            json_data = response.get_json()
            # We expect the response to be our commands that we have taken so assert there
            assert response.status_code == 404
            assert json_data["status"] == "No data available"

    @pytest.mark.integration
    def test_beacon_results_with_success(self, flask_app, fake_redis_client, tmp_path):
        """Sends over results from a beacon and tests whether the application is able to handle them"""

        domain = "test.example.com"

        commands = ["pwd", "ls"]

        command_results = [
            "/johnnybgoode/chuckBerry/Desktop",
            "test.txt \n songs.txt \n dog.jpg",
        ]

        # Example url that is called so we can test it

        fake_url = f"https://{domain}/fjioawejfoew/jfioewajfo/test.css"

        # Make sure that the folder and the file were created
        assert os.path.exists(tmp_path)
        assert os.path.exists(os.path.join(tmp_path, "index.html"))

        with flask_app.get_app().test_client() as client:
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

    @pytest.mark.integration
    def test_long_polling_request_with_success(
        self, flask_app, fake_redis_client, tmp_path
    ):
        domain = "test.example.com"
        commands = ["ls", "pwd"]

        # Make sure that commands are queued into the redis_client
        command.queue_commands(
            domain=domain, redis_client=fake_redis_client, commands=commands
        )

        # Example url that is called so we can test it
        fake_url = f"https://{domain}/fjioawejfoew/jfioewajfo/test.png"

        # Make sure that the folder and the file were created
        assert os.path.exists(tmp_path)
        assert os.path.exists(os.path.join(tmp_path, "index.html"))

        # Use a real http request (in the agent tests this should be using the agent)
        # At the moment this is using the test client for flask applications
        # Going to have the client send the following format for now
        with flask_app.get_app().test_client() as client:
            response = client.get(fake_url)
            json_data = response.get_json()
            # We expect the response to be our commands that we have taken so assert there
            assert response.status_code == 200
            assert json_data["commands"] == commands

    @pytest.mark.integration
    def test_long_polling_request_with_success_commands_not_immediately_available(
        self, flask_app, fake_redis_client, tmp_path
    ):
        """Test long polling when commands arrive after a delay"""
        domain = "test.example.com"
        commands = ["echo delayed", "ls -la"]

        # Example url that is called so we can test it
        fake_url = f"https://{domain}/fjioawejfoew/jfioewajfo/test.png"

        # Make sure that the folder and the file were created
        assert os.path.exists(tmp_path)
        assert os.path.exists(os.path.join(tmp_path, "index.html"))

        def queue_commands_after_delay():
            """Function to queue commands after 2 seconds"""
            sleep(2)  # Wait 2 seconds
            command.queue_commands(
                domain=domain, redis_client=fake_redis_client, commands=commands
            )

        # Start the thread to queue commands after delay
        thread = threading.Thread(target=queue_commands_after_delay, daemon=True)
        thread.start()

        # Record start time
        start_time = time()

        # Make the blocking request (this will wait for commands)
        with flask_app.get_app().test_client() as client:
            response = client.get(fake_url)
            json_data = response.get_json()

            # Record end time
            end_time = time()

            # Verify response
            assert response.status_code == 200
            assert json_data["commands"] == commands

            # Verify it took approximately 2 seconds
            elapsed_time = end_time - start_time
            assert elapsed_time == pytest.approx(2.0, abs=0.5)  # 2 seconds ±0.5s

        # Wait for thread to complete
        thread.join()

    @pytest.mark.integration
    def test_long_polling_requests_with_no_commands(
        self, flask_app, fake_redis_client, tmp_path
    ):
        domain = "test.example.com"
        # Example url that is called so we can test it
        fake_url = f"https://{domain}/fjioawejfoew/jfioewajfo/test.png"

        # Make sure that the folder and the file were created
        assert os.path.exists(tmp_path)
        assert os.path.exists(os.path.join(tmp_path, "index.html"))

        # Use a real http request (in the agent tests this should be using the agent)
        # At the moment this is using the test client for flask applications
        # Going to have the client send the following format for now
        with flask_app.get_app().test_client() as client:
            response = client.get(fake_url)
            json_data = response.get_json()
            # We expect the response to be our commands that we have taken so assert there
            assert response.status_code == 404
            assert json_data["status"] == "No results or commands provided"

    @pytest.mark.integration
    def test_sending_long_polling_results(self, flask_app, fake_redis_client, tmp_path):
        domain = "test.example.com"

        commands = ["pwd", "ls"]

        command_results = [
            "/johnnybgoode/chuckBerry/Desktop",
            "test.txt \n songs.txt \n dog.jpg",
        ]

        # Example url that is called so we can test it

        fake_url = f"https://{domain}/fjioawejfoew/jfioewajfo/test.js"

        # Make sure that the folder and the file were created
        assert os.path.exists(tmp_path)
        assert os.path.exists(os.path.join(tmp_path, "index.html"))

        with flask_app.get_app().test_client() as client:
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

    @pytest.mark.integration
    def test_agent_modification_request_with_available_commands_integration(
        self, flask_app, fake_redis_client, tmp_path
    ):
        domain = "test.example.com"
        modification_commands = [
            "set_beacon_timer:30",
            "change_mode:l",
            "set_domain:backup.com",
        ]

        # Make sure that modification commands are queued into the redis_client
        command.queue_agent_modification_commands(
            domain=domain,
            redis_client=fake_redis_client,
            commands=modification_commands,
        )

        # Example url that is called so we can test it (.pdf extension for modification requests)
        fake_url = f"https://{domain}/fjioawejfoew/jfioewajfo/test.pdf"

        # Make sure that the folder and the file were created
        assert os.path.exists(tmp_path)
        assert os.path.exists(os.path.join(tmp_path, "index.html"))

        # Use a real http request (in the agent tests this should be using the agent)
        # At the moment this is using the test client for flask applications
        with flask_app.get_app().test_client() as client:
            response = client.get(fake_url)

            json_data = response.get_json()
            # We expect the response to be our modification commands that we have queued
            assert response.status_code == 200
            assert json_data["commands"] == modification_commands

    @pytest.mark.integration
    def test_agent_modification_request_with_no_available_commands_integration(
        self, flask_app, tmp_path
    ):
        domain = "test.example.com"

        # Example url that is called so we can test it (.pdf extension for modification requests)
        fake_url = f"https://{domain}/fjioawejfoew/jfioewajfo/test.pdf"

        # Make sure that the folder and the file were created
        assert os.path.exists(tmp_path)
        assert os.path.exists(os.path.join(tmp_path, "index.html"))

        with flask_app.get_app().test_client() as client:
            response = client.get(fake_url)

            json_data = response.get_json()
            # We expect a 404 response when no modification commands are available
            assert response.status_code == 404
            assert json_data["status"] == "No data available"

    @pytest.mark.integration
    def test_sending_agent_modification_results(
        self, flask_app, fake_redis_client, tmp_path
    ):
        domain = "test.example.com"

        modification_commands = ["watchdog:5000", "change_mode:l", "kill"]

        command_results = [
            "Watchdog timer set to 5000 seconds",
            "Switched to long-poll mode",
            "Agent terminated",
        ]

        fake_url = f"https://{domain}/foew/fjewoj/test.gif"

        assert os.path.exists(tmp_path)
        assert os.path.exists(os.path.join(tmp_path, "index.html"))

        with flask_app.get_app().test_client() as client:
            response = client.post(
                fake_url,
                json={"commands": modification_commands, "results": command_results},
            )

            json_data = response.get_json()
            assert response.status_code == 200
            assert json_data["status"] == "received"

        stream_key = f"{domain}:mod_results"
        stream_data = fake_redis_client.xread({stream_key: 0})

        assert len(stream_data[0][1]) == 3

        messages = stream_data[0][1]

        assert messages[0][1][b"command"].decode() == modification_commands[0]
        assert messages[0][1][b"result"].decode() == command_results[0]
        assert messages[0][1][b"domain"].decode() == domain

        assert messages[1][1][b"command"].decode() == modification_commands[1]
        assert messages[1][1][b"result"].decode() == command_results[1]
        assert messages[1][1][b"domain"].decode() == domain

        assert messages[2][1][b"command"].decode() == modification_commands[2]
        assert messages[2][1][b"result"].decode() == command_results[2]
        assert messages[2][1][b"domain"].decode() == domain
