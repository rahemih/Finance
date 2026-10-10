# P09-C — Volume Profile

Task: `FIN-P09-WC-001`  
Linear: `HOS-227`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P09-WC-001-01` / ACQUIRED  
Lead: A4 Quant  
Support: A0, A1, A2, A3, A6, A8, A9, A10

## Objective

Build a deterministic Volume Profile from governed actual trade prints, with explicit price buckets, Point of Control and Value Area while retaining provider/source scope and point-in-time integrity.

## Input boundary

The reference profile accepts only P09-B `TradePrint` inputs. Quote updates, tick-volume observations and generic activity proxies are not converted into synthetic trade volume.

For spot FX, only broker/ECN trade prints accepted by P09-B may be profiled. The resulting profile remains provider-scoped and cannot claim global or consolidated spot-FX volume.

## Bucket convention

For explicit bucket size `s > 0` and origin `o`:

`bucket_index = floor((trade_price - o) / s)`

Each bucket is the half-open range:

`[o + index*s, o + (index+1)*s)`

The complete occupied span is materialized, including zero-volume interior buckets, subject to a policy maximum of 10,000 buckets.

## POC

Point of Control is the bucket with maximum printed volume.

Tie-break: **lowest bucket price wins**. This rule is fixed in policy so reruns cannot choose a different POC.

## Value Area

Target: 70% of total printed volume.

Algorithm:

1. start at POC;
2. compare the immediately adjacent lower and upper buckets;
3. add the side with greater volume;
4. on equal adjacent volume, add the lower-price side first;
5. continue until cumulative included volume reaches or exceeds the target.

Outputs:
- `Value Area Low` = lower boundary of the lowest selected bucket;
- `Value Area High` = upper boundary of the highest selected bucket;
- achieved coverage is recorded in integer basis points.

This is a deterministic descriptive profile, not a trading signal.

## Fail-closed rules

- empty trade input;
- invalid/non-positive bucket size;
- mixed symbol/provider/venue/source/coverage stream;
- duplicate/out-of-order or non-contiguous sequence;
- reversed event time;
- source rejected by P09-B;
- excessive sparse bucket span;
- impossible value-area completion.

## Safety

- POC/VAH/VAL are descriptive market-structure evidence only.
- Quote/tick proxy profile: FORBIDDEN in P09-C.
- Production order-flow vendor: NOT_SELECTED.
- Country assumption: NONE.
- LIVE_TRADING: DISABLED.
- AUTO_TRADING: DISABLED.
- Direct trade/order/recommendation/probability authority: FORBIDDEN.
