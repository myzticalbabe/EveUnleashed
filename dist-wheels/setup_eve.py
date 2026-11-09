"""Build helper: eve-unleashed pure-Python wheel installable on 3.10+.

Produces dist-wheels/eve_unleashed-<ver>-py3-none-any.whl from
EveUnleashed/src/eve_unleashed (stdlib only, native ext optional via
resilience.py ENGINE fallback). Version is read from
EveUnleashed/pyproject.toml so the wheel tracks the repo.

Floor is 3.10 (measured: grammar clean to 3.8, runtime X|Y unions need
3.10+, zero 3.11+ stdlib gates across all 66 files).

Usage (any interpreter with setuptools+wheel, no network):
  python dist-wheels/setup_eve.py bdist_wheel --dist-dir dist-wheels
"""
import os
import tomllib
from setuptools import setup, find_packages

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")

with open(os.path.join(HERE, "..", "pyproject.toml"), "rb") as f:
    meta = tomllib.load(f)["project"]

setup(
    name=meta["name"],
    version=meta["version"],
    description=meta["description"],
    package_dir={"": os.path.abspath(SRC)},
    packages=find_packages(os.path.abspath(SRC), include=["eve_unleashed*"]),
    python_requires=">=3.10",
    entry_points={"console_scripts": ["eve-unleashed=eve_unleashed.cli:main"]},
)
