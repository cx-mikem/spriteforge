"""Storage backend abstraction for saving and retrieving assets."""

import logging
import shutil
from pathlib import Path
from app.config import Config

logger = logging.getLogger(__name__)


class LocalStorageBackend:
    """Save files to local disk under STORAGE_LOCAL_PATH."""

    def __init__(self):
        self.base_path = Path(Config.STORAGE_LOCAL_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, source_path: Path, relative_dest: str) -> str:
        dest = self.base_path / relative_dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest)
        logger.info(f"Saved {source_path} -> {dest}")
        return str(dest)

    def load(self, relative_path: str) -> Path:
        return self.base_path / relative_path

    def exists(self, relative_path: str) -> bool:
        return (self.base_path / relative_path).exists()

    def url(self, relative_path: str) -> str:
        return str(self.base_path / relative_path)


class S3StorageBackend:
    """Save files to AWS S3."""

    def __init__(self):
        import boto3
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=Config.S3_ACCESS_KEY_ID,
            aws_secret_access_key=Config.S3_SECRET_ACCESS_KEY,
            region_name=Config.S3_REGION,
            endpoint_url=Config.S3_ENDPOINT_URL,
        )
        self.bucket = Config.S3_BUCKET

    def save(self, source_path: Path, relative_dest: str) -> str:
        self.s3.upload_file(str(source_path), self.bucket, relative_dest)
        url = f"s3://{self.bucket}/{relative_dest}"
        logger.info(f"Uploaded {source_path} -> {url}")
        return url

    def load(self, relative_path: str) -> Path:
        tmp = Path(f"/tmp/spriteforge_cache/{relative_path}")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        self.s3.download_file(self.bucket, relative_path, str(tmp))
        return tmp

    def exists(self, relative_path: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=relative_path)
            return True
        except Exception:
            return False

    def url(self, relative_path: str) -> str:
        return f"https://{self.bucket}.s3.amazonaws.com/{relative_path}"


class ReplitStorageBackend:
    """Save files to Replit Object Storage."""

    def __init__(self):
        from replit.object_storage import Client
        self.client = Client()

    def save(self, source_path: Path, relative_dest: str) -> str:
        with open(source_path, "rb") as f:
            self.client.upload_from_bytes(relative_dest, f.read())
        logger.info(f"Uploaded {source_path} -> replit://{relative_dest}")
        return f"replit://{relative_dest}"

    def load(self, relative_path: str) -> Path:
        tmp = Path(f"/tmp/spriteforge_cache/{relative_path}")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        data = self.client.download_as_bytes(relative_path)
        tmp.write_bytes(data)
        return tmp

    def exists(self, relative_path: str) -> bool:
        try:
            self.client.stat(relative_path)
            return True
        except Exception:
            return False

    def url(self, relative_path: str) -> str:
        return f"replit://{relative_path}"


def get_storage_backend():
    """Return the configured storage backend instance."""
    backend = Config.STORAGE_BACKEND
    if backend == "s3":
        return S3StorageBackend()
    elif backend == "replit":
        return ReplitStorageBackend()
    else:
        return LocalStorageBackend()
