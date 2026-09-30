from pathlib import Path
from datetime import datetime, timedelta
import magic
import argparse
import logging
import os
import shutil

LOG_DIR = Path(__file__).parent / "logs"
LOG_RETENTION_DAYS = 7


def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)

    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    for log_file in LOG_DIR.glob("*.log"):
        if (
            datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff
            or log_file.stat().st_size == 0
        ):
            log_file.unlink()
            print(f"Deleted old log: {log_file.name}")

    log_path = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(),
        ],
    )


class WatchdogOrganizer:
    MIME_TYPES = {
        "compressed": {
            "application/zip",
            "application/x-rar-compressed",
            "application/gzip",
            "application/x-tar",
            "application/x-7z-compressed",
        },
        "pictures": {
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/bmp",
            "image/tiff",
            "image/webp",
            "image/svg+xml",
        },
        "json": {"application/json"},
        "python": {"text/x-python"},
        "web": {
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",  # Often used interchangeably with text/javascript
            "application/wasm",
        },
        "documents": {
            "application/pdf",
            "text/plain",
            "text/markdown",
            "application/msword",  # .doc
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
            "application/vnd.ms-excel",  # .xls
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        },
        "data": {
            "text/csv",
            "application/xml",
            "text/xml",
            "application/x-yaml",
            "text/yaml",
        },
        "audio": {
            "audio/mpeg",  # .mp3
            "audio/wav",
            "audio/ogg",
            "audio/webm",
            "audio/flac",
        },
        "video": {
            "video/mp4",
            "video/webm",
            "video/x-matroska",  # .mkv
            "video/x-msvideo",  # .avi
            "video/quicktime",  # .mov
        },
        "executables": {
            "application/x-msdownload",  # .exe
            "application/x-executable",  # Linux binaries
            "application/x-mach-binary",  # macOS binaries
        },
    }

    # Exact filenames the OS needs on the Desktop
    DESKTOP_SYSTEM_FILES = {"desktop.ini", ".ds_store", ".localized", "thumbs.db"}

    # Extensions that should stay on the Desktop or indicate an unfinished file
    IGNORED_EXTENSIONS = {
        # Shortcuts
        ".lnk",
        ".url",
        ".desktop",
        # Active downloads & temp files
        ".crdownload",
        ".part",
        ".download",
        ".tmp",
    }

    # libmagic reports most plain-text formats as text/plain (or octet-stream for
    # unknown binaries). For these generic MIME types, fall back to the extension.
    GENERIC_MIME_TYPES = {"text/plain", "application/octet-stream"}
    EXTENSION_CATEGORIES = {
        ".json": "json",
        ".py": "python",
        ".html": "web",
        ".htm": "web",
        ".css": "web",
        ".js": "web",
        ".csv": "data",
        ".xml": "data",
        ".yaml": "data",
        ".yml": "data",
        ".sql": "data",
        ".txt": "documents",
        ".md": "documents",
    }

    def __init__(self):
        folder_to_watch_env = os.getenv("FOLDER_TO_WATCH", None)
        if not folder_to_watch_env:
            raise ValueError("FOLDER_TO_WATCH environment variable is not set.")
        self.folder_to_watch = Path(folder_to_watch_env)
        if not self.folder_to_watch.is_dir():
            raise ValueError(f"FOLDER_TO_WATCH is not a directory: {self.folder_to_watch}")

        self.destination_folder = Path(
            os.getenv("DESTINATION_FOLDER", self.folder_to_watch / "Organized")
        )
        self.destination_folders = {
            key: self.destination_folder / key.capitalize() for key in self.MIME_TYPES
        }

    def is_safe_to_move_from_desktop(self, file_path: str | Path) -> bool:
        path = Path(file_path)

        # Check symlinks first: is_file() follows links, so a link to a file
        # would otherwise pass.
        if path.is_symlink():
            return False
        if not path.is_file():
            return False
        name = path.name.lower()
        if name in self.DESKTOP_SYSTEM_FILES:
            return False
        if path.suffix.lower() in self.IGNORED_EXTENSIONS:
            return False
        # Hidden files and Microsoft Office lock files (~$)
        if name.startswith(".") or name.startswith("~$"):
            return False
        return True

    def determine_categories(self, args) -> list[str]:
        """Categories selected by the CLI flags, minus any --exclude-* flags."""
        selected = [key for key in self.MIME_TYPES if getattr(args, key, False)]
        excluded = {
            key for key in self.MIME_TYPES if getattr(args, f"exclude_{key}", False)
        }
        # --all, or only exclusions given -> start from every category
        if args.all or (not selected and excluded):
            selected = list(self.MIME_TYPES)
        return [key for key in selected if key not in excluded]

    def classify(self, path: Path) -> str | None:
        mime = magic.from_file(str(path), mime=True)
        if mime in self.GENERIC_MIME_TYPES:
            return self.EXTENSION_CATEGORIES.get(path.suffix.lower())
        for category, mime_types in self.MIME_TYPES.items():
            if mime in mime_types:
                return category
        return None

    @staticmethod
    def unique_destination(target: Path, reserved: set[Path]) -> Path:
        """name.ext -> name_1.ext -> name_2.ext ... until free on disk and in this batch."""
        candidate = target
        counter = 1
        while candidate.exists() or candidate in reserved:
            candidate = target.with_name(f"{target.stem}_{counter}{target.suffix}")
            counter += 1
        return candidate

    def build_plan(self, categories: list[str]) -> list[tuple[Path, Path]]:
        """Scan, classify and resolve destinations. Touches nothing on disk.

        Any exception here aborts the run before a single file is moved.
        """
        plan: list[tuple[Path, Path]] = []
        reserved: set[Path] = set()
        wanted = set(categories)

        for f in sorted(self.folder_to_watch.iterdir()):
            if not self.is_safe_to_move_from_desktop(f):
                if f.is_file():
                    logging.info(f"Skipping {f.name}: not safe to relocate.")
                continue
            category = self.classify(f)
            if category not in wanted:
                continue
            destination = self.unique_destination(
                self.destination_folders[category] / f.name, reserved
            )
            reserved.add(destination)
            plan.append((f, destination))
            logging.info(f"[{category}] {f.name}\t-->\t{destination}")
        return plan

    @staticmethod
    def execute_plan(plan: list[tuple[Path, Path]]):
        """Move every file in the plan; on any failure, roll back the moves done so far."""
        # Create destination folders first so a mkdir failure happens before any move.
        for parent in {dst.parent for _, dst in plan}:
            parent.mkdir(parents=True, exist_ok=True)

        done: list[tuple[Path, Path]] = []
        try:
            for src, dst in plan:
                # Something may have appeared since planning; never overwrite.
                if dst.exists():
                    raise FileExistsError(f"Destination appeared during run: {dst}")
                shutil.move(src, dst)  # works across filesystems, unlike Path.rename
                done.append((src, dst))
                logging.info(f"Moved {src.name} to {dst}")
        except Exception:
            logging.exception("Move failed; rolling back files moved in this run.")
            for src, dst in reversed(done):
                try:
                    shutil.move(dst, src)
                    logging.info(f"Restored {src}")
                except Exception:
                    logging.exception(f"ROLLBACK FAILED: {dst} could not be restored to {src}")
            raise

    def move(self, args):
        categories = self.determine_categories(args)
        if not categories:
            logging.warning("No categories selected. Use --all or --<category>.")
            return
        plan = self.build_plan(categories)
        if not plan:
            logging.info("Nothing to move.")
            return
        if args.dry_run:
            logging.info(f"Dry run: {len(plan)} file(s) would be moved.")
            return
        self.execute_plan(plan)
        logging.info(f"Done: {len(plan)} file(s) moved.")


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description="Organize files in the WatchdogFolder."
    )
    argparser.add_argument(
        "--all",
        action="store_true",
        help="Move all file types (combine with --exclude-* to skip some).",
    )
    for key in WatchdogOrganizer.MIME_TYPES:
        argparser.add_argument(
            f"--{key}",
            action="store_true",
            help=f"Move {key} files.",
        )
        argparser.add_argument(
            f"--exclude-{key}",
            action="store_true",
            help=f"Exclude {key} files.",
        )
    argparser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be moved without actually moving files.",
    )
    args = argparser.parse_args()

    setup_logging()
    try:
        organizer = WatchdogOrganizer()
        organizer.move(args)
    except Exception:
        logging.exception("Aborted.")
        raise SystemExit(1)
