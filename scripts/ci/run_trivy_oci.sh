#!/usr/bin/env bash
# P24-CI: immutable Trivy v0.75.0 OCI scanner, NOT a security scan waiver.
# On network, image, database, policy, JSON or scanner error: exit nonzero.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ROOT="$(pwd -P)"
if [[ ! -f "${ROOT}/.trivyignore" || ! -f "${ROOT}/config/supply-chain/dependency-policy.json" ]]; then
  echo "TRIVY_REQUIRED_POLICY_MISSING" >&2
  exit 1
fi
command -v docker >/dev/null || { echo "TRIVY_DOCKER_UNAVAILABLE" >&2; exit 1; }

# Source: Aqua Security official GHCR and Docker Hub published linux/amd64
# image for exact v0.75.0. Docker verifies the immutable OCI manifest digest.
# This is NOT a floating tag, and no unverified registry is ever used.
DIGEST="sha256:9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283"
GHCR="ghcr.io/aquasecurity/trivy@${DIGEST}"
DOCKER_HUB="docker.io/aquasec/trivy@${DIGEST}"
if docker pull --platform linux/amd64 "${GHCR}"; then
  image="${GHCR}"
elif docker pull --platform linux/amd64 "${DOCKER_HUB}"; then
  image="${DOCKER_HUB}"
else
  echo "TRIVY_PINNED_OFFICIAL_IMAGE_UNAVAILABLE" >&2
  exit 1
fi

# Refuse a mismatched binary even when the digest pull succeeds.
version="$(docker run --rm --platform linux/amd64 --network none \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  "${image}" --version)"
if ! grep -Fxq 'Version: 0.75.0' <<< "${version}"; then
  echo "TRIVY_BINARY_VERSION_MISMATCH" >&2
  exit 1
fi

mkdir -p "${ROOT}/build"
cache_root="${RUNNER_TEMP:-${ROOT}/build}/trivy-oci-cache"
mkdir -p "${cache_root}"
# Never accept an old JSON left by an earlier build or a failed scan.
rm -f "${ROOT}/build/trivy.json"

# No Docker socket, no privileged mode, no root in the scanner, read-only
# repository mount and root filesystem. Only DB cache and scanner output
# receive writable mounts; network is required for the up-to-date vuln DB.
docker run --rm --platform linux/amd64 \
  --user "$(id -u):$(id -g)" \
  --read-only --tmpfs /tmp:rw,noexec,nosuid \
  --cap-drop ALL --security-opt no-new-privileges \
  --network bridge \
  --volume "${ROOT}:/scan:ro" \
  --volume "${ROOT}/build:/out:rw" \
  --volume "${cache_root}:/cache:rw" \
  --env TRIVY_CACHE_DIR=/cache \
  --workdir /scan \
  "${image}" fs \
  --scanners vuln,misconfig,secret \
  --severity HIGH,CRITICAL \
  --exit-code 1 \
  --format json \
  --output /out/trivy.json \
  --ignorefile /scan/.trivyignore \
  /scan

# A successful return code with a missing, malformed or tampered JSON is NOT
# a pass. The validation independently rechecks all three finding families.
python3 scripts/ci/verify_trivy_scan.py --report build/trivy.json
echo "TRIVY_OCI_SCANNER_VERIFIED=PASS image_digest=${DIGEST}"
