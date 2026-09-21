#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

set -euo pipefail

version="${RELEASE_TOOL_VERSION:-}"
if [[ -z "${version}" ]]; then
	version_file="${GITHUB_ACTION_PATH:?github action path is required}/release-tool-version"
	version="$(tr -d '[:space:]' < "${version_file}")"
fi

if [[ ! "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
	echo "::error::release-tool version must be an exact semantic version, got '${version}'"
	exit 2
fi

case "${version}" in
	latest|stable|main|master|*'*'*|*'^'*|*'~'*|*'>'*|*'<'*)
		echo "::error::floating release-tool versions are forbidden"
		exit 2
		;;
esac

install_root="${RUNNER_TEMP:-/tmp}/librecode-release-tool/${version}"
mkdir -p "${install_root}"

base_url="https://github.com/LibreCodeCoop/release-tool/releases/download/v${version}"
phar="${install_root}/release-tool.phar"
checksum="${install_root}/release-tool.phar.sha256"

curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 	"${base_url}/release-tool.phar" --output "${phar}"
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 	"${base_url}/release-tool.phar.sha256" --output "${checksum}"

expected="$(awk 'NR == 1 {print $1}' "${checksum}")"
if [[ ! "${expected}" =~ ^[0-9a-fA-F]{64}$ ]]; then
	echo "::error::published release-tool checksum is malformed"
	exit 3
fi

actual="$(sha256sum "${phar}" | awk '{print $1}')"
if [[ "${actual,,}" != "${expected,,}" ]]; then
	echo "::error::release-tool checksum mismatch"
	exit 3
fi

chmod 0755 "${phar}"
php "${phar}" --version >/dev/null

{
	echo "path=${phar}"
	echo "version=${version}"
} >> "${GITHUB_OUTPUT}"

echo "${install_root}" >> "${GITHUB_PATH}"
echo "Installed release-tool ${version} with verified SHA-256."
