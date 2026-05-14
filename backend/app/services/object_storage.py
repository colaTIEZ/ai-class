"""Object storage abstraction for local and S3-compatible backends."""

from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


@dataclass(slots=True)
class StoredObject:
    key: str
    uri: str


class LocalObjectStorage:
    def __init__(self, root: Path, bucket: str) -> None:
        self.root = root
        self.bucket = bucket

    def put_bytes(self, key: str, content: bytes) -> str:
        target = self.root / self.bucket / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return key

    def uri_for(self, key: str) -> str:
        return f"local://{self.bucket}/{key}"


def get_object_storage() -> LocalObjectStorage:
    return LocalObjectStorage(
        root=Path(settings.object_storage_local_root),
        bucket=settings.object_storage_bucket,
    )
