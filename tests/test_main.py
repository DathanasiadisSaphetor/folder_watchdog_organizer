import logging
import shutil

import magic
import pytest

from main import WatchdogOrganizer
from tests.factories import ArgsFactory, DiskFileFactory


# --------------------------------------------------------------------------- #
# __init__
# --------------------------------------------------------------------------- #
class TestInit:
    def test_raises_when_folder_to_watch_is_not_set(self, monkeypatch):
        monkeypatch.delenv("FOLDER_TO_WATCH", raising=False)

        with pytest.raises(ValueError, match="FOLDER_TO_WATCH environment variable is not set"):
            WatchdogOrganizer()

    def test_raises_when_folder_to_watch_does_not_exist(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FOLDER_TO_WATCH", str(tmp_path / "missing"))

        with pytest.raises(ValueError, match="not a directory"):
            WatchdogOrganizer()

    def test_raises_when_folder_to_watch_is_a_file(self, tmp_path, monkeypatch):
        file = DiskFileFactory(folder=tmp_path)
        monkeypatch.setenv("FOLDER_TO_WATCH", str(file.path))

        with pytest.raises(ValueError, match="not a directory"):
            WatchdogOrganizer()

    def test_destination_defaults_to_organized_inside_watch_folder(self, watch_dir, monkeypatch):
        monkeypatch.setenv("FOLDER_TO_WATCH", str(watch_dir))
        monkeypatch.delenv("DESTINATION_FOLDER", raising=False)

        organizer = WatchdogOrganizer()

        assert organizer.destination_folder == watch_dir / "Organized"

    def test_every_category_has_a_capitalized_destination_folder(self, organizer, dest_dir):
        assert organizer.destination_folders == {
            key: dest_dir / key.capitalize() for key in WatchdogOrganizer.MIME_TYPES
        }

    def test_init_creates_nothing_on_disk(self, organizer, dest_dir):
        assert not dest_dir.exists()


# --------------------------------------------------------------------------- #
# is_safe_to_move_from_desktop
# --------------------------------------------------------------------------- #
class TestIsSafeToMove:
    def test_regular_file_is_safe(self, organizer, watch_dir):
        file = DiskFileFactory(folder=watch_dir, name="report.pdf")

        assert organizer.is_safe_to_move_from_desktop(file.path) is True

    def test_accepts_string_paths(self, organizer, watch_dir):
        file = DiskFileFactory(folder=watch_dir, name="report.pdf")

        assert organizer.is_safe_to_move_from_desktop(str(file.path)) is True

    def test_directory_is_not_safe(self, organizer, watch_dir):
        folder = watch_dir / "subfolder"
        folder.mkdir()

        assert organizer.is_safe_to_move_from_desktop(folder) is False

    def test_missing_path_is_not_safe(self, organizer, watch_dir):
        assert organizer.is_safe_to_move_from_desktop(watch_dir / "ghost.txt") is False

    @pytest.mark.parametrize("name", ["desktop.ini", "Desktop.ini", "Thumbs.db", "THUMBS.DB"])
    def test_system_files_are_not_safe_case_insensitively(self, organizer, watch_dir, name):
        file = DiskFileFactory(folder=watch_dir, name=name)

        assert organizer.is_safe_to_move_from_desktop(file.path) is False

    @pytest.mark.parametrize(
        "name",
        [
            "shortcut.lnk",
            "site.url",
            "app.desktop",
            "movie.mkv.crdownload",
            "movie.mkv.part",
            "movie.mkv.download",
            "scratch.tmp",
            "UPPER.PART",
        ],
    )
    def test_shortcuts_and_in_progress_downloads_are_not_safe(self, organizer, watch_dir, name):
        file = DiskFileFactory(folder=watch_dir, name=name)

        assert organizer.is_safe_to_move_from_desktop(file.path) is False

    def test_hidden_file_is_not_safe(self, organizer, watch_dir):
        file = DiskFileFactory(folder=watch_dir, name=".bashrc")

        assert organizer.is_safe_to_move_from_desktop(file.path) is False

    def test_office_lock_file_is_not_safe(self, organizer, watch_dir):
        file = DiskFileFactory(folder=watch_dir, name="~$budget.xlsx")

        assert organizer.is_safe_to_move_from_desktop(file.path) is False

    def test_symlink_to_a_regular_file_is_not_safe(self, organizer, watch_dir, tmp_path):
        # Regression: is_file() follows links, so the symlink check must come first.
        target = DiskFileFactory(folder=tmp_path / "elsewhere", name="real.pdf")
        link = watch_dir / "link.pdf"
        link.symlink_to(target.path)

        assert organizer.is_safe_to_move_from_desktop(link) is False


# --------------------------------------------------------------------------- #
# determine_categories
# --------------------------------------------------------------------------- #
class TestDetermineCategories:
    def test_no_flags_selects_nothing(self, organizer):
        assert organizer.determine_categories(ArgsFactory()) == []

    def test_single_category_flag(self, organizer):
        assert organizer.determine_categories(ArgsFactory(pictures=True)) == ["pictures"]

    def test_multiple_category_flags_keep_definition_order(self, organizer):
        args = ArgsFactory(video=True, json=True)

        assert organizer.determine_categories(args) == ["json", "video"]

    def test_all_selects_every_category(self, organizer):
        assert organizer.determine_categories(ArgsFactory(all=True)) == list(
            WatchdogOrganizer.MIME_TYPES
        )

    def test_all_with_exclude_removes_that_category(self, organizer):
        args = ArgsFactory(all=True, exclude_documents=True)

        result = organizer.determine_categories(args)

        assert "documents" not in result
        assert len(result) == len(WatchdogOrganizer.MIME_TYPES) - 1

    def test_only_excludes_means_everything_except_those(self, organizer):
        args = ArgsFactory(exclude_video=True, exclude_audio=True)

        result = organizer.determine_categories(args)

        assert set(result) == set(WatchdogOrganizer.MIME_TYPES) - {"video", "audio"}

    def test_exclude_wins_over_explicit_selection(self, organizer):
        args = ArgsFactory(json=True, pictures=True, exclude_json=True)

        assert organizer.determine_categories(args) == ["pictures"]

    def test_non_category_flags_never_become_categories(self, organizer):
        # Regression: 'all', 'dry_run' and 'exclude_*' used to leak in as categories.
        args = ArgsFactory(all=True, dry_run=True, exclude_web=True)

        result = organizer.determine_categories(args)

        assert set(result) <= set(WatchdogOrganizer.MIME_TYPES)


# --------------------------------------------------------------------------- #
# classify
# --------------------------------------------------------------------------- #
class TestClassify:
    def test_png_is_classified_by_content(self, organizer, watch_dir):
        file = DiskFileFactory(folder=watch_dir, png=True)

        assert organizer.classify(file.path) == "pictures"

    def test_content_beats_a_misleading_extension(self, organizer, watch_dir):
        file = DiskFileFactory(folder=watch_dir, png=True, name="not_really.txt")

        assert organizer.classify(file.path) == "pictures"

    def test_json_goes_to_json_not_documents(self, organizer, watch_dir):
        # Regression: .json files detected as text/plain landed in "documents".
        file = DiskFileFactory(folder=watch_dir, json=True)

        assert organizer.classify(file.path) == "json"

    @pytest.mark.parametrize("trait", ["csv", "sql"])
    def test_plain_text_data_files_go_to_data(self, organizer, watch_dir, trait):
        file = DiskFileFactory(folder=watch_dir, **{trait: True})

        assert organizer.classify(file.path) == "data"

    def test_txt_goes_to_documents(self, organizer, watch_dir):
        file = DiskFileFactory(folder=watch_dir, name="notes.txt")

        assert organizer.classify(file.path) == "documents"

    def test_extension_fallback_is_case_insensitive(self, organizer, watch_dir):
        file = DiskFileFactory(folder=watch_dir, name="DUMP.SQL", content=b"select 1;\n")

        assert organizer.classify(file.path) == "data"

    def test_octet_stream_falls_back_to_extension(self, organizer, watch_dir):
        file = DiskFileFactory(folder=watch_dir, name="blob.csv", content=b"\x00\x01\x02\x03" * 64)
        assert magic.from_file(str(file.path), mime=True) == "application/octet-stream"

        assert organizer.classify(file.path) == "data"

    def test_unknown_text_extension_is_unclassified(self, organizer, watch_dir):
        file = DiskFileFactory(folder=watch_dir, name="server.log")

        assert organizer.classify(file.path) is None

    def test_empty_file_is_unclassified(self, organizer, watch_dir):
        file = DiskFileFactory(folder=watch_dir, name="empty.bin", content=b"")

        assert organizer.classify(file.path) is None


# --------------------------------------------------------------------------- #
# unique_destination
# --------------------------------------------------------------------------- #
class TestUniqueDestination:
    def test_free_name_is_kept(self, tmp_path):
        target = tmp_path / "a.json"

        assert WatchdogOrganizer.unique_destination(target, set()) == target

    def test_existing_file_gets_suffix_1(self, tmp_path):
        DiskFileFactory(folder=tmp_path, name="a.json")

        result = WatchdogOrganizer.unique_destination(tmp_path / "a.json", set())

        assert result == tmp_path / "a_1.json"

    def test_numbers_cascade_past_every_taken_name(self, tmp_path):
        for name in ["a.json", "a_1.json", "a_2.json"]:
            DiskFileFactory(folder=tmp_path, name=name)

        result = WatchdogOrganizer.unique_destination(tmp_path / "a.json", set())

        assert result == tmp_path / "a_3.json"

    def test_reserved_names_count_as_taken(self, tmp_path):
        reserved = {tmp_path / "a.json", tmp_path / "a_1.json"}

        result = WatchdogOrganizer.unique_destination(tmp_path / "a.json", reserved)

        assert result == tmp_path / "a_2.json"

    def test_disk_and_reserved_names_combine(self, tmp_path):
        DiskFileFactory(folder=tmp_path, name="a.json")
        reserved = {tmp_path / "a_1.json"}

        result = WatchdogOrganizer.unique_destination(tmp_path / "a.json", reserved)

        assert result == tmp_path / "a_2.json"

    def test_file_without_extension(self, tmp_path):
        DiskFileFactory(folder=tmp_path, name="Makefile")

        result = WatchdogOrganizer.unique_destination(tmp_path / "Makefile", set())

        assert result == tmp_path / "Makefile_1"

    def test_only_the_last_extension_is_preserved(self, tmp_path):
        DiskFileFactory(folder=tmp_path, name="backup.tar.gz")

        result = WatchdogOrganizer.unique_destination(tmp_path / "backup.tar.gz", set())

        assert result == tmp_path / "backup.tar_1.gz"

    def test_does_not_mutate_reserved(self, tmp_path):
        reserved = {tmp_path / "a.json"}

        WatchdogOrganizer.unique_destination(tmp_path / "a.json", reserved)

        assert reserved == {tmp_path / "a.json"}


# --------------------------------------------------------------------------- #
# build_plan
# --------------------------------------------------------------------------- #
class TestBuildPlan:
    def test_plans_each_file_into_its_category_folder(self, organizer, watch_dir, dest_dir):
        image = DiskFileFactory(folder=watch_dir, png=True)
        data = DiskFileFactory(folder=watch_dir, json=True)

        plan = organizer.build_plan(["pictures", "json"])

        assert set(plan) == {
            (image.path, dest_dir / "Pictures" / image.name),
            (data.path, dest_dir / "Json" / data.name),
        }

    def test_touches_nothing_on_disk(self, organizer, watch_dir, dest_dir, snapshot):
        DiskFileFactory(folder=watch_dir, png=True)
        DiskFileFactory(folder=watch_dir, json=True)
        before = snapshot(watch_dir, dest_dir)

        organizer.build_plan(list(WatchdogOrganizer.MIME_TYPES))

        assert snapshot(watch_dir, dest_dir) == before
        assert not dest_dir.exists()

    def test_only_selected_categories_are_planned(self, organizer, watch_dir):
        DiskFileFactory(folder=watch_dir, png=True)
        data = DiskFileFactory(folder=watch_dir, json=True)

        plan = organizer.build_plan(["json"])

        assert [src for src, _ in plan] == [data.path]

    def test_unsafe_files_are_skipped(self, organizer, watch_dir):
        DiskFileFactory(folder=watch_dir, name=".hidden.json", content=b"{}")
        DiskFileFactory(folder=watch_dir, name="video.mp4.part")
        DiskFileFactory(folder=watch_dir, name="~$lock.txt")

        assert organizer.build_plan(list(WatchdogOrganizer.MIME_TYPES)) == []

    def test_unsafe_files_are_never_read(self, organizer, watch_dir, monkeypatch):
        DiskFileFactory(folder=watch_dir, name="big.iso.crdownload")
        monkeypatch.setattr(
            organizer, "classify", lambda path: pytest.fail(f"classified {path}")
        )

        organizer.build_plan(list(WatchdogOrganizer.MIME_TYPES))

    def test_subdirectories_are_skipped(self, organizer, watch_dir):
        DiskFileFactory(folder=watch_dir / "nested", json=True)

        assert organizer.build_plan(["json"]) == []

    def test_unclassified_files_are_skipped(self, organizer, watch_dir):
        DiskFileFactory(folder=watch_dir, name="server.log")

        assert organizer.build_plan(list(WatchdogOrganizer.MIME_TYPES)) == []

    def test_collision_with_existing_destination_gets_numbered(self, organizer, watch_dir, dest_dir):
        DiskFileFactory(folder=dest_dir / "Json", name="a.json", content=b"{}")
        DiskFileFactory(folder=dest_dir / "Json", name="a_1.json", content=b"{}")
        source = DiskFileFactory(folder=watch_dir, json=True, name="a.json")

        plan = organizer.build_plan(["json"])

        assert plan == [(source.path, dest_dir / "Json" / "a_2.json")]

    def test_names_reserved_earlier_in_the_batch_are_not_reused(self, organizer, watch_dir, dest_dir):
        # a.json is taken on disk -> source a.json is planned as a_1.json,
        # so source a_1.json must not also land on a_1.json.
        DiskFileFactory(folder=dest_dir / "Json", name="a.json", content=b"{}")
        first = DiskFileFactory(folder=watch_dir, json=True, name="a.json")
        second = DiskFileFactory(folder=watch_dir, json=True, name="a_1.json")

        plan = organizer.build_plan(["json"])

        assert plan == [
            (first.path, dest_dir / "Json" / "a_1.json"),
            (second.path, dest_dir / "Json" / "a_1_1.json"),
        ]

    def test_every_planned_destination_is_unique(self, organizer, watch_dir, dest_dir):
        for name in ["a.json", "a_1.json", "a_2.json"]:
            DiskFileFactory(folder=dest_dir / "Json", name=name, content=b"{}")
        DiskFileFactory.create_batch(10, folder=watch_dir, json=True)
        DiskFileFactory(folder=watch_dir, json=True, name="a.json")

        destinations = [dst for _, dst in organizer.build_plan(["json"])]

        assert len(destinations) == len(set(destinations)) == 11
        assert not any(dst.exists() for dst in destinations)

    def test_classification_error_propagates_before_anything_moves(
        self, organizer, watch_dir, dest_dir, snapshot, monkeypatch
    ):
        DiskFileFactory.create_batch(3, folder=watch_dir, json=True)
        before = snapshot(watch_dir, dest_dir)

        def explode(path):
            raise OSError("libmagic failed")

        monkeypatch.setattr(organizer, "classify", explode)

        with pytest.raises(OSError, match="libmagic failed"):
            organizer.build_plan(["json"])
        assert snapshot(watch_dir, dest_dir) == before


# --------------------------------------------------------------------------- #
# execute_plan
# --------------------------------------------------------------------------- #
class FailingMove:
    """Stands in for shutil.move and raises on the Nth call (1-based)."""

    def __init__(self, fail_on_call, fail_on_rollback=False):
        self.fail_on_call = fail_on_call
        self.fail_on_rollback = fail_on_rollback
        self.calls = 0
        self.real_move = shutil.move

    def __call__(self, src, dst):
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise OSError("disk full")
        if self.fail_on_rollback and self.calls > self.fail_on_call:
            raise OSError("rollback denied")
        return self.real_move(src, dst)


class TestExecutePlan:
    def test_moves_every_file_and_keeps_content(self, watch_dir, dest_dir):
        files = DiskFileFactory.create_batch(3, folder=watch_dir, json=True)
        plan = [(f.path, dest_dir / "Json" / f.name) for f in files]

        WatchdogOrganizer.execute_plan(plan)

        for f, (src, dst) in zip(files, plan):
            assert not src.exists()
            assert dst.read_bytes() == f.content

    def test_creates_missing_destination_folders(self, watch_dir, dest_dir):
        file = DiskFileFactory(folder=watch_dir)
        destination = dest_dir / "deep" / "nested" / file.name

        WatchdogOrganizer.execute_plan([(file.path, destination)])

        assert destination.exists()

    def test_empty_plan_is_a_no_op(self, dest_dir):
        WatchdogOrganizer.execute_plan([])

        assert not dest_dir.exists()

    def test_folder_creation_failure_moves_nothing(self, watch_dir, dest_dir, snapshot):
        files = DiskFileFactory.create_batch(2, folder=watch_dir)
        # A file where a destination folder should be makes mkdir fail.
        DiskFileFactory(folder=dest_dir, name="Json", content=b"in the way")
        plan = [
            (files[0].path, dest_dir / "Data" / files[0].name),
            (files[1].path, dest_dir / "Json" / files[1].name),
        ]
        before = snapshot(watch_dir, dest_dir)

        with pytest.raises(OSError):
            WatchdogOrganizer.execute_plan(plan)

        assert snapshot(watch_dir, dest_dir) == before

    def test_failure_mid_run_rolls_back_earlier_moves(self, watch_dir, dest_dir, snapshot, monkeypatch):
        files = DiskFileFactory.create_batch(3, folder=watch_dir)
        plan = [(f.path, dest_dir / "Docs" / f.name) for f in files]
        before = snapshot(watch_dir)
        monkeypatch.setattr("main.shutil.move", FailingMove(fail_on_call=3))

        with pytest.raises(OSError, match="disk full"):
            WatchdogOrganizer.execute_plan(plan)

        assert snapshot(watch_dir) == before
        assert not any((dest_dir / "Docs").iterdir())

    def test_failure_on_first_move_leaves_everything_in_place(
        self, watch_dir, dest_dir, snapshot, monkeypatch
    ):
        files = DiskFileFactory.create_batch(2, folder=watch_dir)
        plan = [(f.path, dest_dir / f.name) for f in files]
        before = snapshot(watch_dir)
        monkeypatch.setattr("main.shutil.move", FailingMove(fail_on_call=1))

        with pytest.raises(OSError):
            WatchdogOrganizer.execute_plan(plan)

        assert snapshot(watch_dir) == before

    def test_never_overwrites_a_destination_that_appeared_after_planning(
        self, watch_dir, dest_dir, snapshot
    ):
        first = DiskFileFactory(folder=watch_dir, name="first.txt")
        second = DiskFileFactory(folder=watch_dir, name="second.txt")
        plan = [
            (first.path, dest_dir / "first.txt"),
            (second.path, dest_dir / "second.txt"),
        ]
        # Simulate another process creating the target between plan and execute.
        intruder = DiskFileFactory(folder=dest_dir, name="second.txt", content=b"do not touch")
        before_watch = snapshot(watch_dir)

        with pytest.raises(FileExistsError):
            WatchdogOrganizer.execute_plan(plan)

        assert intruder.path.read_bytes() == b"do not touch"
        assert snapshot(watch_dir) == before_watch  # first.txt was rolled back
        assert not (dest_dir / "first.txt").exists()

    def test_rollback_failure_is_logged_and_original_error_is_raised(
        self, watch_dir, dest_dir, monkeypatch, caplog
    ):
        files = DiskFileFactory.create_batch(2, folder=watch_dir)
        plan = [(f.path, dest_dir / f.name) for f in files]
        monkeypatch.setattr("main.shutil.move", FailingMove(fail_on_call=2, fail_on_rollback=True))

        with caplog.at_level(logging.ERROR), pytest.raises(OSError, match="disk full"):
            WatchdogOrganizer.execute_plan(plan)

        assert f"ROLLBACK FAILED: {plan[0][1]}" in caplog.text
        assert plan[0][1].exists()  # the file is left where the log says it is


# --------------------------------------------------------------------------- #
# move (end to end)
# --------------------------------------------------------------------------- #
class TestMove:
    def test_moves_selected_files_into_category_folders(self, organizer, watch_dir, dest_dir):
        image = DiskFileFactory(folder=watch_dir, png=True)
        data = DiskFileFactory(folder=watch_dir, json=True)

        organizer.move(ArgsFactory(all=True))

        assert (dest_dir / "Pictures" / image.name).read_bytes() == image.content
        assert (dest_dir / "Json" / data.name).read_bytes() == data.content
        assert not image.path.exists()
        assert not data.path.exists()

    def test_dry_run_moves_nothing(self, organizer, watch_dir, dest_dir, snapshot):
        DiskFileFactory(folder=watch_dir, png=True)
        DiskFileFactory(folder=watch_dir, json=True)
        before = snapshot(watch_dir, dest_dir)

        organizer.move(ArgsFactory(all=True, dry_run=True))

        assert snapshot(watch_dir, dest_dir) == before
        assert not dest_dir.exists()

    def test_no_categories_selected_moves_nothing(self, organizer, watch_dir, dest_dir, snapshot, caplog):
        DiskFileFactory(folder=watch_dir, json=True)
        before = snapshot(watch_dir, dest_dir)

        with caplog.at_level(logging.WARNING):
            organizer.move(ArgsFactory())

        assert snapshot(watch_dir, dest_dir) == before
        assert "No categories selected" in caplog.text

    def test_excluded_categories_stay_put(self, organizer, watch_dir, dest_dir):
        image = DiskFileFactory(folder=watch_dir, png=True)
        data = DiskFileFactory(folder=watch_dir, json=True)

        organizer.move(ArgsFactory(all=True, exclude_pictures=True))

        assert image.path.exists()
        assert (dest_dir / "Json" / data.name).exists()

    def test_unsafe_files_stay_put(self, organizer, watch_dir):
        partial = DiskFileFactory(folder=watch_dir, name="movie.mp4.crdownload")
        hidden = DiskFileFactory(folder=watch_dir, name=".secret.json", content=b"{}")

        organizer.move(ArgsFactory(all=True))

        assert partial.path.exists()
        assert hidden.path.exists()

    def test_collisions_get_cascading_numbers_and_existing_files_survive(
        self, organizer, watch_dir, dest_dir
    ):
        old = DiskFileFactory(folder=dest_dir / "Json", name="a.json", content=b'{"old": 0}')
        old_1 = DiskFileFactory(folder=dest_dir / "Json", name="a_1.json", content=b'{"old": 1}')
        new = DiskFileFactory(folder=watch_dir, name="a.json", content=b'{"new": 2}')

        organizer.move(ArgsFactory(json=True))

        assert old.path.read_bytes() == b'{"old": 0}'
        assert old_1.path.read_bytes() == b'{"old": 1}'
        assert (dest_dir / "Json" / "a_2.json").read_bytes() == b'{"new": 2}'

    def test_failure_leaves_every_file_where_it_started(
        self, organizer, watch_dir, dest_dir, snapshot, monkeypatch
    ):
        DiskFileFactory.create_batch(3, folder=watch_dir, json=True)
        DiskFileFactory(folder=dest_dir / "Json", name="keep.json", content=b"{}")
        before = snapshot(watch_dir, dest_dir)
        monkeypatch.setattr("main.shutil.move", FailingMove(fail_on_call=3))

        with pytest.raises(OSError):
            organizer.move(ArgsFactory(all=True))

        assert snapshot(watch_dir, dest_dir) == before
