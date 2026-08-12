#!/usr/bin/env bash
# Maintainer helper — compare vendored prayog-skills fixture tip to a remote tip.
# Not required in PR CI (pytest stays offline). Run when bumping kit tip.
#
# Usage:
#   scripts/check-fixture-pin.sh                  # vs remote HEAD
#   scripts/check-fixture-pin.sh features/rc-2    # vs that ref on origin
#   scripts/check-fixture-pin.sh d3bd94e          # vs that commit (must be on remote)
#
# Optional: FIXTURE_REMOTE=org/repo (default drivestream-lab/prayog-skills)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTRACT="${ROOT}/tests/fixtures/prayog-skills/delivery-contract.yaml"
REMOTE_SLUG="${FIXTURE_REMOTE:-drivestream-lab/prayog-skills}"
TIP_REF="${1:-HEAD}"

if [[ ! -f "${CONTRACT}" ]]; then
  echo "missing fixture contract: ${CONTRACT}" >&2
  exit 2
fi

header="$(head -n 1 "${CONTRACT}")"
if [[ ! "${header}" =~ @([0-9a-fA-F]{7,40}) ]]; then
  echo "could not parse vendored SHA from: ${header}" >&2
  exit 2
fi
VENDORED="$(echo "${BASH_REMATCH[1]}" | tr 'A-F' 'a-f')"

remote_url="https://github.com/${REMOTE_SLUG}.git"
echo "fixture header SHA: ${VENDORED}"
echo "remote:             ${REMOTE_SLUG}  tip ref: ${TIP_REF}"

mapfile -t lines < <(git ls-remote "${remote_url}" "${TIP_REF}" 2>/dev/null || true)
if [[ ${#lines[@]} -eq 0 ]]; then
  # SHA pins: ls-remote HEAD and see if object matches via API-less check —
  # try peeling common refs that contain the commit name as tip.
  mapfile -t lines < <(git ls-remote "${remote_url}" "refs/heads/${TIP_REF}" "refs/tags/${TIP_REF}" "${TIP_REF}" 2>/dev/null || true)
fi

tip=""
for line in "${lines[@]:-}"; do
  [[ -z "${line}" ]] && continue
  sha="${line%%[[:space:]]*}"
  name="${line#*$'\t'}"
  # Prefer peeled annotated tag
  if [[ "${name}" == *'^{}' ]]; then
    tip="${sha}"
    break
  fi
  tip="${sha}"
done

if [[ -z "${tip}" ]]; then
  # Allow comparing fixture SHA prefix to an explicit full SHA argument
  if [[ "${TIP_REF}" =~ ^[0-9a-fA-F]{7,40}$ ]]; then
    tip="$(echo "${TIP_REF}" | tr 'A-F' 'a-f')"
  else
    echo "could not resolve tip ${TIP_REF!r} on ${REMOTE_SLUG}" >&2
    exit 2
  fi
fi

tip="$(echo "${tip}" | tr 'A-F' 'a-f')"
echo "resolved tip SHA:   ${tip}"

if [[ "${tip}" == "${VENDORED}"* || "${VENDORED}" == "${tip:0:${#VENDORED}}" ]]; then
  echo "OK — fixture tip matches resolved tip"
  exit 0
fi

echo "STALE — fixture @ ${VENDORED} ≠ tip ${tip}"
echo "Re-vendor tests/fixtures/prayog-skills/ and update the header comment."
exit 1
