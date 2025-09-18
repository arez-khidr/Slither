import pytest
import os
import sys
import socket
import fakeredis
import redis
from threading import Thread
from time import sleep

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from domain_orchestrator import DomainOrchestrator
from agent.agent import Agent
from flask_application import FlaskApplication
from wsgi_creator import WSGICreator


def get_free_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture
def fake_redis_client():
    """Shared fake Redis client fixture"""
    server_port = get_free_port()
    print(f"THIS IS THE PORT IN THE FAKE REDIS CLIENT: {server_port}")
    server_address = ("127.0.0.1", server_port)
    server = fakeredis.TcpFakeServer(server_address=server_address, server_type="redis")
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    redis_client = redis.Redis(host=server_address[0], port=server_address[1])
    yield redis_client

    # Cleanup
    try:
        redis_client.close()
    except:
        pass
    server.shutdown()


@pytest.fixture
def agent():
    """Creates an agent to be used with the tests"""
    agent = Agent(domains=["testing.com"])
    yield agent

    # Clean up agent session
    if hasattr(agent, "session") and agent.session:
        agent.session.close()


@pytest.fixture
def clean_dorch(tmp_path, fake_redis_client):
    """Create a clean domain orchestrator with no domains - for domain orchestrator tests"""
    domain_storage = os.path.join(tmp_path, "domains.json")
    template_folder = str(tmp_path / "templates")
    wsgi_folder = str(tmp_path / "wsgi")
    nginx_conf_folder = str(tmp_path / "nginx")

    dorch = DomainOrchestrator(
        domain_storage=domain_storage,
        redis_client=fake_redis_client,
        template_folder=template_folder,
        wsgi_folder=wsgi_folder,
        nginx_conf_folder=nginx_conf_folder,
    )
    yield dorch

    # Cleanup: shutdown all domains even if test failed
    try:
        dorch.shutdown_domains()
    except Exception as e:
        print(f"Warning: Failed to shutdown domains during cleanup: {e}")

    # Remove all domains to clean up files
    try:
        for domain in list(dorch.domainDictionary.keys()):
            dorch.remove_domain(domain)
    except Exception as e:
        print(f"Warning: Failed to remove domains during cleanup: {e}")

    sleep(4)


@pytest.fixture
def fake_dorch(tmp_path, fake_redis_client):
    """Create a domain orchestrator with testing.com domain - for agent tests"""
    domain_storage = os.path.join(tmp_path, "domains.json")
    template_folder = str(tmp_path / "templates")
    wsgi_folder = str(tmp_path / "wsgi")
    nginx_conf_folder = str(tmp_path / "nginx")

    fake_dorch = DomainOrchestrator(
        domain_storage=domain_storage,
        redis_client=fake_redis_client,
        template_folder=template_folder,
        wsgi_folder=wsgi_folder,
        nginx_conf_folder=nginx_conf_folder,
    )
    fake_dorch.create_domain("testing.com", top_level_domain="", preferred_port=49152)
    yield fake_dorch

    # Cleanup: shutdown all domains even if test failed
    try:
        fake_dorch.shutdown_domains()
    except Exception as e:
        print(f"Warning: Failed to shutdown domains during cleanup: {e}")

    # Remove all domains to clean up files
    try:
        for domain in list(fake_dorch.domainDictionary.keys()):
            fake_dorch.remove_domain(domain)
    except Exception as e:
        print(f"Warning: Failed to remove domains during cleanup: {e}")

    # Making sure that everything shuts down :wsgi_folder
    sleep(4)


@pytest.fixture
def flask_app(fake_redis_client, tmp_path):
    """Create a FlaskApplication instance for testing"""
    domain = "test.example.com"

    app = FlaskApplication(
        domain=domain,
        redis_client=fake_redis_client,
        template_folder=tmp_path,
    )

    yield app

    # Cleanup Flask app if it has any running processes
    try:
        flask_app_instance = app.get_app()
        if hasattr(flask_app_instance, "shutdown"):
            flask_app_instance.shutdown()
    except:
        pass


@pytest.fixture
def wsgi_creator(tmp_path, fake_redis_client):
    """Create WSGICreator with test-appropriate parameters"""
    wsgi_folder = str(tmp_path / "wsgi")

    return WSGICreator(
        redis_client=fake_redis_client,
        template_folder=tmp_path,
        wsgi_folder=wsgi_folder,
    )


@pytest.fixture
def fake_app(tmp_path, fake_redis_client):
    app = FlaskApplication(
        domain="testing.com",
        redis_client=fake_redis_client,
        template_folder=tmp_path,
    )
    yield app
