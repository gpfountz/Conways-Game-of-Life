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

## Dependency review October 31, 2026

Official PyPI release metadata and upstream release notes were queried during
this review. Development minimums changed as follows:

| Tool | Previous minimum | Reviewed minimum | Relevant upstream changes |
| --- | --- | --- | --- |
| pytest | 9.1.1 | 9.2.0 | Clearer configuration/plugin errors and test reporting; reviewed keyword-only parametrization changes do not require project changes. [Changelog](https://docs.pytest.org/en/stable/changelog.html#pytest-9-2-0-2026-10-27). |
| Ruff | 0.17.2 | 0.17.3 | Fixes an incorrect f-string conversion and improves formatter/lexer performance. [Release notes](https://github.com/astral-sh/ruff/releases/tag/0.17.3). |
| mypy | 2.4.0 | 2.4.1 | Fixes two-phase overload checking and mypyc nested-function setup. [Versioned changelog](https://github.com/python/mypy/blob/v2.4.1/CHANGELOG.md#mypy-241). |

All three tools retain MIT metadata, compatible Python requirements, and
byte-identical license documents compared with their prior macOS wheels,
including mypy's typeshed notices. They remain development dependencies and do
not change the runtime notice inventory. SHA-256 hashes for all 48 downloaded
runtime, development, and temporary validation-tool wheels matched exact official
PyPI release metadata. Preserved upstream legal files and their recorded hashes
were left unchanged.

Runtime decisions and deferrals:

- Retain PySide6/Essentials/Addons/Shiboken 6.11.3, the newest stable 6.11
  release. [PySide6 6.12.0](https://pypi.org/project/PySide6/6.12.0/) requires
  macOS 14 wheels and adds separate WebEngine/PDF distributions. Adopting it
  needs a platform-support decision, full closure/native-notice review, and GUI
  validation before removing `<6.12`.
- Update PyObjC Core/Cocoa from 12.2.2 to [13.0](https://pyobjc.readthedocs.io/en/latest/changelog.html#version-13-0),
  the latest stable PyPI release. Raise the project's minimum Python to 3.11
  in package metadata, deployment validation, and documentation. The reviewed
  deployment range is 3.11–3.14; macOS 13 support is unchanged. No PyObjC upper
  bound is imposed. The application's real Foundation bundle metadata calls
  work with the changed selector implementation. Both universal2 wheel hashes,
  declared MIT terms, native architectures, and system-library links were
  inspected; provenance now records 13.0. The upstream Core and Cocoa wheel
  license bytes match the preserved copy. Changelog 13.0.1 is not yet a stable
  PyPI release at this review point.
- Installed development transitive packages and pip 26.2.2 are current. The
  setuptools `>=77.0.3` build requirement is a compatibility floor, not a pin;
  isolated builds select current setuptools 84.2.1. There is no production lock,
  npm manifest, CI workflow/action pin, or container image in this repository.
  Python remains externally supplied.

Validation on Apple Silicon/macOS with Python 3.14.8:

- `.venv/bin/python -m pytest -q`: 64 passed, three opt-in Qt cases skipped,
  including deployment support checks rejecting Python 3.10 and accepting 3.11.
- `.venv/bin/ruff check src tests scripts` and
  `.venv/bin/mypy --strict src tests scripts`: passed (17 typed files).
- `.venv/bin/ruff format --check src tests scripts`: flags five existing source
  files; the complete output is identical under 0.17.2 and 0.17.3. No unrelated
  formatting changes were made.
- `pip check`, `scripts/check_legal_resources.py`, and
  `zsh -n scripts/deploy.sh scripts/redeploy.sh`: passed.
- A fresh environment installed the full runtime/development closure from the
  verified wheels and passed `pip check`. With `RUN_QT_LEGAL_TESTS=1` and
  `QT_QPA_PLATFORM=offscreen`, the life, legal, and legal-GUI suites passed all
  14 cases, including Light/Dark text selection, scrolling, and missing notices.
- A clean, wheel-only resolution for Intel/macOS 13 and Python 3.11 succeeded.
  Target markers were checked across every resolved requirement; this target
  was not executed. Python 3.10 is no longer supported.
- `pip-audit` 2.10.1 against `requirements.txt` resolved and audited all six
  runtime distributions with no known vulnerabilities. A separate audit of all
  19 installed runtime/development distributions, including pip, also found no
  known vulnerabilities. These point-in-time advisory lookups do not inspect
  embedded native code.
- Isolated wheel/source-archive builds passed the legal-resource artifact
  checker. The wheel installed into the fresh environment and loaded the app,
  Qt 6.11.3, Foundation bridge, and complete offline legal texts outside the
  checkout using isolated Python imports.

Validation used application version 1.0.16 before commit-time version allocation.
No app was deployed or published. Existing binary-release limitations above
remain open.

Primary references: [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html),
[SPDX GPL-3.0-only](https://spdx.org/licenses/GPL-3.0-only.html),
[REUSE notices](https://reuse.software/tutorial/), and
[Python packaging metadata](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license-and-license-files).
