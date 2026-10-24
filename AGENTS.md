# Project guidance

Use Python for new automation. Annotate variables and function signatures, give
functions focused docstrings, and follow the existing formatting conventions.

## Application version policy

- The shared application version is `src/gameoflife/__init__.py`; package, About,
  and bundle metadata must consume that source. Keep build identifiers separate.
- Install clone-local hooks with `.venv/bin/python scripts/app_versioning.py install`.
  Publication is `origin/master`. Never infer publication from a pre-push attempt.
- Increment patch once per successful-push batch. Unknown/fix branches use patch.
  Classify a genuine feature explicitly with `scripts/app_versioning.py classify feature`:
  allocate minor once, then patch batches for follow-up fixes after publication.
- Preserve the higher compatible version on merges, without an extra increment.
  Never downgrade or infer a major change; a major override needs a user request.
- File saves, tests, and builds must not change the application version. Preserve
  partial staging and the active Git index. Follow README recovery instructions.
- Run the disposable Git integration tests when changing this workflow. Do not
  commit, push, deploy, or change hosted settings solely to install versioning.
