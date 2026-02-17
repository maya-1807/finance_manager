import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.models import SyncRequest, SyncResponse, SyncScrapeResult, SyncIngestionResult
from ingestion.ingest import ingest_all

router = APIRouter(prefix="/api/sync", tags=["sync"])

VALID_BANKS = ["leumi", "isracard", "max"]
DATA_FETCHER_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data-fetcher"


@router.post("", response_model=SyncResponse)
def sync(request: SyncRequest = None):
    banks = request.banks if request and request.banks else VALID_BANKS

    unknown = [b for b in banks if b not in VALID_BANKS]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown banks: {unknown}")

    # Run scrapers
    scrape_results: list[SyncScrapeResult] = []
    for bank in banks:
        try:
            result = subprocess.run(
                ["npm", "run", f"scrape:{bank}"],
                cwd=str(DATA_FETCHER_DIR),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                scrape_results.append(SyncScrapeResult(bank=bank, success=True))
            else:
                scrape_results.append(SyncScrapeResult(
                    bank=bank, success=False, error=result.stderr.strip() or f"Exit code {result.returncode}",
                ))
        except subprocess.TimeoutExpired:
            scrape_results.append(SyncScrapeResult(bank=bank, success=False, error="Scraper timed out (120s)"))
        except Exception as e:
            scrape_results.append(SyncScrapeResult(bank=bank, success=False, error=str(e)))

    # Ingest new files
    ingestion_results = ingest_all()

    inserted = sum(r["inserted"] for r in ingestion_results)
    updated = sum(r["updated"] for r in ingestion_results)
    skipped = sum(r["skipped"] for r in ingestion_results)
    errors = []
    for r in ingestion_results:
        errors.extend(r["errors"])

    return SyncResponse(
        scrape_results=scrape_results,
        ingestion=SyncIngestionResult(
            inserted=inserted,
            updated=updated,
            skipped=skipped,
            errors=errors,
        ),
    )
