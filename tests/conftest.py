import pytest

from main import WatchdogOrganizer


@pytest.fixture
def watch_dir(tmp_path):
    folder = tmp_path / "watch"
    folder.mkdir()
    return folder


@pytest.fixture
def dest_dir(tmp_path):
    return tmp_path / "dest"


@pytest.fixture
def organizer(watch_dir, dest_dir, monkeypatch):
    monkeypatch.setenv("FOLDER_TO_WATCH", str(watch_dir))
    monkeypatch.setenv("DESTINATION_FOLDER", str(dest_dir))
    return WatchdogOrganizer()


@pytest.fixture
def snapshot():
    """Returns a function mapping every file under the given folders to its bytes.

    Comparing snapshots before and after an action proves nothing moved.
    """

    def take(*folders):
        return {
            p: p.read_bytes()
            for folder in folders
            if folder.exists()
            for p in folder.rglob("*")
            if p.is_file()
        }

    return take
