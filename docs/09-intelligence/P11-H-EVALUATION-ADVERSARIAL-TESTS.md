# P11-H — Evaluation / Adversarial Tests

Task: `FIN-P11-WH-001`  
Linear: `HOS-249`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P11-WH-001-01` / ACQUIRED  
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
