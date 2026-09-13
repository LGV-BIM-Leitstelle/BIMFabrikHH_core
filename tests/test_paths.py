"""
Unit tests for path configuration helpers.
"""

from pathlib import Path

from BIMFabrikHH_core.config.paths import local_dir_or_raw


class TestLocalDirOrRaw:
    """Test cases for local_dir_or_raw."""

    def test_returns_existing_directory(self, tmp_path):
        """An existing directory comes back as a path this OS can open."""
        assert Path(local_dir_or_raw(str(tmp_path))) == tmp_path

    def test_keeps_remote_url_unchanged(self):
        """A remote root has no local directory, so it must survive untouched."""
        url = "https://example.org/datasets/dgm1"

        assert local_dir_or_raw(url) == url

    def test_keeps_unknown_path_unchanged(self, tmp_path):
        """An unresolvable path is returned so callers can report what failed."""
        missing = str(tmp_path / "missing")

        assert local_dir_or_raw(missing) == missing

    def test_keeps_empty_string_unchanged(self):
        assert local_dir_or_raw("") == ""

    def test_prefers_linux_spelling_over_windows(self, monkeypatch):
        """Deployment is Linux, so the ``/mnt`` form wins when both resolve."""
        monkeypatch.setattr(Path, "is_dir", lambda self: True)

        resolved = local_dir_or_raw(r"C:\datasets\dgm1")

        assert Path(resolved) == Path("/mnt/c/datasets/dgm1")
