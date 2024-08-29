"""
Defines a "rich" reporter backend
This reporter handler provides the default output for conda.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import Progress

from conda.base.context import context
from conda.exceptions import CondaError
from conda.plugins import CondaReporterBackend, hookimpl
from conda.plugins.types import ProgressBarBase, ReporterRendererBase

if TYPE_CHECKING:
    from typing import ContextManager


class QuietProgressBar(ProgressBarBase):
    """
    Progress bar class used when no output should be printed
    """

    def __init__(self, description, **kwargs):
        super().__init__(description, **kwargs)

        sys.stdout.write(f"...downloading {description}...\n")

    def update_to(self, fraction) -> None:
        pass

    def refresh(self) -> None:
        pass

    def close(self) -> None:
        pass


class RichReporterRenderer(ReporterRendererBase):
    """
    Default implementation for console reporting in conda
    """

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        table_parts = [""]
        longest_header = max(map(len, data.keys()))

        for header, value in data.items():
            table_parts.append(f" {header:>{longest_header}} : {value}")

        table_parts.append("\n")

        return "\n".join(table_parts)

    def envs_list(self, data, **kwargs) -> str:
        console = Console(file=sys.stdout)

        with console.capture() as capture:
            console.print("Enviroments")
            console.print(data)

        return capture.get()

    def progress_bar(
        self,
        description: str,
        **kwargs,
    ) -> ProgressBarBase:
        """
        Determines whether to return a RichProgressBar or QuietProgressBar
        """
        if context.quiet:
            return QuietProgressBar(description, **kwargs)
        else:
            return RichProgressBar(description, **kwargs)

    @classmethod
    def progress_bar_context_manager(cls) -> ContextManager:
        @contextmanager
        def rich_context_manager():
            console = Console(file=sys.stdout)
            with Progress(transient=True, console=console) as progress:
                yield progress

        return rich_context_manager()


class RichProgressBar(ProgressBarBase):
    def __init__(
        self,
        description: str,
        context_manager=None,
        **kwargs,
    ) -> None:
        super().__init__(description)

        self.progress: Progress | None = None

        # We are passed in a list of context managers. Only one of them
        # is allowed to be the ``rich.Progress`` one we've defined. We
        # find it and then set it to ``self.progress``.
        if isinstance(context_manager, Progress):
            self.progress = context_manager

        # Unrecoverable state has been reached
        if self.progress is None:
            raise CondaError(
                "Rich is configured, but there is no progress bar available"
            )

        self.task = self.progress.add_task(description, total=1)

    def update_to(self, fraction) -> None:
        if self.progress is not None:
            self.progress.update(self.task, completed=fraction)

            if fraction == 1:
                self.progress.update(self.task, visible=False)

    def close(self) -> None:
        if self.progress is not None:
            self.progress.stop_task(self.task)

    def refresh(self) -> None:
        if self.progress is not None:
            self.progress.refresh()


@hookimpl
def conda_reporter_backends():
    """
    Reporter backend for rich
    """
    yield CondaReporterBackend(
        name="rich",
        description="Rich implementation for console reporting in conda",
        renderer=RichReporterRenderer,
    )
