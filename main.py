from pathlib import Path
import magic
import argparse
import logging
import os


class WatchdogOrganizer:
    def __init__(self):
        self.original_folder, self.folder_to_watch, self.destination_folder = (
            self.setup_watchdog()
        )
        self.destination_folders = {
            "compressed": self.destination_folder.joinpath("Compressed"),
            "pictures": self.destination_folder.joinpath("Pictures"),
            "json": self.destination_folder.joinpath("Json"),
        }

    def setup_watchdog(self):
        original_folder = Path(os.getenv("ORIGINAL_FOLDER"))
        folder_to_watch = Path(os.getenv("FOLDER_TO_WATCH"))
        destination_folder = Path(os.getenv("DESTINATION_FOLDER"))

        return original_folder, folder_to_watch, destination_folder

    def fetch_compressed_files(self, folder: Path) -> set[Path]:
        compressed_files = set()
        for f in folder.iterdir():
            if f.is_file():
                file_type = magic.from_file(str(f), mime=True)
                if file_type in [
                    "application/zip",
                    "application/x-rar-compressed",
                    "application/gzip",
                ]:
                    compressed_files.add(f)
                    logging.info(f"Compressed file found: {f.name}")

        return compressed_files

    def fetch_picture_files(self, folder: Path) -> set[Path]:
        picture_files = set()
        for f in folder.iterdir():
            if f.is_file():
                file_type = magic.from_file(str(f), mime=True)
                if file_type in [
                    "image/jpeg",
                    "image/png",
                    "image/gif",
                    "image/bmp",
                    "image/tiff",
                ]:
                    picture_files.add(f)
                    logging.info(f"Picture file found: {f.name}")
        return picture_files

    def fetch_json_files(self, folder: Path) -> set[Path]:
        json_files = set()
        for f in folder.iterdir():
            if f.is_file():
                file_type = magic.from_file(str(f), mime=True)
                if file_type == "application/json":
                    json_files.add(f)
                    logging.info(f"JSON file found: {f.name}")

        return json_files

    def fetch_all_files(self, folder: Path) -> dict[str, set[Path]]:
        return {
            "compressed": self.fetch_compressed_files(folder),
            "pictures": self.fetch_picture_files(folder),
            "json": self.fetch_json_files(folder),
        }

    def move_files(self, files: set[Path], file_type: str):
        for f in files:
            destination = self.destination_folders[file_type].joinpath(f.name)
            destination.parent.mkdir(exist_ok=True)
            f.rename(destination)
            logging.warning(f"Moved file {f.name} to {destination}")

    def move(self):
        file_types = {
            "compressed": ("fetch_compressed_files", args.compressed),
            "pictures": ("fetch_picture_files", args.pictures),
            "json": ("fetch_json_files", args.json),
        }

        for key, (fetch_method, enabled) in file_types.items():
            if enabled:
                files = getattr(self, fetch_method)(self.folder_to_watch)
                self.move_files(files, key)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description="Organize files in the WatchdogFolder."
    )
    argparser.add_argument(
        "--compressed",
        action="store_true",
        help="Move only compressed files to Compressed folder.",
    )
    argparser.add_argument(
        "--pictures",
        action="store_true",
        help="Move only picture files to Pictures folder.",
    )
    argparser.add_argument(
        "--json", action="store_true", help="Move only JSON files to Json folder."
    )
    args = argparser.parse_args()

    organizer = WatchdogOrganizer()
    organizer.move()
