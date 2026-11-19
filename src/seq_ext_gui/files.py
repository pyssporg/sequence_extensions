"""Project-root-confined browsing of flow modules and plan documents."""

from __future__ import annotations

from pathlib import Path

from .contracts import FileContent, FileEntry, TreeResponse

TREE_SUFFIXES = {".py", ".json"}
SKIP_DIRS = {"__pycache__", ".git", ".venv", "runs", ".seq_ext_gui"}


class ProjectFiles:
    """All paths are resolved and confined to a single project root."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()

    def set_root(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()

    def resolve(self, path: str | Path | None, *, must_exist: bool = False) -> Path:
        raw = Path(path) if path not in (None, "") else Path()
        candidate = raw if raw.is_absolute() else self.root / raw
        try:
            resolved = candidate.resolve()
        except OSError as exc:
            raise ValueError(f"cannot resolve path {path!r}: {exc}") from exc
        if resolved != self.root and not resolved.is_relative_to(self.root):
            raise ValueError(f"path is outside the project root: {path!r}")
        if must_exist and not resolved.exists():
            raise ValueError(f"path does not exist: {path!r}")
        return resolved

    def relative(self, path: Path) -> str:
        rel = path.relative_to(self.root)
        return "" if rel == Path(".") else rel.as_posix()

    def tree(self, path: str | Path | None = "") -> TreeResponse:
        directory = self.resolve(path, must_exist=True)
        if not directory.is_dir():
            raise ValueError(f"not a directory: {path!r}")

        dirs: list[FileEntry] = []
        files: list[FileEntry] = []
        for child in directory.iterdir():
            name = child.name
            if name.startswith("."):
                continue
            if child.is_dir():
                if name in SKIP_DIRS:
                    continue
                try:
                    if not child.resolve().is_relative_to(self.root):
                        continue
                    stat = child.stat()
                except OSError:
                    continue
                dirs.append(
                    FileEntry(
                        path=self.relative(child),
                        name=name,
                        kind="dir",
                        mtime=stat.st_mtime,
                    )
                )
                continue
            if child.suffix not in TREE_SUFFIXES:
                continue
            try:
                if not child.resolve().is_relative_to(self.root):
                    continue
                stat = child.stat()
            except OSError:
                continue
            files.append(
                FileEntry(
                    path=self.relative(child),
                    name=name,
                    kind="file",
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                )
            )

        dirs.sort(key=lambda entry: (entry.name.lower(), entry.name))
        files.sort(key=lambda entry: (entry.name.lower(), entry.name))
        return TreeResponse(
            root=str(self.root),
            path=self.relative(directory),
            entries=dirs + files,
        )

    def read(self, path: str | Path) -> FileContent:
        target = self.resolve(path, must_exist=True)
        if not target.is_file() or target.suffix not in TREE_SUFFIXES:
            raise ValueError(f"not a readable .py/.json file: {path!r}")
        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"file is not valid UTF-8: {path!r}") from exc
        return FileContent(path=self.relative(target), content=content)
