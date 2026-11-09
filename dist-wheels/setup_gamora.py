"""Build helper: Gamora DOMellifluousML Berzerker A-I-O cliT, pure wheel.

Assembles a shippable tree in dist-wheels/build-gamora/ (committed sources
only -- nothing read from outside EveUnleashed except the pinned eve-unleashed
wheel dependency, resolved from PyPI at install time), then builds
dist-wheels/gamora_domellifluousml_berzerker_a_i_o_clit-1.0.0-py3-none-any.whl.

One universal wheel for all Python versions: py3-none-any, floor 3.10
(proven installs on 3.14 / 3.15t / 3.16t on this box).

Self-sufficiency: gamora/berzerker/jaeger/hook ship as top-level modules,
lucy ships from _vendor, the AOA tracer ships from _vendor/AOA (provenance
in Project_GAMORA/_vendor/README.md). eve parts (cli, swarm, therapy,
cradle) resolve from the eve-unleashed dependency. doctor is green iff
eve-unleashed is installed (READY on 316t) -- the harness mandates 316t
anyway and exits 1 elsewhere by design.

Usage (any interpreter with setuptools+wheel, no network):
  python dist-wheels/setup_gamora.py bdist_wheel --dist-dir dist-wheels
"""
import os
import shutil
from setuptools import setup, find_packages

HERE = os.path.dirname(os.path.abspath(__file__))
GAMORA = os.path.join(HERE, "..", "Project_GAMORA")
STAGE = os.path.join(HERE, "build-gamora")

TOP_MODULES = ["gamora.py", "berzerker.py", "jaeger_inject.py",
               "opencode_jaeger_hook.py"]

if os.path.isdir(STAGE):
    shutil.rmtree(STAGE)
os.makedirs(os.path.join(STAGE, "AOA"))

for m in TOP_MODULES:
    shutil.copy(os.path.join(GAMORA, m), STAGE)
shutil.copy(os.path.join(GAMORA, "_vendor", "lucy.py"), STAGE)
os.makedirs(os.path.join(STAGE, "gamora_data"), exist_ok=True)
shutil.copy(os.path.join(HERE, "..", "Project_CRADLE", "cradle.py"),
              os.path.join(STAGE, "gamora_data", "cradle.py"))
for pkg in ("AOA/__init__.py", "AOA/core/__init__.py",
            "AOA/core/delegation_tracer.py", "AOA/core/contracts.py"):
    dst = os.path.join(STAGE, pkg)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(os.path.join(GAMORA, "_vendor", pkg), dst)

setup(
    name="gamora-domellifluousml-berzerker-a-i-o-clit",
    version="1.0.0",
    description="Gamora DOMellifluousML Berzerker A-I-O cliT -- one command over "
                "lilith swarm, eve, jaeger 3:16T, cradle, lucy, berzerker. Stdlib only.",
    package_dir={"": os.path.abspath(STAGE)},
    py_modules=["gamora", "berzerker", "jaeger_inject",
                "opencode_jaeger_hook", "lucy"],
    packages=["AOA", "AOA.core"],
    data_files=[("gamora_data", [os.path.join(STAGE, "gamora_data",
                                               "cradle.py")])],
    install_requires=["eve-unleashed>=3.16"],
    python_requires=">=3.10",
    entry_points={"console_scripts": ["gamora=gamora:main"]},
)
