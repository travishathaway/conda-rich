"""
Defines a "rich" reporter backend
This reporter handler provides the default output for conda.
"""

from __future__ import annotations

import sys

from contextlib import contextmanager
from typing import TYPE_CHECKING

from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from conda.base.context import context
from conda.exceptions import CondaError
from conda.plugins import CondaReporterBackend, hookimpl
from conda.plugins.types import ProgressBarBase, ReporterRendererBase, SpinnerBase

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
            console.print("Environments")
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

    def spinner(self, message, fail_message="failed\n"):
        if context.quiet:
            return QuietSpinner(message, fail_message)
        else:
            return RichSpinner(message, fail_message)

    def prompt(
        self, message: str = "Continue?", choices=("yes", "no"), default: str = "yes"
    ):
        """
        Implementation of prompt
        """
        return Prompt.ask(message, choices=choices, default=default)


class RichProgressBar(ProgressBarBase):
    def __init__(
        self,
        description: str,
        context_manager=None,
        visible_when_finished=False,
        **kwargs,
    ) -> None:
        super().__init__(description)

        self.progress: Progress | None = None
        self.visible_when_finished = visible_when_finished

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
                self.progress.update(self.task, visible=self.visible_when_finished)

    def close(self) -> None:
        if self.progress is not None:
            self.progress.stop_task(self.task)

    def refresh(self) -> None:
        if self.progress is not None:
            self.progress.refresh()


class RichSpinner(SpinnerBase):
    def __init__(self, message: str, fail_message: str = "failed\n"):
        super().__init__(message, fail_message)

        self.live_ctx = None
        self.live = None
        self.task_id = None

    def __enter__(self):
        self.progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            SpinnerColumn("aesthetic"),
        )
        self.live_ctx = Live(self.progress, transient=True)
        self.live = self.live_ctx.__enter__()
        self.progress.add_task(self.message, start=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.live_ctx is not None:
            self.live.console.print(f"{self.message} (done)")
            self.live_ctx.__exit__(exc_type, exc_val, exc_tb)


class QuietSpinner(SpinnerBase):
    def __enter__(self):
        sys.stdout.write(f"{self.message}: ")
        sys.stdout.flush()

        sys.stdout.write("...working... ")
        sys.stdout.flush()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type or exc_val:
            sys.stdout.write(f"{self.fail_message}\n")
        else:
            sys.stdout.write("done\n")
        sys.stdout.flush()


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
