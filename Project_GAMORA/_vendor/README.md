# _vendor — vendored dependencies of the Gamora wheel

The wheel must be shippable without either repo checkout. These files are
copies, each byte-identical to its source except a provenance header line.

| vendored file | source | source HEAD | sha256 (vendored, with header) |
| --- | --- | --- | --- |
| `AOA/core/delegation_tracer.py` | `azazael/src/AOA/core/delegation_tracer.py` | azazael@116ece97 | 4a594113…52920c92 |
| `AOA/core/contracts.py` | `azazael/src/AOA/core/contracts.py` | azazael@116ece97 | ee175345…c98eb7b7 |
| `lucy.py` | `EveUnleashed/Project_LUCY/lucy.py` | EveUnleashed@c0e47d6 | bd10dded…16bd4250 |

Re-vendor procedure: copy the files, re-prepend the header with the new
source SHA, re-run `gamora doctor` + `pytest Project_GAMORA/tests/` +
a clean-target wheel install + doctor. All stdlib-only (MellifluousML holds).

`AOA/__init__.py`, `AOA/core/__init__.py`, `_vendor/__init__.py` are
packaging shims written for this tree (no source counterpart).
