#!/usr/bin/env python
"""Tests for `moin2gitwiki` package."""
import re

import pytest
from click.testing import CliRunner

from moin2gitwiki import __version__
from moin2gitwiki import cli


@pytest.fixture
def response():
    """Sample pytest fixture.

    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    # import requests
    # return requests.get("https://github.com/audreyr/cookiecutter-pypackage")


def test_content(response):
    """Sample pytest test function with the pytest fixture as an argument."""
    # from bs4 import BeautifulSoup
    # assert "GitHub" in BeautifulSoup(response.content).title.string


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.moin2gitwiki)
    assert result.exit_code == 0
    assert "moin2gitwiki" in result.output
    help_result = runner.invoke(cli.moin2gitwiki, ["--help"])
    assert help_result.exit_code == 0
    assert re.search(r"--help \s+ Show this message and exit.", help_result.output)
    version_result = runner.invoke(cli.moin2gitwiki, ["--version"])
    assert version_result.exit_code == 0
    assert f", version {__version__}" in version_result.output
