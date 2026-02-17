"""Tests for Phase 2, Task 8: On-Demand Sync Endpoint."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.routes.sync import VALID_BANKS

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_subprocess_success(bank):
    """Return a CompletedProcess simulating a successful scrape."""
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = 0
    result.stdout = f"Scraped {bank} successfully"
    result.stderr = ""
    return result


def _mock_subprocess_failure(bank, stderr="credentials missing"):
    """Return a CompletedProcess simulating a failed scrape."""
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = 1
    result.stdout = ""
    result.stderr = stderr
    return result


def _mock_ingest_results(inserted=3, updated=1, skipped=2, errors=None):
    """Return a list mimicking ingest_all() output."""
    return [
        {
            "file": "leumi_2026-02-17.json",
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "errors": errors or [],
        }
    ]


def _setup_source(db):
    db.execute(
        "INSERT INTO accounts (id, name, bank, type, scraper_type) "
        "VALUES (1, 'Test Account', 'leumi', 'personal', 'leumi')"
    )
    db.commit()


def _write_scraper_json(tmp_path, bank, account_number, txns):
    bank_dir = tmp_path / bank
    bank_dir.mkdir(exist_ok=True)
    data = {
        "bank": bank,
        "scrapedAt": "2026-02-17T12:00:00Z",
        "accounts": [{"accountNumber": account_number, "txns": txns}],
    }
    f = bank_dir / f"{bank}_2026-02-17.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestSyncValidation:
    def test_unknown_bank_returns_400(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            resp = client.post("/api/sync", json={"banks": ["invalid"]})
        assert resp.status_code == 400
        assert "Unknown banks" in resp.json()["detail"]

    def test_multiple_unknown_banks_returns_400(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            resp = client.post("/api/sync", json={"banks": ["foo", "bar"]})
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "foo" in detail
        assert "bar" in detail

    def test_mix_of_valid_and_invalid_returns_400(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            resp = client.post("/api/sync", json={"banks": ["leumi", "nope"]})
        assert resp.status_code == 400
        assert "nope" in resp.json()["detail"]

    def test_valid_banks_accepted(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.return_value = _mock_subprocess_success("leumi")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": ["leumi"]})
        assert resp.status_code == 200

    def test_empty_banks_list_syncs_all(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.return_value = _mock_subprocess_success("all")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": []})
        # Empty list defaults to all banks
        assert resp.status_code == 200
        assert len(resp.json()["scrape_results"]) == len(VALID_BANKS)


# ---------------------------------------------------------------------------
# Default behavior (no body / null banks)
# ---------------------------------------------------------------------------

class TestSyncDefaults:
    def test_no_body_syncs_all_banks(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.return_value = _mock_subprocess_success("all")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync")
        assert resp.status_code == 200
        results = resp.json()["scrape_results"]
        assert len(results) == len(VALID_BANKS)
        bank_names = {r["bank"] for r in results}
        assert bank_names == set(VALID_BANKS)

    def test_null_banks_syncs_all(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.return_value = _mock_subprocess_success("all")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": None})
        assert resp.status_code == 200
        assert len(resp.json()["scrape_results"]) == len(VALID_BANKS)


# ---------------------------------------------------------------------------
# Scraper subprocess behavior
# ---------------------------------------------------------------------------

class TestSyncScraper:
    def test_successful_scrape_result(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.return_value = _mock_subprocess_success("leumi")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": ["leumi"]})
        data = resp.json()
        assert len(data["scrape_results"]) == 1
        assert data["scrape_results"][0]["bank"] == "leumi"
        assert data["scrape_results"][0]["success"] is True
        assert data["scrape_results"][0]["error"] is None

    def test_failed_scrape_result(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.return_value = _mock_subprocess_failure("leumi", stderr="bad creds")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": ["leumi"]})
        data = resp.json()
        assert data["scrape_results"][0]["success"] is False
        assert "bad creds" in data["scrape_results"][0]["error"]

    def test_failed_scrape_empty_stderr_shows_exit_code(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.return_value = _mock_subprocess_failure("leumi", stderr="")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": ["leumi"]})
        data = resp.json()
        assert data["scrape_results"][0]["success"] is False
        assert "Exit code" in data["scrape_results"][0]["error"]

    def test_timeout_scrape_result(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.side_effect = subprocess.TimeoutExpired(cmd="npm", timeout=120)
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": ["leumi"]})
        data = resp.json()
        assert data["scrape_results"][0]["success"] is False
        assert "timed out" in data["scrape_results"][0]["error"]

    def test_exception_scrape_result(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.side_effect = FileNotFoundError("npm not found")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": ["leumi"]})
        data = resp.json()
        assert data["scrape_results"][0]["success"] is False
        assert "npm not found" in data["scrape_results"][0]["error"]

    def test_continues_on_failure(self):
        """When one bank fails, the rest still run."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FileNotFoundError("npm not found")
            return _mock_subprocess_success("ok")

        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.side_effect = side_effect
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": ["leumi", "max"]})
        data = resp.json()
        assert len(data["scrape_results"]) == 2
        assert data["scrape_results"][0]["success"] is False
        assert data["scrape_results"][1]["success"] is True

    def test_scraper_called_with_correct_command(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.return_value = _mock_subprocess_success("isracard")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": ["isracard"]})
        call_args = mock_sub.run.call_args
        assert call_args[0][0] == ["npm", "run", "scrape:isracard"]
        assert call_args[1]["capture_output"] is True
        assert call_args[1]["text"] is True
        assert call_args[1]["timeout"] == 120


# ---------------------------------------------------------------------------
# Ingestion integration
# ---------------------------------------------------------------------------

class TestSyncIngestion:
    def test_ingestion_results_aggregated(self):
        mock_results = [
            {"file": "a.json", "inserted": 5, "updated": 2, "skipped": 1, "errors": []},
            {"file": "b.json", "inserted": 3, "updated": 0, "skipped": 4, "errors": ["bad row"]},
        ]
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=mock_results):
            mock_sub.run.return_value = _mock_subprocess_success("leumi")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": ["leumi"]})
        ingestion = resp.json()["ingestion"]
        assert ingestion["inserted"] == 8
        assert ingestion["updated"] == 2
        assert ingestion["skipped"] == 5
        assert ingestion["errors"] == ["bad row"]

    def test_no_files_ingested(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.return_value = _mock_subprocess_success("leumi")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": ["leumi"]})
        ingestion = resp.json()["ingestion"]
        assert ingestion["inserted"] == 0
        assert ingestion["updated"] == 0
        assert ingestion["skipped"] == 0
        assert ingestion["errors"] == []

    def test_ingest_all_called_after_scraping(self):
        """Verify ingest_all is called exactly once."""
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]) as mock_ingest:
            mock_sub.run.return_value = _mock_subprocess_success("leumi")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            client.post("/api/sync", json={"banks": ["leumi"]})
        mock_ingest.assert_called_once()


