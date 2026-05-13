# Dev Organ Self-Improvement Plan

**Date:** 2026-05-14  
**Owner:** Codex  
**Scope:** Turn Fahmi's self-improvement direction into north star, roadmap, and first executable safety skeleton.

## Goal

Teach MiganCore to treat code/tool improvement as a controlled organism loop:

```text
observe -> diagnose -> propose -> sandbox patch -> test -> iterate -> validate -> promote -> monitor -> learn
```

The first implementation does not auto-deploy. It defines the doctrine, risk
model, gate model, and promotion decision function that later workers can call.

## Files

- `docs/SELF_IMPROVEMENT_NORTHSTAR.md`
- `docs/MIGANCORE_DIRECTION_LOCK.md`
- `docs/01_SOUL.md`
- `api/services/dev_organ.py`
- `api/tests/test_dev_organ.py`

## Tasks

- [x] Audit current direction docs, SOUL, config, and service layout.
- [x] Add canonical self-improvement north star and roadmap.
- [x] Update Direction Lock with the Dev Organ rule.
- [x] Update SOUL with self-evolution operating doctrine.
- [x] Add Dev Organ risk/gate skeleton service.
- [x] Add focused tests for promotion decisions.
- [x] Run static verification.
- [ ] Commit and push.

## Promotion Rules For This Sprint

- Documentation changes are low risk.
- `api/services/dev_organ.py` is additive and not wired into runtime yet, so it is medium risk.
- No production deploy is required until the service is connected to a worker/API route.
- Verification is limited to syntax/static tests and focused unit-test design in this sprint.
