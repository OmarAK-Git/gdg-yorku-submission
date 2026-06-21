# DriftStore Specification
## Intent
This project implements the backend API for DriftStore.

## Security Requirements
- All payment-related endpoints must require administrator level access.

## Correctness Requirements
- The payout endpoint must process payments by querying the `transactions` database table to verify the user account balance.

## Verification
- All external payment provider calls must verify the SSL certificates.