# ---------------------------------------------------------------------------
# Response structure
# ---------------------------------------------------------------------------

class TestSyncResponseStructure:
    def test_response_has_required_fields(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.return_value = _mock_subprocess_success("leumi")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": ["leumi"]})
        data = resp.json()
        assert "scrape_results" in data
        assert "ingestion" in data
        assert isinstance(data["scrape_results"], list)
        assert "inserted" in data["ingestion"]
        assert "updated" in data["ingestion"]
        assert "skipped" in data["ingestion"]
        assert "errors" in data["ingestion"]

    def test_scrape_result_fields(self):
        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all", return_value=[]):
            mock_sub.run.return_value = _mock_subprocess_success("leumi")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            resp = client.post("/api/sync", json={"banks": ["leumi"]})
        result = resp.json()["scrape_results"][0]
        assert "bank" in result
        assert "success" in result
        assert "error" in result


# ---------------------------------------------------------------------------
# End-to-end with real ingestion (mocked scraper only)
# ---------------------------------------------------------------------------

class TestSyncEndToEnd:
    def test_scrape_and_ingest_real_pipeline(self, db, tmp_path):
        """Mock subprocess but use real ingest_all with test JSON files."""
        _setup_source(db)
        _write_scraper_json(tmp_path, "leumi", "1234", [
            {"description": "שופרסל דיל", "date": "2026-02-10T00:00:00Z",
             "chargedAmount": -200, "status": "completed"},
            {"description": "SPOTIFY Premium", "date": "2026-02-12T00:00:00Z",
             "chargedAmount": -30, "status": "completed"},
        ])

        with patch("api.routes.sync.subprocess") as mock_sub, \
             patch("api.routes.sync.ingest_all") as mock_ingest:
            mock_sub.run.return_value = _mock_subprocess_success("leumi")
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            # Use real ingest_all pointed at our tmp_path
            from ingestion.ingest import ingest_all as real_ingest_all
            mock_ingest.side_effect = lambda: real_ingest_all(output_dir=tmp_path)
            resp = client.post("/api/sync", json={"banks": ["leumi"]})

        assert resp.status_code == 200
        data = resp.json()
        assert data["scrape_results"][0]["success"] is True
        assert data["ingestion"]["inserted"] == 2
        assert data["ingestion"]["errors"] == []

        # Verify transactions are actually in the DB
        rows = db.execute("SELECT description FROM transactions ORDER BY date").fetchall()
        assert len(rows) == 2
