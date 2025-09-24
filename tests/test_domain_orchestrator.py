import pytest
import tempfile
import os
import json
import socket
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import fakeredis

from domain_orchestrator import DomainOrchestrator


class TestDomainOrchestrator:
    @pytest.mark.unit
    def test_create_domain_already_exists(self, clean_dorch):
        clean_dorch.domainDictionary = {
            "test.com": (8000, 123, "running", "2024-01-01")
        }
        result = clean_dorch.create_domain("test.com", ".com")
        assert result is False

    @pytest.mark.unit
    def test_pause_domain_not_running(self, clean_dorch):
        clean_dorch.domainDictionary = {
            "test.com": (8000, None, "paused", "2024-01-01")
        }
        result = clean_dorch.pause_domain("test.com")
        assert result is False

    @pytest.mark.unit
    def test_pause_domain_not_found(self, clean_dorch):
        result = clean_dorch.pause_domain("nonexistent.com")
        assert result is False

    @pytest.mark.unit
    def test_resume_domain_not_paused(self, clean_dorch):
        clean_dorch.domainDictionary = {
            "test.com": (8000, 123, "running", "2024-01-01")
        }
        result = clean_dorch.resume_domain("test.com")
        assert result is False

    @pytest.mark.unit
    def test_resume_domain_not_found(self, clean_dorch):
        result = clean_dorch.resume_domain("nonexistent.com")
        assert result is False

    @pytest.mark.unit
    def test_remove_domain_not_found(self, clean_dorch):
        result = clean_dorch.remove_domain("nonexistent.com")
        assert result is False

    @pytest.mark.unit
    def test_is_port_available_internal_conflict(self, clean_dorch):
        clean_dorch.domainDictionary = {
            "existing.com": (8000, 123, "running", "2024-01-01")
        }
        assert clean_dorch.is_port_available(8000) is False
        assert clean_dorch.is_port_available(8000, "different.com") is False

    @pytest.mark.unit
    def test_is_port_available_same_domain(self, clean_dorch):
        clean_dorch.domainDictionary = {
            "test.com": (8000, 123, "running", "2024-01-01")
        }
        with patch("socket.socket") as mock_socket:
            mock_socket.return_value.__enter__.return_value.bind.return_value = None
            assert clean_dorch.is_port_available(8000, "test.com") is True

    @pytest.mark.unit
    @patch("socket.socket")
    def test_is_port_available_socket_success(self, mock_socket, clean_dorch):
        mock_socket.return_value.__enter__.return_value.bind.return_value = None
        assert clean_dorch.is_port_available(8000) is True

    @pytest.mark.unit
    @patch("socket.socket")
    def test_is_port_available_socket_failure(self, mock_socket, clean_dorch):
        mock_socket.return_value.__enter__.return_value.bind.side_effect = OSError()
        assert clean_dorch.is_port_available(8000) is False

    @pytest.mark.unit
    def test_find_available_port_success(self, clean_dorch):
        with patch.object(clean_dorch, "is_port_available") as mock_available:
            mock_available.side_effect = [False, False, True]
            port = clean_dorch.find_available_port(start_port=8000)
            assert port == 8002

    @pytest.mark.unit
    def test_find_available_port_none_available(self, clean_dorch):
        with patch.object(clean_dorch, "is_port_available", return_value=False):
            port = clean_dorch.find_available_port(start_port=8000, max_attempts=5)
            assert port is None

    @pytest.mark.unit
    def test_get_running_domains(self, clean_dorch):
        clean_dorch.domainDictionary = {
            "running1.com": (8000, 123, "running", "2024-01-01"),
            "paused.com": (8001, None, "paused", "2024-01-01"),
            "running2.com": (8002, 456, "running", "2024-01-02"),
            "resume.com": (8003, None, "resume", "2024-01-03"),
        }
        running = clean_dorch.get_running_domains()
        assert len(running) == 2
        running_domains = [domain for domain, _ in running]
        assert "running1.com" in running_domains
        assert "running2.com" in running_domains
        assert "paused.com" not in running_domains

    @pytest.mark.unit
    def test_get_paused_domains(self, clean_dorch):
        clean_dorch.domainDictionary = {
            "running.com": (8000, 123, "running", "2024-01-01"),
            "paused1.com": (8001, None, "paused", "2024-01-01"),
            "paused2.com": (8002, None, "paused", "2024-01-02"),
            "resume.com": (8003, None, "resume", "2024-01-03"),
        }
        paused = clean_dorch.get_paused_domains()
        assert len(paused) == 2
        paused_domains = [domain for domain, _ in paused]
        assert "paused1.com" in paused_domains
        assert "paused2.com" in paused_domains
        assert "running.com" not in paused_domains

    @pytest.mark.unit
    def test_get_all_domains(self, clean_dorch):
        original_dict = {
            "test1.com": (8000, 123, "running", "2024-01-01"),
            "test2.com": (8001, None, "paused", "2024-01-01"),
        }
        clean_dorch.domainDictionary = original_dict
        all_domains = clean_dorch.get_all_domains()
        assert all_domains == original_dict
        assert all_domains is not clean_dorch.domainDictionary

    @pytest.mark.unit
    def test_store_and_load_domains(self, clean_dorch, tmp_path):
        clean_dorch.domainDictionary = {
            "test.com": (8000, 123, "running", "2024-01-01"),
            "paused.com": (8001, None, "paused", "2024-01-02"),
        }
        clean_dorch._store_domains()
        assert os.path.exists(clean_dorch.domain_storage)

        # Create new orchestrator with same parameters to test loading
        fake_redis = fakeredis.FakeRedis()
        new_orchestrator = DomainOrchestrator(
            domain_storage=clean_dorch.domain_storage,
            redis_client=fake_redis,
            template_folder=clean_dorch.template_folder,
            wsgi_folder=clean_dorch.wsgi_folder,
            nginx_conf_folder=clean_dorch.nginx_conf_folder,
        )
        assert new_orchestrator._load_domains() is True
        assert new_orchestrator.domainDictionary == clean_dorch.domainDictionary

    @pytest.mark.unit
    def test_load_domains_file_not_found(self, clean_dorch, tmp_path):
        # Test with non-existent domain storage file
        result = clean_dorch._load_domains()
        assert result is False
        assert clean_dorch.domainDictionary == {}

    @pytest.mark.unit
    def test_store_domains_creates_valid_json(self, clean_dorch, tmp_path):
        clean_dorch.domainDictionary = {
            "test.com": (8000, 123, "running", "2024-01-01")
        }
        clean_dorch._store_domains()

        with open(clean_dorch.domain_storage, "r") as f:
            stored_data = json.load(f)
        # JSON stores tuples as lists, so verify the JSON format
        expected_json_data = {"test.com": [8000, 123, "running", "2024-01-01"]}
        assert stored_data == expected_json_data
        assert stored_data["test.com"][0] == 8000
        assert stored_data["test.com"][1] == 123
        assert stored_data["test.com"][2] == "running"

    @pytest.mark.unit
    def test_pause_domain_stores_to_file(self, clean_dorch, tmp_path):
        clean_dorch.domainDictionary = {
            "test.com": (8000, 123, "running", "2024-01-01")
        }
        with (
            patch.object(
                clean_dorch.wsgi_creator, "is_server_running", return_value=True
            ),
            patch.object(clean_dorch.wsgi_creator, "stop_server_by_port"),
        ):
            result = clean_dorch.pause_domain("test.com")
            assert result is True

        with open(clean_dorch.domain_storage, "r") as f:
            stored_data = json.load(f)
        assert stored_data["test.com"][2] == "paused"
        assert stored_data["test.com"][1] is None

    @pytest.mark.unit
    def test_pause_domain_with_resume_flag_stores_to_file(self, clean_dorch, tmp_path):
        clean_dorch.domainDictionary = {
            "test.com": (8000, 123, "running", "2024-01-01")
        }
        with (
            patch.object(
                clean_dorch.wsgi_creator, "is_server_running", return_value=True
            ),
            patch.object(clean_dorch.wsgi_creator, "stop_server_by_port"),
        ):
            result = clean_dorch.pause_domain("test.com", resume=True)
            assert result is True

        with open(clean_dorch.domain_storage, "r") as f:
            stored_data = json.load(f)
        assert stored_data["test.com"][2] == "resume"
        assert stored_data["test.com"][1] is None

    @pytest.mark.unit
    def test_shutdown_domains_stores_resume_status(self, clean_dorch, tmp_path):
        clean_dorch.domainDictionary = {
            "running1.com": (8000, 123, "running", "2024-01-01"),
            "running2.com": (8001, 456, "running", "2024-01-02"),
            "paused.com": (8002, None, "paused", "2024-01-03"),
        }
        with (
            patch.object(
                clean_dorch.wsgi_creator, "is_server_running", return_value=True
            ),
            patch.object(clean_dorch.wsgi_creator, "stop_server_by_port"),
        ):
            result = clean_dorch.shutdown_domains()
            assert result is True

        with open(clean_dorch.domain_storage, "r") as f:
            stored_data = json.load(f)
        assert stored_data["running1.com"][2] == "resume"
        assert stored_data["running2.com"][2] == "resume"
        assert stored_data["paused.com"][2] == "paused"
