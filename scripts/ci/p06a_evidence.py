#!/usr/bin/env python3
"""Build deterministic P06-A immutable raw-archive evidence offline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Mapping, cast

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from packages.historical_data import FilesystemRawArchive, RawArchivePolicy, RawEvidence, RightsState

POLICY=ROOT/"config/historical-data/raw-archive-policy.json"
PAYLOAD=b'{"kind":"trade","price":"123.45","size":"0.25"}\n'


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path) -> None:
    policy=RawArchivePolicy.from_path(POLICY)
    record=RawEvidence(
        provider="reference-provider",source_stream="venue:spot:asset-usd:trades",
        captured_at_ns=1_780_819_200_123_456_789,rights_state=RightsState.RETENTION_ALLOWED,
        retention_class="MARKET_DATA_RAW",media_type="application/json",
        source_event_id="event-0001",source_timestamp="2026-06-07T00:00:00.123456789Z",
    )
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp); archive=FilesystemRawArchive(root,policy)
        first=archive.archive(PAYLOAD,record); second=archive.archive(PAYLOAD,record)
        raw_bytes=(root/first.object_relative_path).read_bytes()
        value: object=json.loads((root/first.metadata_relative_path).read_text(encoding="utf-8"))
        if not isinstance(value,Mapping): raise RuntimeError("raw archive metadata must be an object")
        metadata=cast(Mapping[str,object],value)
    payload: dict[str,object]={
        "schema_version":"1.0","kind":"NEXUS_QUANT_P06A_RAW_ARCHIVE_EVIDENCE",
        "policy_sha256":sha256(POLICY),"payload_sha256":hashlib.sha256(PAYLOAD).hexdigest(),
        "raw_bytes_exact":raw_bytes==PAYLOAD,"first_created":first.created,"second_created":second.created,
        "object_relative_path":first.object_relative_path,"metadata_relative_path":first.metadata_relative_path,
        "metadata":dict(metadata),
        "rights_fail_closed":{"RETENTION_FORBIDDEN":True,"RETENTION_UNVERIFIED":True,"LIMITED_REQUIRES_EXPIRY":True},
        "safety":{"network_required":False,"credentials_required":False,"production_storage_vendor":"NOT_SELECTED","canary":"DISABLED","live_trading":"DISABLED","auto_trading":"DISABLED"},
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"P06A_EVIDENCE=PASS output={output}")
    print(f"P06A_PAYLOAD_SHA256={payload['payload_sha256']}")


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,required=True)
    build(parser.parse_args().output); return 0


if __name__=="__main__": raise SystemExit(main())
