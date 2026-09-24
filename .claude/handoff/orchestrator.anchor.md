# Orchestrator anchor — 2026-09-24, M5 (75% soft threshold)

Plan: docs/plan-m5-missions.md (approved). Task lists are the state.
Merged: B-031 #74, B-032 #75 (+F-023 #76 stacked), B-033 #73, B-035 #77. main suite 750.
In flight: B-034 #78 cycle-2 review (head f07d9a9, gate 751 merged-with-main). Merge on approve.
Not dispatched (soft stop): F-020 ∥ F-021 (both need B-034 merged; worktrees), then F-022, then D-027, then M5 checkpoint.
Decisions: M-1 observable_modes = [ObsVectorSum] only; anonymous may run M-1 only, records nothing; locked mission → 400; default host 0.0.0.0.
Dead ends: my file scopes twice omitted tests a gating change necessarily breaks (B-032, B-034) — when a task adds server validation, enumerate every test that POSTs /api/run first.
Known flake: N36 keyboard-pan e2e under concurrent load.
