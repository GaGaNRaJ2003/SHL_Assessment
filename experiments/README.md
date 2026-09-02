# Experiments

Archived research code from building the recommender. Not part of the deployed
system — kept as the record of the optimisation journey (34.67% → 61.56% Recall@10).

Run from the repository root so the `src.*` imports resolve:

```bash
python -m experiments.evaluate_xgboost
```

- `evaluate_*.py` — one file per retrieval/re-ranking strategy that was tried
  (direct, top-k sweep, LLM rerank, ensemble, sentence-transformers, XGBoost).
  `evaluate_xgboost.py` is the winning configuration.
- `generate_predictions_*.py` — prediction generation for alternate pipelines.
- `analyze_low_recall_queries.py`, `add_missing_assessments.py`,
  `check_assessments.py`, `check_setup.py` — one-off diagnostics.
- `crawlers/` — crawler variants superseded by `src/crawler_master.py`.
