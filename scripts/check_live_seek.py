"""Optional live diagnostic: one public SEEK search and one job-detail request."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import seek_search


def main():
    payload = seek_search.fetch_page("Python developer", "All Sydney NSW", 1, 14)
    records = payload.get("data")
    if not isinstance(records, list) or not records:
        raise RuntimeError("SEEK returned no listings; job-detail availability could not be verified.")
    detail = seek_search.fetch_detail(str(records[0]["id"]))
    if not detail or not detail.get("description") or detail.get("is_expired"):
        raise RuntimeError("SEEK did not return a full, active job description.")
    print(f"PASS: live SEEK search ({len(records)} results) and full job description ({len(detail['description'])} characters)")


if __name__ == "__main__":
    main()
