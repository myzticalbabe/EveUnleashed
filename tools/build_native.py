"""Bottle the native-kernel recipe for the 316t interpreter.

Cythonizes every .pyx kernel under src/ and builds it in place with
setuptools, so `eve_unleashed._replay_cy` and `eve_unleashed._forensic_cy`
import as compiled extensions instead of falling back to Python.

Recipe notes (see native_replay.py): the build MUST target the
free-threaded ABI -- running this under the 316t interpreter makes
sysconfig define Py_GIL_DISABLED and link python316t.lib automatically.
Building the same sources under a GIL interpreter yields a GIL-only .pyd
that re-enables the lock process-wide on import; don't do that.

Usage: py316t tools/build_native.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"

KERNELS = [
    "eve_unleashed._replay_cy",
    "eve_unleashed._forensic_cy",
]


def main() -> int:
    from Cython.Build import cythonize
    from setuptools import Extension, setup

    ext_modules = [
        Extension(
            name,
            sources=[str(SRC / (name.replace(".", "/") + ".pyx"))],
            define_macros=[("Py_GIL_DISABLED", "1")],
        )
        for name in KERNELS
    ]
    for ext in ext_modules:
        if not Path(ext.sources[0]).exists():
            print("missing kernel source: " + ext.sources[0])
            return 1
    setup(
        name="eve-unleashed-native",
        ext_modules=cythonize(
            ext_modules,
            compiler_directives={
                "boundscheck": False,
                "wraparound": False,
                "cdivision": True,
            },
        ),
        script_args=["build_ext", "--inplace"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
