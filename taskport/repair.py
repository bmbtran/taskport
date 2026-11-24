"""Explicit, version-pinned repair for upstream archive representation mismatch."""
from pathlib import Path

OLD="emailIds.includes(e.id) ? { ...e, folder: 'all-mail' } : e"
NEW="emailIds.includes(e.id) ? { ...e, folder: 'archive' } : e"
PATCH_PIN='taskport-repair-archive-v1'


def patch_archive(source):
    if source.count(OLD)!=1:raise ValueError('upstream archive implementation changed; review patch')
    return source.replace(OLD,NEW,1)


def patch_file(path):
    path=Path(path)
    path.write_text(patch_archive(path.read_text()))
