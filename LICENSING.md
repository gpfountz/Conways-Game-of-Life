<!-- SPDX-FileCopyrightText: 2026 Greg Pfountz -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Licensing and redistribution

The original Python code, tests, scripts, configuration, and documentation of
Conway's Game of Life are copyright (C) 2026 Greg Pfountz and licensed under
**GPL-3.0-only**: GNU General Public License version 3, without permission to
choose a later GPL version. The unmodified full text is in [LICENSE](LICENSE).
Its application appendix contains an example "or later" notice; this project's
explicit GPL-3.0-only designation controls the project's choice.

This project implements John Conway's B3/S23 cellular automaton and includes
named classic seeds, including Gosper's glider gun. The project copyright
notice covers its implementation and documentation; it does not claim ownership
of the underlying mathematical rules or the historical patterns.

## Material and exceptions

| Material | Treatment |
| --- | --- |
| Original `src/gameoflife/*.py`, tests, scripts, and project documentation/configuration | GPL-3.0-only; retain copyright and SPDX notices. |
| `LICENSE` and `src/gameoflife/legal_texts/LICENSE` | Unmodified Free Software Foundation license document; the latter is its offline runtime copy. |
| `src/gameoflife/legal_texts/third-party/` | Preserved upstream documents under their own terms; see the notice index and provenance manifest. |
| Both image/icon files in `src/gameoflife/assets/` | Ownership/provenance confirmation is pending; no project copyright or new license is asserted over them yet. |
| Wheels, egg metadata, caches, virtual environments, and application bundles | Generated artifacts; their contents retain the licenses of the included components. They are not newly licensed by a blanket project header. |
| Python, Qt/PySide6, Shiboken, PyObjC, bundled native libraries, and macOS system libraries | Separate components; upstream terms and notices remain applicable. |

The repository contains no vendored source library or downloaded puzzle dataset.
The coordinate tuples in `patterns.py` are named mathematical seeds, not a
third-party pattern archive. No fonts or screenshots were added by this adoption.

## Reuse and contributions

You may use, modify, and redistribute this software, including commercially,
under GPLv3's conditions. Private modifications need not be published merely
because they were made. When conveying covered source or compiled derivatives,
retain applicable copyright/license notices, identify modifications as required,
and license the covered derivative under GPLv3. Provide recipients the applicable
Corresponding Source through a method allowed by the license.

Preserve the application's appropriate legal notices, including author credit,
no-warranty information, redistribution rights, and access to the full license,
as required by GPLv3. There is no extra advertising-credit requirement or
indemnification condition. The license's warranty and liability provisions apply
to the extent permitted by applicable law.

Unless clearly identified otherwise and accepted as a compatible separately
licensed component, contributions are offered under GPL-3.0-only. Contributors
retain their copyrights; add their notices rather than replacing them. No
copyright assignment or contributor license agreement is introduced here.

## Desktop legal notices and package checks

Open **About Conway's Game of Life**. The About dialog displays the author,
shared application version, GPL designation, and no-warranty/redistribution
notice. Its License and Third-party tabs load selectable, scrollable local text
from `gameoflife/legal_texts` using `importlib.resources`. No internet access is
needed. Missing resources produce an explicit error instead of an incomplete
legal view. The dialog uses the current Qt theme and does not alter the universe.

Setuptools metadata declares GPL-3.0-only and includes the legal files. The wheel
also includes importable runtime copies; a metadata declaration alone is not a
runtime-resource check. The source archive includes build/install scripts, tests,
and project guidance. Verify actual artifacts before distribution:

```zsh
.venv/bin/python scripts/check_legal_resources.py
.venv/bin/python scripts/check_legal_resources.py --wheel /path/to/application.whl --sdist /path/to/application.tar.gz
```

## Binary distribution status

This adoption prepares project source and package notices. It does not approve or
publish an application bundle. The existing locally installed app is untouched.
The [third-party notice index](src/gameoflife/legal_texts/THIRD_PARTY_NOTICES.md)
records observed runtime versions, native evidence, and outstanding items.

Before a binary release, resolve icon provenance and the exact Qt/native payload
notice inventory; obtain and provide the required matching dependency source and
build/install materials. Choose and record the exact application release commit,
including any uncommitted release changes, and preserve its build/dependency
inputs. A moving `master` URL or an archive containing only this repository is
not a complete substitute for required dependency source. Match the method of
source provision to GPLv3 section 6 and the other applicable component licenses.
Verify the extracted final bundle, its resources, executable dependencies,
architecture, platform signatures, and installation instructions. The current
venv-based launcher depends on an external Homebrew Python installation and is
not established as a portable, self-contained application distribution.

These are engineering observations and licensing implementation guidance, not a
legal opinion or certification of a future distribution.

## Adoption checks recorded October 24, 2026

- The ordinary suite passed 35 tests; three opt-in native GUI cases were skipped.
  Ruff, strict mypy, and shell syntax checks passed.
- A real 1.0.13 wheel and source archive were built locally. Their legal files,
  metadata, preserved upstream bytes, and build/install materials were checked.
  The extracted wheel loaded the complete offline GPL and third-party texts
  independently of the checkout's working directory.
- Native Qt 6.11.1 verification stalled before application code ran. A stack
  sample showed macOS's dynamic loader waiting in `fcntl` while importing Qt;
  an isolated temporary copy also timed out. The verification processes were
  stopped. Light/Dark rendering and scrolling therefore remain unverified.
  The opt-in cases are in `tests/test_legal_gui.py`; run them with
  `RUN_QT_LEGAL_TESTS=1 QT_QPA_PLATFORM=offscreen` in an environment that loads Qt.
- No application bundle was built, installed, signed, deployed, or published.

## Dependency validation October 26, 2026

- The reviewed runtime now uses PySide6/Shiboken 6.11.3 and PyObjC 12.2.2.
  Its embedded FFmpeg identifies 7.1.5. The notice index and `SOURCES.json`
  describe these exact inspected wheels; all six downloaded wheel hashes
  matched official PyPI release metadata. The binary inventory limitations
  above still apply.
- A clean Python 3.14.8 environment passed 35 ordinary tests and all three
  opt-in Qt tests. Qt imported and created an offscreen application successfully.
  Light/Dark legal-dialog screenshots were inspected; text selection, scrolling,
  and missing-resource handling passed. This supersedes the earlier Qt loader
  limitation for this environment and dependency set.
- Ruff lint and strict mypy passed for source, tests, and scripts. Formatting
  checks identify five existing source files with the same result under the
  previous Ruff version; those files were left unchanged.
- The six-package runtime audit with pip-audit 2.10.1 found no known
  vulnerabilities. This advisory lookup does not inspect embedded native code.
  Dependency resolution also succeeded for Python 3.10 on Intel/macOS 13,
  including `tomli`; that target was not executed.
- No application bundle was installed, signed, deployed, or published.

Primary references: [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html),
[SPDX GPL-3.0-only](https://spdx.org/licenses/GPL-3.0-only.html),
[REUSE notices](https://reuse.software/tutorial/), and
[Python packaging metadata](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license-and-license-files).
