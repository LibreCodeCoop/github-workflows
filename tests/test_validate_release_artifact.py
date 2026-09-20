# SPDX-FileCopyrightText: 2026 LibreCode coop and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.validate_release_artifact import validate_artifact


class ValidateReleaseArtifactTest(unittest.TestCase):
    def create_archive(
        self,
        directory: str,
        *,
        app_name: str = "example_app",
        version: str = "1.2.3",
        info_path: str | None = None,
        extra_name: str | None = None,
    ) -> Path:
        artifact = Path(directory) / "artifact.tar.gz"
        info = (
            f"<info><id>{app_name}</id><version>{version}</version></info>"
        ).encode()
        with tarfile.open(artifact, "w:gz") as archive:
            member = tarfile.TarInfo(
                info_path or f"{app_name}/appinfo/info.xml"
            )
            member.size = len(info)
            archive.addfile(member, io.BytesIO(info))

            if extra_name is not None:
                extra = tarfile.TarInfo(extra_name)
                extra.size = 1
                archive.addfile(extra, io.BytesIO(b"x"))

        return artifact

    def test_accepts_expected_app_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.create_archive(directory)
            validate_artifact(artifact, "example_app", "1.2.3")

    def test_rejects_version_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.create_archive(directory, version="1.2.2")
            with self.assertRaisesRegex(ValueError, "expected '1.2.3'"):
                validate_artifact(artifact, "example_app", "1.2.3")

    def test_rejects_multiple_top_level_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.create_archive(
                directory,
                extra_name="other/file.txt",
            )
            with self.assertRaisesRegex(ValueError, "top-level directory"):
                validate_artifact(artifact, "example_app", "1.2.3")

    def test_rejects_missing_info_xml(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.create_archive(
                directory,
                info_path="example_app/not-appinfo/info.xml",
            )
            with self.assertRaisesRegex(ValueError, "missing"):
                validate_artifact(artifact, "example_app", "1.2.3")

    def test_rejects_unsafe_archive_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.create_archive(
                directory,
                extra_name="../escape",
            )
            with self.assertRaisesRegex(ValueError, "unsafe archive path"):
                validate_artifact(artifact, "example_app", "1.2.3")


if __name__ == "__main__":
    unittest.main()
