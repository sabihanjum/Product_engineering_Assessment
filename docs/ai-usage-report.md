# AI Usage Report

## AI tool used

GitHub Copilot was used during implementation.

## What I asked AI to do

1. Identify the core workflows, roles, ticket lifecycle, SLA behavior, audit history, and edge cases for a student support product.
2. Generate a focused FastAPI, SQLAlchemy, React, and Docker MVP structure.
3. Review the API boundary for authorization and invalid state transition risks.

## Most useful prompt

> Design a student support and ticket management MVP for a college. Include Student, Staff, and Manager roles; ticket lifecycle and SLA rules; audit history; role-based authorization; dashboard metrics; API boundaries; edge cases; validation strategy; and practical trade-offs. Prioritize a complete end-to-end workflow over breadth.

## Code generated and modified

AI generated initial boilerplate for models, authentication routes, ticket endpoints, seed data, React views, Docker files, and tests. The implementation was then shaped around the selected schema, status transition graph, SLA policy, API ownership rules, UI workflow, and local environment.

## Incorrect or incomplete output identified

The first password hashing choice relied on a bcrypt/passlib combination that was incompatible with the installed Python 3.13 environment. The test suite exposed that failure during collection. It was replaced with Passlib's portable PBKDF2-SHA256 scheme. Frontend-only access restrictions were also treated as insufficient, so ownership checks remain in FastAPI.

## Validation performed

- Ran `python -m pytest -q` after the authentication repair: 2 tests passed.
- Ran `npm run build`: production bundle completed successfully.
- Reviewed role and ownership checks against the intended Student/Staff/Manager workflows.
- Included invalid transition, invalid assignee, reopen, SLA breach, and unauthorized-ticket behavior in the implementation contract and documentation.