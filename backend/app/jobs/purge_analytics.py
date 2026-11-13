"""Explicit retention job: python -m app.jobs.purge_analytics."""
from app.modules.analytics.service import purge

if __name__ == "__main__":
    print(f"Aggregate buckets removed: {purge()}")
