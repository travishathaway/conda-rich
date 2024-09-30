import time
from io import StringIO

import pytest

from conda.exceptions import CondaError
from conda.plugins import CondaReporterBackend
from rich.progress import Progress

from conda_rich.hooks import (
    QuietProgressBar,
    QuietSpinner,
    RichSpinner,
    RichProgressBar,
    conda_reporter_backends,
    RichReporterRenderer,
)


def test_conda_reporter_backends():
    """
    Ensure that a ``CondaReporterBackend`` object is yielded from the ``conda_reporter_backends``
    function
    """
    hook_obj = next(conda_reporter_backends())

    assert hook_obj is not None
    assert isinstance(hook_obj, CondaReporterBackend)
    assert hook_obj.name == "rich"
    assert hook_obj.description == "Rich implementation for console reporting in conda"
    assert hook_obj.renderer is RichReporterRenderer


def test_quiet_progress_bar(capsys):
    """
    Basic test to ensure the quiet progress bar works as expected
    """
    description = "Test"
    quiet_progress = QuietProgressBar(description)

    capture = capsys.readouterr()

    assert capture.out == f"...downloading {description}...\n"

    # Test individual methods; these should do nothing and return None
    assert quiet_progress.refresh() is None
    assert quiet_progress.close() is None
    assert quiet_progress.update_to(1) is None


def test_rich_progress_bar(capsys):
    """
    Basic test to ensure the rich progress bar works as expected
    """
    description = "Test"
    units = 0

    with Progress() as progress:
        rich_progress = RichProgressBar(
            description, context_manager=progress, visible_when_finished=True
        )

        while units < 5:
            units += 1
            rich_progress.update_to(units / 4)
            rich_progress.refresh()
            time.sleep(0.01)

        rich_progress.close()

    capture = capsys.readouterr()

    assert capture.out == "Test ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00\n"


def test_rich_progress_bar_misconfigured():
    """
    Ensure an exception is raised when we fail to pass a ``rich.progress.Progress``
    bar object to ``RichProgressBar``.
    """
    with pytest.raises(
        CondaError, match="Rich is configured, but there is no progress bar available"
    ):
        RichProgressBar("Test description", None)


def test_quiet_spinner(capsys):
    """
    Basic test to ensure the quiet spinner works as expected
    """
    message = "test"
    with QuietSpinner(message):
        pass

    capture = capsys.readouterr()

    assert capture.out == f"{message}: ...working... done\n"


def test_quiet_spinner_failed_state(capsys):
    """
    Basic test to ensure the quiet spinner works as expected
    """
    message = "test"
    fail_message = "testing fail message"

    try:
        with QuietSpinner(message, fail_message=fail_message):
            raise Exception("Test fail")

    except Exception:
        capture = capsys.readouterr()
        assert capture.out == f"{message}: ...working... {fail_message}\n"


def test_rich_spinner(capsys):
    """
    Basic test to ensure the rich spinner works as expected
    """
    message = "test"
    with RichSpinner(message):
        pass

    capture = capsys.readouterr()

    assert capture.out == "test (done)\n"


def test_rich_reporter_renderer_detail_view():
    """
    Basic test to ensure that the ``detail_view`` method on the ``RichReporterRenderer`` class
    works as expected
    """
    renderer = RichReporterRenderer()

    data = {
        "field_one": "one",
        "field_two": "two",
    }

    render_str = renderer.detail_view(data)

    assert render_str == "\n field_one : one\n field_two : two\n\n"


def test_rich_reporter_renderer_env_list():
    """
    Basic test to ensure that the ``env_list`` method on the ``RichReporterRenderer`` class
    works as expected
    """
    renderer = RichReporterRenderer()
    environments = ["one", "two", "three"]

    render_str = renderer.envs_list(environments)

    assert render_str == "Environments\n['one', 'two', 'three']\n"


def test_rich_reporter_renderer_progress_bar(mocker):
    """
    Basic test to ensure that the ``progress_bar`` method on the ``RichReporterRenderer`` class
    works as expected
    """
    mock_context = mocker.patch("conda_rich.hooks.context")
    mock_context.quiet = False

    renderer = RichReporterRenderer()
    progress = Progress()
    progress_bar = renderer.progress_bar("test", context_manager=progress)

    assert isinstance(progress_bar, RichProgressBar)


def test_rich_reporter_renderer_progress_bar_with_quiet(mocker):
    """
    Basic test to ensure that the ``progress_bar`` method on the ``RichReporterRenderer`` class
    works as expected when ``context.quiet`` is ``True``
    """
    mock_context = mocker.patch("conda_rich.hooks.context")
    mock_context.quiet = True

    renderer = RichReporterRenderer()
    progress_bar = renderer.progress_bar("test")

    assert isinstance(progress_bar, QuietProgressBar)


def test_rich_reporter_renderer_progress_bar_context_manager():
    """
    Basic test to ensure that the ``progress_bar_context_manager`` method on the
    ``RichReporterRenderer`` class works as expected
    """
    renderer = RichReporterRenderer()

    # Make sure that the item the context manager returns is a ``rich.progress.Progress`` instance
    with renderer.progress_bar_context_manager() as ctx:
        assert isinstance(ctx, Progress)


def test_rich_reporter_renderer_spinner(mocker):
    """
    Basic test to ensure that the ``spinner`` method on the ``RichReporterRenderer`` class
    works as expected
    """
    mock_context = mocker.patch("conda_rich.hooks.context")
    mock_context.quiet = False

    renderer = RichReporterRenderer()
    spinner = renderer.spinner("test message")

    assert isinstance(spinner, RichSpinner)


def test_rich_reporter_renderer_spinner_with_quiet(mocker):
    """
    Basic test to ensure that the ``spinner`` method on the ``RichReporterRenderer`` class
    works as expected when ``context.quiet`` is ``True``
    """
    mock_context = mocker.patch("conda_rich.hooks.context")
    mock_context.quiet = True

    renderer = RichReporterRenderer()
    spinner = renderer.spinner("test")

    assert isinstance(spinner, QuietSpinner)


def test_rich_reporter_renderer_prompt(monkeypatch, capsys):
    """
    Basic test to ensure that the ``prompt`` method on the ``RichReporterRenderer`` class
    works as expected
    """
    renderer = RichReporterRenderer()
    monkeypatch.setattr("sys.stdin", StringIO("yes\n"))

    assert renderer.prompt() == "yes"
