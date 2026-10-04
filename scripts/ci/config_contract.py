#!/usr/bin/env python3
"""Validate NEXUS QUANT P04-D non-secret config/environment contracts."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
ENV_DIR = CONFIG / "environments"

EXPECTED = {
    "DEV": ("dev.json", "SIMULATED_ONLY", "secret://dev/"),
    "TEST": ("test.json", "SIMULATED_ONLY", "secret://test/"),
    "RESEARCH": ("research.json", "SIMULATED_ONLY", "secret://research/"),
    "DEMO": ("demo.json", "DEMO_ONLY", "secret://demo/"),
    "SHADOW": ("shadow.json", "SHADOW_ONLY", "secret://shadow/"),
    "CANARY": ("canary.json", "CANARY_DISABLED", "secret://canary/"),
    "LIVE": ("live.json", "LIVE_DISABLED", "secret://live/"),
}
ALLOWED_OVERRIDE_PATHS = {
    "settings.log_level",
    "settings.clock_mode",
    "settings.data_mode",
}
EXPECTED_ENV_KEYS = {
    "schema_version",
    "environment",
    "inherits",
    "config_version",
    "provisioning_state",
    "authority_ceiling",
    "safety",
    "execution",
    "credentials",
    "settings",
}
EXPECTED_SAFETY_KEYS = {"live_trading", "auto_trading", "withdrawals", "transfers"}
EXPECTED_EXECUTION_KEYS = {"active_mode", "external_order_submission"}
EXPECTED_CREDENTIAL_KEYS = {"authority_provisioned", "secret_namespace", "secret_refs"}
EXPECTED_SETTING_KEYS = {"log_level", "clock_mode", "data_mode"}

SECRET_REF_RE = re.compile(
    r"^secret://(dev|test|research|demo|shadow|canary|live)/"
    r"[a-z0-9-]+/[a-z0-9._-]+@[a-z0-9._-]+$"
)
PROHIBITED_RAW_KEYS = {
    "password",
    "passwd",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "bearer_token",
    "client_secret",
    "private_key",
    "secret_value",
    "credential_value",
}
PROHIBITED_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{16,}\b", re.IGNORECASE),
)


class ConfigFailure(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ConfigFailure(message)


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"CONFIG_JSON_INVALID path={path.relative_to(ROOT)} error={exc}")
    if not isinstance(value, dict):
        fail(f"CONFIG_OBJECT_REQUIRED path={path.relative_to(ROOT)}")
    return value


def exact_keys(value: dict, expected: set[str], path: str) -> None:
    keys = set(value)
    if keys != expected:
        missing = sorted(expected - keys)
        extra = sorted(keys - expected)
        fail(f"CONFIG_KEYS_INVALID path={path} missing={missing} extra={extra}")


def scan_for_raw_secrets(value, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.lower()
            if normalized in PROHIBITED_RAW_KEYS:
                fail(f"RAW_SECRET_KEY_FORBIDDEN path={path}.{key}")
            scan_for_raw_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_for_raw_secrets(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if value.startswith("secret://"):
            return
        for pattern in PROHIBITED_VALUE_PATTERNS:
            if pattern.search(value):
                fail(f"RAW_SECRET_VALUE_FORBIDDEN path={path}")


def validate_policy() -> dict:
    policy = load(CONFIG / "config-policy.json")
    if policy.get("schema_version") != "1.0":
        fail("POLICY_SCHEMA_VERSION_INVALID")
    if policy.get("environments") != list(EXPECTED):
        fail("POLICY_ENVIRONMENT_ORDER_OR_SET_INVALID")
    if policy.get("invalid_config_behavior") != "FAIL_CLOSED":
        fail("POLICY_INVALID_CONFIG_NOT_FAIL_CLOSED")
    if policy.get("unknown_environment_behavior") != "FAIL_CLOSED":
        fail("POLICY_UNKNOWN_ENVIRONMENT_NOT_FAIL_CLOSED")

    override = policy.get("runtime_override", {})
    if set(override.get("allowed_paths", [])) != ALLOWED_OVERRIDE_PATHS:
        fail("POLICY_OVERRIDE_ALLOWLIST_INVALID")
    if override.get("fail_on_unknown_path") is not True:
        fail("POLICY_UNKNOWN_OVERRIDE_NOT_FAIL_CLOSED")

    universal = policy.get("universal_safety", {})
    expected_false = (
        "authority_provisioned",
        "external_order_submission",
        "live_trading",
        "auto_trading",
        "withdrawals",
        "transfers",
        "authorization_location_dependency",
    )
    for key in expected_false:
        if universal.get(key) is not False:
            fail(f"POLICY_UNIVERSAL_SAFETY_INVALID key={key}")
    if universal.get("provisioning_state") != "CONTRACT_ONLY":
        fail("POLICY_PROVISIONING_STATE_INVALID")
    if universal.get("active_execution_mode") != "DISABLED":
        fail("POLICY_EXECUTION_MODE_INVALID")

    secret = policy.get("secret_reference", {})
    if secret.get("scheme") != "secret://":
        fail("POLICY_SECRET_SCHEME_INVALID")
    if secret.get("raw_secret_values_in_canonical_config") is not False:
        fail("POLICY_RAW_SECRET_VALUES_NOT_FORBIDDEN")
    if secret.get("environment_segment_must_match_owner") is not True:
        fail("POLICY_SECRET_ENV_MATCH_NOT_REQUIRED")
    if secret.get("lower_environment_can_reference_canary_or_live") is not False:
        fail("POLICY_LOWER_ENV_CAN_REFERENCE_HIGH_ENV")

    scan_for_raw_secrets(policy)
    return policy


def validate_schema() -> None:
    schema = load(CONFIG / "environment-config.schema.json")
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        fail("CONFIG_SCHEMA_DIALECT_INVALID")
    props = schema.get("properties", {})
    env_enum = props.get("environment", {}).get("enum")
    if env_enum != list(EXPECTED):
        fail("CONFIG_SCHEMA_ENVIRONMENT_ENUM_INVALID")
    if props.get("provisioning_state", {}).get("const") != "CONTRACT_ONLY":
        fail("CONFIG_SCHEMA_PROVISIONING_CONST_INVALID")


def validate_base() -> None:
    base = load(CONFIG / "base.json")
    if base.get("schema_version") != "1.0":
        fail("BASE_SCHEMA_VERSION_INVALID")
    if base.get("kind") != "BASE_NON_SECRET_DEFAULTS":
        fail("BASE_KIND_INVALID")
    rules = base.get("rules", {})
    if rules.get("unknown_key_behavior") != "FAIL_CLOSED":
        fail("BASE_UNKNOWN_KEY_NOT_FAIL_CLOSED")
    if rules.get("secret_values") != "FORBIDDEN":
        fail("BASE_SECRET_VALUES_NOT_FORBIDDEN")
    if rules.get("location_as_authorization_input") != "FORBIDDEN":
        fail("BASE_LOCATION_AUTH_NOT_FORBIDDEN")
    if rules.get("runtime_override_authority_widening") != "FORBIDDEN":
        fail("BASE_AUTHORITY_WIDENING_NOT_FORBIDDEN")
    scan_for_raw_secrets(base)


def validate_environment(env: str, filename: str, ceiling: str, namespace: str) -> None:
    path = ENV_DIR / filename
    value = load(path)
    exact_keys(value, EXPECTED_ENV_KEYS, str(path.relative_to(ROOT)))

    if value["schema_version"] != "1.0":
        fail(f"ENV_SCHEMA_VERSION_INVALID env={env}")
    if value["environment"] != env:
        fail(f"ENV_IDENTITY_INVALID env={env}")
    if value["inherits"] != "config/base.json":
        fail(f"ENV_INHERITANCE_INVALID env={env}")
    if value["config_version"] != 1:
        fail(f"ENV_CONFIG_VERSION_INVALID env={env}")
    if value["provisioning_state"] != "CONTRACT_ONLY":
        fail(f"ENV_PROVISIONING_STATE_INVALID env={env}")
    if value["authority_ceiling"] != ceiling:
        fail(f"ENV_AUTHORITY_CEILING_INVALID env={env}")

    safety = value["safety"]
    exact_keys(safety, EXPECTED_SAFETY_KEYS, f"{env}.safety")
    if any(safety[key] is not False for key in EXPECTED_SAFETY_KEYS):
        fail(f"ENV_SAFETY_ENABLE_FORBIDDEN env={env}")

    execution = value["execution"]
    exact_keys(execution, EXPECTED_EXECUTION_KEYS, f"{env}.execution")
    if execution["active_mode"] != "DISABLED":
        fail(f"ENV_EXECUTION_MODE_FORBIDDEN env={env}")
    if execution["external_order_submission"] is not False:
        fail(f"ENV_EXTERNAL_ORDER_SUBMISSION_FORBIDDEN env={env}")

    credentials = value["credentials"]
    exact_keys(credentials, EXPECTED_CREDENTIAL_KEYS, f"{env}.credentials")
    if credentials["authority_provisioned"] is not False:
        fail(f"ENV_CREDENTIAL_AUTHORITY_FORBIDDEN env={env}")
    if credentials["secret_namespace"] != namespace:
        fail(f"ENV_SECRET_NAMESPACE_INVALID env={env}")

    refs = credentials["secret_refs"]
    if not isinstance(refs, dict):
        fail(f"ENV_SECRET_REFS_OBJECT_REQUIRED env={env}")
    expected_segment = env.lower()
    for name, ref in refs.items():
        if not isinstance(name, str) or not isinstance(ref, str):
            fail(f"ENV_SECRET_REF_TYPE_INVALID env={env}")
        match = SECRET_REF_RE.fullmatch(ref)
        if match is None:
            fail(f"ENV_SECRET_REF_FORMAT_INVALID env={env} ref={name}")
        if match.group(1) != expected_segment:
            fail(f"ENV_SECRET_REF_CROSS_ENV_FORBIDDEN env={env} ref={name}")

    settings = value["settings"]
    exact_keys(settings, EXPECTED_SETTING_KEYS, f"{env}.settings")
    if settings["log_level"] not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        fail(f"ENV_LOG_LEVEL_INVALID env={env}")
    if settings["clock_mode"] not in {"SYSTEM", "DETERMINISTIC", "REPLAY"}:
        fail(f"ENV_CLOCK_MODE_INVALID env={env}")
    if settings["data_mode"] not in {"FIXTURE", "RECORDED", "EXTERNAL_READ_ONLY", "NONE"}:
        fail(f"ENV_DATA_MODE_INVALID env={env}")

    if env in {"CANARY", "LIVE"} and not ceiling.endswith("_DISABLED"):
        fail(f"HIGH_ENVIRONMENT_NOT_DISABLED env={env}")
    if env == "SHADOW" and execution["external_order_submission"] is not False:
        fail("SHADOW_ORDER_SUBMISSION_FORBIDDEN")

    scan_for_raw_secrets(value)


def validate_inventory() -> None:
    actual = {path.name for path in ENV_DIR.glob("*.json")}
    expected = {item[0] for item in EXPECTED.values()}
    if actual != expected:
        fail(f"ENVIRONMENT_FILE_SET_INVALID expected={sorted(expected)} actual={sorted(actual)}")


def validate_override_example() -> None:
    value = load(CONFIG / "runtime-overrides.example.json")
    if value.get("schema_version") != "1.0":
        fail("OVERRIDE_SCHEMA_VERSION_INVALID")
    if value.get("environment") not in EXPECTED:
        fail("OVERRIDE_ENVIRONMENT_INVALID")
    overrides = value.get("overrides")
    if not isinstance(overrides, dict):
        fail("OVERRIDE_OBJECT_REQUIRED")
    unknown = sorted(set(overrides) - ALLOWED_OVERRIDE_PATHS)
    if unknown:
        fail(f"OVERRIDE_PATH_FORBIDDEN paths={unknown}")

    for path, setting in overrides.items():
        if path == "settings.log_level" and setting not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            fail("OVERRIDE_LOG_LEVEL_INVALID")
        if path == "settings.clock_mode" and setting not in {"SYSTEM", "DETERMINISTIC", "REPLAY"}:
            fail("OVERRIDE_CLOCK_MODE_INVALID")
        if path == "settings.data_mode" and setting not in {"FIXTURE", "RECORDED", "EXTERNAL_READ_ONLY", "NONE"}:
            fail("OVERRIDE_DATA_MODE_INVALID")
    scan_for_raw_secrets(value)


def validate_all_json() -> None:
    for path in sorted(CONFIG.rglob("*.json")):
        load(path)


def main() -> int:
    try:
        validate_all_json()
        validate_schema()
        validate_policy()
        validate_base()
        validate_inventory()
        for env, (filename, ceiling, namespace) in EXPECTED.items():
            validate_environment(env, filename, ceiling, namespace)
        validate_override_example()
    except ConfigFailure as exc:
        print(f"CONFIG_CONTRACT=FAIL error={exc}")
        return 1

    print("CONFIG_CONTRACT=PASS")
    print(f"ENVIRONMENTS={','.join(EXPECTED)}")
    print("PROVISIONING=CONTRACT_ONLY")
    print("RAW_SECRETS=FORBIDDEN")
    print("CANARY=DISABLED")
    print("LIVE_TRADING=DISABLED")
    print("AUTO_TRADING=DISABLED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
