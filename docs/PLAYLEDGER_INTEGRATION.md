# PlayLedger integration plan

This starter deliberately does not call PlayLedger over the network or create real funds.

Recommended integration:
1. Treat PlayLedger as the authoritative ledger for deposits, withdrawals, stakes, payouts, reversals, and balances.
2. Add an outbox event in the same transaction as each committed ledger entry.
3. Publish outbox events to this service with a unique event ID and signature/authentication.
4. Deduplicate by source system + event ID (extend `ActivityEvent` with `source_system` if multiple producers are used).
5. Compute net-loss/deposit aggregates from authoritative ledger entries using documented reversal/refund rules; do not trust client-submitted totals.
6. Define a fail-closed policy for responsible-gaming checks if the risk service or ledger is unavailable.
7. Use service-to-service authentication and least-privilege database credentials.
8. Test duplicate, delayed, reordered, reversed, and concurrent events.

Do not expose this demo's event-ingestion endpoint publicly without authentication hardening, throttling, input limits, event signing, and an explicit tenant/source authorization model.
