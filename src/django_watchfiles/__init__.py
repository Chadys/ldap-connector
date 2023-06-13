from __future__ import annotations

import logging
from pathlib import Path
from typing import Generator

import watchfiles
from django.utils import autoreload

logger = logging.getLogger("watchfiles.watcher")


class WatchfilesReloader(autoreload.BaseReloader):
    def watch_dir(self, path, glob):
        if path.is_relative_to("/usr/local/lib/python3.10/site-packages/"):
            return
        path = Path(path)
        try:
            path = path.absolute()
        except FileNotFoundError:
            logger.debug(
                "Unable to watch directory %s as it cannot be resolved.",
                path,
                exc_info=True,
            )
            return
        logger.debug("Watching dir %s with glob %s.", path, glob)
        self.directory_globs[path].add(glob)

    def watched_roots(self, watched_files: list[Path]) -> frozenset[Path]:
        extra_directories = self.directory_globs.keys()
        watched_file_dirs = {f.parent for f in watched_files}
        sys_paths = set(autoreload.sys_path_directories())
        return frozenset(
            tuple(
                filter(
                    lambda x: not x.is_relative_to(
                        "/usr/local/lib/python3.10/site-packages/"
                    ),
                    (*extra_directories, *watched_file_dirs, *sys_paths),
                )
            )
        )

    def tick(self) -> Generator[None, None, None]:
        watched_files = list(self.watched_files(include_globs=False))
        roots = autoreload.common_roots(self.watched_roots(watched_files))

        roots = tuple(
            filter(
                lambda x: not x.is_relative_to("/usr/local/lib/python3.10/"),
                roots,
            )
        )
        watcher = watchfiles.watch(
            *roots,
            watch_filter=watchfiles.PythonFilter(),
            # debug=True
        )

        for file_changes in watcher:
            for _change, path in file_changes:
                self.notify_file_changed(Path(path))
            yield


def replaced_get_reloader() -> autoreload.BaseReloader:
    return WatchfilesReloader()


autoreload.get_reloader = replaced_get_reloader
