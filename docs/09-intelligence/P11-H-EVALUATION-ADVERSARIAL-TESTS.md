# P11-H — Evaluation / Adversarial Tests

Task: `FIN-P11-WH-001`  
Linear: `HOS-249`  
State: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P11-WH-001-01` / RELEASED  
Canonical base: `4710b21b3bed56a78d419470c03f6a91664190f4`

## Objective

Validate the complete canonical P11-A..G news pipeline against deterministic mandatory adversarial scenarios.

## Mandatory scenarios

- confirmed fresh high-importance context reaches the expected critical descriptive alert;
- unconfirmed news is BLOCKED / QUARANTINED / SUPPRESSED;
- expired news is SUPPRESSED;
- entity boundary matching does not map "ethics" to ETH;
- community single-source news requires review;
- mixed sentiment remains explicit;
- as_of before observed_at fails closed;
- tampered content identity fails closed.

## Exit rule

Every mandatory scenario must pass. Required pass rate = 10000 basis points (100%).

Safety:
- evaluation is offline;
- no LLM is required;
- production news vendor remains NOT_SELECTED;
- no signal probability, risk or execution authority is introduced;
- LIVE_TRADING and AUTO_TRADING remain DISABLED.


## Canonical closure evidence
- implementation PR #237 = MERGED
- implementation merge SHA = `b5773f83aa94b4b083f57315bda9a35d26820094`
- final repaired head = `c6a9abfd4b9ed8b40565a7fb2cae257839e207fa`
- implementation artifact = `sha256:127350c8c9fd62414245f0fdef43c95dff6dda8ce762689bc1000a7be9c23ab1`
- superseded Governance `38128239548` = FAILURE / unused import / AUTO_REPAIRED
- implementation Governance `38128288674` = SUCCESS
- post-merge Governance `38128385783` = SUCCESS
- post-merge Branch Hygiene `38128385809` = SUCCESS
- mandatory scenarios = 8
- mandatory passed = 8
- mandatory failed = 0
- mandatory pass rate = 10000 bps / 100%
- FIN-P11-WH-001 = CANONICAL_COMPLETE
- LOCK-FIN-P11-WH-001-01 = RELEASED
- P11 = CANONICAL_COMPLETE
- P12 = OWNER_PHASE_AUTHORIZATION_REQUIRED
