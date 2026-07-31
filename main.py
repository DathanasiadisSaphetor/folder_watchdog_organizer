from pathlib import Path
from datetime import datetime, timedelta
import magic
import argparse
import logging
import os

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

    def __init__(self):
        folder_to_watch_env = os.getenv("FOLDER_TO_WATCH", None)
        if not folder_to_watch_env:
            raise ValueError("FOLDER_TO_WATCH environment variable is not set.")
        self.folder_to_watch = Path(folder_to_watch_env)

        self.destination_folder = Path(
            os.getenv("DESTINATION_FOLDER", self.folder_to_watch / "Organized")
        )
        self.destination_folders = {
            "compressed": self.destination_folder / "Compressed",
            "pictures": self.destination_folder / "Pictures",
            "json": self.destination_folder / "Json",
            "python": self.destination_folder / "Python",
            "web": self.destination_folder / "Web",
            "documents": self.destination_folder / "Documents",
            "data": self.destination_folder / "Data",
            "audio": self.destination_folder / "Audio",
            "video": self.destination_folder / "Video",
            "executables": self.destination_folder / "Executables",
        }

    def is_safe_to_move_from_desktop(self, file_path: str | Path) -> bool:
        path = Path(file_path)

        # 1. Ignore if it's a directory (unless you want to move whole folders)
        if not path.is_file():
            return False

        # 2. Check exact system file names
        if path.name.lower() in self.DESKTOP_SYSTEM_FILES:
            return False

        # 3. Check for specific ignored extensions
        if path.suffix.lower() in self.IGNORED_EXTENSIONS:
            return False

        # 4. Ignore hidden files (starts with dot)
        # This automatically catches .DS_Store, .localized, etc., but it's good to be explicit above
        if path.name.startswith("."):
            return False

        # 5. Ignore Microsoft Office lock files (they start with ~$)
        if path.name.startswith("~$"):
            return False

        # 6. Ignore symlinks (macOS/Linux aliases)
        if path.is_symlink():
            return False

        return True

    def determine_mime_types(self, args) -> dict[str, set[str]]:
        if args.all is True:
            return self.MIME_TYPES

        mime_types = {}
        args_dict = vars(args)
        for arg in args_dict:
            if arg == "dry_run":
                continue
            mime_types[arg] = self.MIME_TYPES.get(arg, {})

        return mime_types

    def fetch_all_files(
        self, folder: Path, mime_types: dict[str, set[str]]
    ) -> dict[str, set[Path]]:
        result = {key: set() for key in mime_types}
        for f in folder.iterdir():
            if not f.is_file():
                continue
            file_type = magic.from_file(str(f), mime=True)
            for category, mime_types_set in mime_types.items():
                if file_type in mime_types_set:
                    result[category].add(f)
                    logging.info(
                        f"{category} file found: {f.name}.\t-->\t{'SAFE' if self.is_safe_to_move_from_desktop(f) else 'NOT SAFE'}"
                    )
                    break
        return result

    def move_files(self, files: set[Path], file_type: str):
        for f in files:
            # TODO this checks only the desktop folder.
            # more checks to be added
            if not self.is_safe_to_move_from_desktop(file_path=f):
                logging.warning(f"Skipped file {f.name}. It is not safe to relocate.")
                continue
            destination = self.destination_folders[file_type] / f.name
            destination.parent.mkdir(exist_ok=True)
            f.rename(destination)
            logging.info(f"Moved file {f.name} to {destination}")

    def move(self, args):
        mime_types = self.determine_mime_types(args)
        all_files = self.fetch_all_files(self.folder_to_watch, mime_types)
        if not args.dry_run:
            for key in mime_types:
                if args.all or getattr(args, key, False):
                    self.move_files(all_files[key], key)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description="Organize files in the WatchdogFolder."
    )
    argparser.add_argument(
        "--all",
        action="store_true",
        help="Move all file types, ignoring other type arguments.",
    )
    for key in WatchdogOrganizer.MIME_TYPES:
        argparser.add_argument(
            f"--{key}",
            action="store_true",
            help=f"Move only {key} files.",
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
    organizer = WatchdogOrganizer()
    organizer.move(args)
