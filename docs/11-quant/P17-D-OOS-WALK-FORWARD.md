# P17-D — Out-of-Sample / Walk-Forward

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P17-WD-001`

## Objective

Certify that strategy/model candidate selection is performed only on training/validation information and that final evaluation occurs on chronologically isolated out-of-sample test windows.

## Fold contract

Every fold explicitly defines half-open windows:

`train → validation → test`

The train and validation windows may touch at their boundaries. Validation must finish before the test window begins, leaving an explicit pre-test selection interval.

Test windows across folds must also be chronological and non-overlapping.

## Candidate selection

Every fold must carry one candidate-selection record with:
- candidate ID;
- selection timestamp;
- training artifact SHA-256;
- validation artifact SHA-256.

The selection timestamp must be at or after validation completion and strictly before the test window begins.

This prevents test-informed model/strategy selection.

## OOS result

Every fold must carry exactly one OOS result reference with:
- backtest result ID;
- exact test window;
- P17-C information-hygiene certificate ID.

The result window must match the fold test window exactly.

## Determinism

Folds, selections and results are canonicalized before certificate hashing.

Input ordering cannot change the certificate identity.

## Authority boundary

P17-D has no:
- G9 authority;
- profitability-claim authority;
- execution or routing authority;
- production-promotion authority.

P17-E..P17-I = NOT_STARTED.  
`G9_QUANT_VALIDATED` = NOT_REACHED.  
P18 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.
