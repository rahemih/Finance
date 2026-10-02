# Security Policy

This repository is public, but the system is intended for private use by the owner and a small trusted team.

## Never commit

- Exchange or broker API keys
- Secret keys, private keys, passwords, session tokens
- Live account IDs or personally sensitive account data
- Production database credentials
- Raw secrets in screenshots, logs, fixtures, notebooks, or examples

Use placeholders and environment variables. Production secrets must live in an approved secret manager.

## Trading safety

Live trading and automatic trading are disabled until explicit roadmap gates and Owner approval are satisfied.

Trading API credentials should not have withdrawal permission.

## Reporting a vulnerability

Do not post exploitable security details or real credentials in a public issue. Use a private owner-approved channel or GitHub private vulnerability reporting once enabled.

## Incident priority

Unauthorized live order, risk-firewall bypass, or credential compromise is SEV-0 and requires immediate SAFE_MODE/EMERGENCY handling.
