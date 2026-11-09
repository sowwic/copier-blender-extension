import pathlib

import pytest


@pytest.fixture(scope="session")
def output_dir() -> pathlib.Path:
    """Output directory for tests.

    Returns:
        pathlib.Path: path to test output directory.

    """
    out_dir = pathlib.Path.cwd() / ".test_output"
    out_dir.mkdir(exist_ok=True)
    return out_dir


def _bpy_is_available() -> bool:
    try:
        import bpy  # noqa: F401
    except ImportError:
        return False
    return True


def pytest_collection_modifyitems(config, items):
    """Skip what needs Blender when `bpy` can't be imported.

    The tests run with the `bpy` package (`make pytest`). A plain `pytest` without it
    runs only the tests that don't use Blender.
    """
    if _bpy_is_available():
        return
    skip = pytest.mark.skip(reason="needs bpy: run `make pytest`")
    for item in items:
        if item.path.name == "test_extension.py":
            item.add_marker(skip)
