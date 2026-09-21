#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

set -euo pipefail

: "${RELEASE_TOOL_PATH:?release-tool path is required}"
: "${RELEASE_CONFIG_PATH:?release config path is required}"
: "${RELEASE_ROOT:?release root is required}"
: "${RELEASE_REF:?release ref is required}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"

php "${RELEASE_TOOL_PATH}" config:validate 	--config "${RELEASE_CONFIG_PATH}" 	--root "${RELEASE_ROOT}"

metadata_file="${RUNNER_TEMP:-/tmp}/release-consumer-metadata-${RANDOM}-${RANDOM}.json"
trap 'rm -f "${metadata_file}"' EXIT

php "${RELEASE_TOOL_PATH}" metadata:inspect 	--config "${RELEASE_CONFIG_PATH}" 	--root "${RELEASE_ROOT}" 	--ref "${RELEASE_REF}" 	--json > "${metadata_file}"

php -r '
$metadata = json_decode(file_get_contents($argv[1]), true, 512, JSON_THROW_ON_ERROR);
foreach (["version", "major", "development", "changelog_path"] as $key) {
	if (!array_key_exists($key, $metadata)) {
		fwrite(STDERR, "Missing metadata field: {$key}\n");
		exit(2);
	}
}
printf("version=%s\n", $metadata["version"]);
printf("major=%s\n", $metadata["major"]);
printf("development=%s\n", $metadata["development"] ? "true" : "false");
printf("changelog-path=%s\n", $metadata["changelog_path"]);
' "${metadata_file}" >> "${GITHUB_OUTPUT}"
