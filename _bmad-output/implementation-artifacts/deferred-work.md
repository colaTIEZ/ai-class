## Deferred from: code review of 1-5-epic1-hotfix-zombie-tasks-security (2026-04-1)

- Test DB isolation still uses shared default SQLite path in `backend/tests/conftest.py`; pre-existing test architecture issue and not introduced by this hotfix.
