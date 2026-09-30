import argparse
from dataclasses import dataclass
from pathlib import Path

import factory

from main import WatchdogOrganizer

# Minimal valid 1x1 PNG, so libmagic detects image/png from content.
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


@dataclass
class DiskFile:
    """A real file written to disk by DiskFileFactory."""

    folder: Path
    name: str
    content: bytes

    @property
    def path(self) -> Path:
        return self.folder / self.name


class DiskFileFactory(factory.Factory):
    """Creates a real file. `folder` must be supplied (usually a tmp_path)."""

    class Meta:
        model = DiskFile

    folder = None
    name = factory.Sequence(lambda n: f"file_{n}.txt")
    content = b"plain text content\n"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj = model_class(*args, **kwargs)
        obj.folder.mkdir(parents=True, exist_ok=True)
        obj.path.write_bytes(obj.content)
        return obj

    class Params:
        json = factory.Trait(
            name=factory.Sequence(lambda n: f"data_{n}.json"),
            content=b'{"key": "value", "numbers": [1, 2, 3]}\n',
        )
        png = factory.Trait(
            name=factory.Sequence(lambda n: f"image_{n}.png"),
            content=PNG_BYTES,
        )
        csv = factory.Trait(
            name=factory.Sequence(lambda n: f"table_{n}.csv"),
            content=b"a,b,c\n1,2,3\n",
        )
        sql = factory.Trait(
            name=factory.Sequence(lambda n: f"dump_{n}.sql"),
            content=b"select 1;\n",
        )


class ArgsFactory(factory.Factory):
    """argparse.Namespace mirroring the CLI; every flag defaults to False."""

    class Meta:
        model = argparse.Namespace

    all = False
    dry_run = False

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        flags = {}
        for key in WatchdogOrganizer.MIME_TYPES:
            flags[key] = False
            flags[f"exclude_{key}"] = False
        flags.update(kwargs)
        return model_class(**flags)
