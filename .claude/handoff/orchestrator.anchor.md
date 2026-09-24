# Orchestrator anchor — 2026-09-24, M5 (past 75% soft threshold)

Plan: docs/plan-m5-missions.md (approved). Task lists are the state.
Backend for M5 is DONE: B-031 #74, B-032 #75 (+F-023 #76), B-033 #73, B-034 #78, B-035 #77. main suite 751.
Next (not dispatched — soft stop): F-020 ∥ F-021 (Ready; scout Q3 first), then F-022, then D-027, then M5 checkpoint.
Decisions: M-1 observable_modes = [ObsVectorSum]; anonymous may run M-1 only, records nothing; locked mission → 400; default host 0.0.0.0; cookie valid only if the student row exists.
Dead ends: my scopes twice omitted tests a new server validation necessarily breaks — before dispatching any task that adds validation to /api/run, have scout enumerate every test that POSTs it.
Known flake: N36 keyboard-pan e2e under concurrent load.
