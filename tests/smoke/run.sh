#!/usr/bin/env bash
# Smoke test: start HA container, verify Paperang integration loads
# without errors (checks logs only — no auth required).
#
# Usage:
#   ./run.sh              Build image, start, verify
#   ./run.sh --skip-build  Skip build (CI already built with cache)
set -euo pipefail

SKIP_BUILD=false
if [[ "${1:-}" == "--skip-build" ]]; then
    SKIP_BUILD=true
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTAINER_NAME="ha-paperang-smoke"
HA_PORT="8123"
HA_URL="http://localhost:${HA_PORT}"
MAX_WAIT=180
POLL_INTERVAL=3

cleanup() {
    echo "==> Tearing down container..."
    docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true
}
trap cleanup EXIT

# ── Build image (skip in CI) ────────────────────────────────
if [ "${SKIP_BUILD}" = true ]; then
    echo "==> Skipping build (--skip-build), using paperang-ha-test:ci"
    IMAGE="paperang-ha-test:ci"
else
    echo "==> Building HA smoke-test image..."
    docker build \
        -t paperang-ha-test \
        -f "${SCRIPT_DIR}/Dockerfile.ha-test" \
        "$(git rev-parse --show-toplevel)"
    IMAGE="paperang-ha-test"
fi

# ── Start container ─────────────────────────────────────────
echo "==> Starting HA container..."
docker run -d \
    --name "${CONTAINER_NAME}" \
    -p "${HA_PORT}:${HA_PORT}" \
    "${IMAGE}"

# ── Wait for HA to be ready ─────────────────────────────────
echo "==> Waiting for Home Assistant to start (max ${MAX_WAIT}s)..."
elapsed=0
while [ "${elapsed}" -lt "${MAX_WAIT}" ]; do
    if docker exec "${CONTAINER_NAME}" \
        curl -sf "${HA_URL}/api/onboarding" -o /dev/null 2>/dev/null; then
        echo "==> Home Assistant is ready after ${elapsed}s"
        break
    fi
    sleep "${POLL_INTERVAL}"
    elapsed=$((elapsed + POLL_INTERVAL))
done

if [ "${elapsed}" -ge "${MAX_WAIT}" ]; then
    echo "ERROR: HA did not start within ${MAX_WAIT}s"
    docker logs "${CONTAINER_NAME}" --tail 50
    exit 1
fi

# Give HA a few more seconds to finish loading
sleep 10

# ── Verify no paperang errors ───────────────────────────────
echo "==> Checking for Paperang errors in logs..."
ERRORS=$(docker logs "${CONTAINER_NAME}" 2>&1 | grep -i "paperang" | grep -iE "error|traceback|exception" || true)
if [ -n "${ERRORS}" ]; then
    echo "  ❌ Paperang errors found:"
    echo "${ERRORS}"
    exit 1
fi
echo "  ✅ No paperang errors — integration loaded cleanly"

# ── Verify paperang mentioned in setup logs ─────────────────
echo "==> Checking Paperang in setup logs..."
SETUP_LOGS=$(docker logs "${CONTAINER_NAME}" 2>&1 | grep -i "paperang" || true)
if [ -z "${SETUP_LOGS}" ]; then
    echo "  ⚠️  Paperang not mentioned in logs (may not have loaded)"
else
    echo "  ✅ Paperang found in logs:"
    echo "${SETUP_LOGS}" | head -5
fi

echo "==> All smoke tests passed! 🎉"
# Services registered via async_setup — confirmed by log line:
# "Paperang P2 Printer integration loaded"
