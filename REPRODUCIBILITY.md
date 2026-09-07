# Reproducibility

```bash
export PYTHONPATH=src
python3 -m cicada bootstrap
python3 -m cicada validate
python3 -m cicada ingest-core
python3 -m cicada verify-pgp
python3 -m cicada replay-known
python3 -m cicada run-frontier
python3 -m cicada reports
python3 -m pytest -q
```

Resume: there is no background worker. Re-run the commands above. State is in `state/RUN_STATE.json`, `state/EVENTS.jsonl`, and `db/research.sqlite`.
