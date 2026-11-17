#!/bin/bash
# ===========================================================================
# HAL 9000 — AI sidecar installer (Raspberry Pi)
# ===========================================================================
#   sudo ./install_sidecar.sh
#
# Installs hal9000-sidecar.service and prepares /etc/hal9000/env, the one
# place on the machine that holds the Anthropic API key.
#
# This script NEVER handles the key itself.
#
# It does not read it, prompt for it, accept it as an argument, print it,
# or write it anywhere. It creates an empty root-owned 0600 file and tells
# you to put the key in with an editor. That is deliberate: a key passed on
# a command line is visible in `ps` and lands in shell history, and a key
# captured with `read` lands in the history of any shell with a careless
# HISTCONTROL. The only safe handler of a secret here is a text editor
# writing straight to a 0600 file.
# ===========================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="hal9000-sidecar"
ENV_DIR="/etc/hal9000"
ENV_FILE="${ENV_DIR}/env"
RUN_USER="${SUDO_USER:-pi}"

if [[ $EUID -ne 0 ]]; then
  echo "This installer must run as root:  sudo ./install_sidecar.sh" >&2
  exit 1
fi

echo "============================================"
echo "  HAL 9000 — AI sidecar install"
echo "============================================"

# ---------------------------------------------------------------------------
# 1. The env file — created empty, never populated by this script
# ---------------------------------------------------------------------------
echo "[1/4] Preparing ${ENV_FILE}"

install -d -m 0700 -o root -g root "${ENV_DIR}"

if [[ -f "${ENV_FILE}" ]]; then
  echo "  • ${ENV_FILE} already exists — left untouched."
else
  # Create with restrictive permissions BEFORE any content exists, so the
  # file is never briefly world-readable.
  install -m 0600 -o root -g root /dev/null "${ENV_FILE}"
  cat > "${ENV_FILE}" <<'TEMPLATE'
# HAL 9000 sidecar environment. Mode 0600, root-owned.
# Put the Anthropic API key on the line below, with no quotes and no export.
#
#   ANTHROPIC_API_KEY=sk-ant-...
#
ANTHROPIC_API_KEY=
TEMPLATE
  echo "  ✓ created, mode 0600, root-owned"
fi

chown root:root "${ENV_FILE}"
chmod 0600 "${ENV_FILE}"

# ---------------------------------------------------------------------------
# 2. The unit
# ---------------------------------------------------------------------------
echo "[2/4] Installing ${SERVICE_NAME}.service"

sed "s|INSTALL_DIR|${SCRIPT_DIR}|g" "${SCRIPT_DIR}/${SERVICE_NAME}.service" \
  | sed "s|^User=pi$|User=${RUN_USER}|" \
  > "/etc/systemd/system/${SERVICE_NAME}.service"
chmod 0644 "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
echo "  ✓ unit installed (User=${RUN_USER}, WorkingDirectory=${SCRIPT_DIR})"

# ---------------------------------------------------------------------------
# 3. Is a key present yet?
# ---------------------------------------------------------------------------
echo "[3/4] Checking for a configured key"

# Test for a non-empty value WITHOUT reading, printing or expanding it.
if grep -Eq '^ANTHROPIC_API_KEY=.+' "${ENV_FILE}"; then
  KEY_PRESENT=yes
  echo "  ✓ a key is present in ${ENV_FILE}"
else
  KEY_PRESENT=no
  echo "  • no key set yet"
fi

# ---------------------------------------------------------------------------
# 4. Enable
# ---------------------------------------------------------------------------
echo "[4/4] Enabling the service"
systemctl enable "${SERVICE_NAME}" >/dev/null 2>&1
echo "  ✓ enabled at boot"

echo
echo "============================================"
if [[ "${KEY_PRESENT}" == "no" ]]; then
  cat <<INSTRUCTIONS
  Add the key yourself, with an editor:

      sudo nano ${ENV_FILE}

  Put it after ANTHROPIC_API_KEY= on one line, save, then:

      sudo systemctl start ${SERVICE_NAME}

  Do NOT use a shell one-liner such as
      echo "ANTHROPIC_API_KEY=sk-ant-..." | sudo tee ${ENV_FILE}
  or a 'read' prompt. Both put the key in shell history.
INSTRUCTIONS
else
  cat <<INSTRUCTIONS
  Start it with:

      sudo systemctl start ${SERVICE_NAME}

INSTRUCTIONS
fi
cat <<CHECKS
  Verify (neither command prints the key):

      systemctl status ${SERVICE_NAME}
      curl -s http://127.0.0.1:3001/api/health

  Health should report {"ok": true, ...}. If it reports false, the key
  in ${ENV_FILE} is empty or wrong.

  The sidecar listens on 127.0.0.1 only. Confirm with:

      ss -ltnp | grep 3001
CHECKS
echo "============================================"
