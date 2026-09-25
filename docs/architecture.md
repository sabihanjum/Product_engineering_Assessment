# Architecture and Database Notes

## Request flow

1. The React client authenticates through `/api/auth/login` and stores the short-lived bearer token for the demo session.
2. FastAPI decodes the token and loads the user from PostgreSQL.
3. Route dependencies enforce role permissions before service logic runs.
4. Ticket mutations validate the transition graph, update current state, and append an activity record in the same database transaction.
5. Dashboard queries derive queue counts and SLA breach state from current ticket data.

## Lifecycle

```text
OPEN -> ASSIGNED -> IN_PROGRESS -> PENDING_STUDENT -> IN_PROGRESS
                                  \-> RESOLVED -> CLOSED
                                                   \-> REOPENED -> IN_PROGRESS
```

The API rejects transitions not listed in the graph. Reopening clears `resolved_at` while retaining the earlier activity record.

## Security boundary

The frontend hides controls for convenience, but every sensitive action is checked in the API. A Student can only list, view, and comment on tickets where `student_id` matches their identity. Staff and Managers can view the service queue; only those roles can update assignment, status, or priority.

## Next production steps

- Alembic migrations and PostgreSQL integration tests
- Conditional claim endpoint with `SELECT ... FOR UPDATE` or optimistic versioning
- Dedicated assignment history with reason and previous assignee
- Object storage for attachment uploads
- Background worker for notifications and scheduled breach escalation