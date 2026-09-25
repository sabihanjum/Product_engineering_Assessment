# Assumptions and Trade-offs

- This assessment prioritizes a complete demonstrable workflow over a large feature count.
- Demo registration accepts a requested role so reviewers can exercise each persona. Production registration would always create Students; Manager provisioning would be administrative.
- The API uses a modular monolith because the domain is small and transactional. Splitting services now would add deployment and consistency cost without improving the user workflow.
- PostgreSQL is the Docker default. SQLite fallback exists only to make a local API smoke test easy when a database service is unavailable.
- Current dashboard counts are intentionally simple and readable. A production system would aggregate in SQL, paginate ticket queues, and add date-windowed analytics.
- AI categorization is not on the critical path. Any suggested category or priority should be shown as a suggestion and require staff confirmation.