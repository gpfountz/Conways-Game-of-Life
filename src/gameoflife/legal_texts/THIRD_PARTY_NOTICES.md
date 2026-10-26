<!-- SPDX-FileCopyrightText: 2026 Greg Pfountz -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Third-party notices

Conway's Game of Life is copyright (C) 2026 Greg Pfountz, GPL-3.0-only.
Other components retain their own copyright notices and license terms.
The complete upstream texts listed below are included locally in this package.
They have not been rewritten or replaced with the project's copyright.

## Runtime components reviewed on October 26, 2026

| Component | Observed version | Terms / attribution |
| --- | --- | --- |
| PySide6, PySide6 Essentials, PySide6 Addons, Shiboken6 | 6.11.3 | The Qt Company and contributors; package metadata offers LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only. Open-source GPLv3 use is compatible with this project's chosen license; included modules and their dependencies retain separate terms. |
| Qt native frameworks | QtCore reports 6.11.3 | The Qt Company and contributors; module-specific GPL/LGPL terms and third-party licenses apply. The Python package's license field is not an exhaustive license inventory of its native payload. |
| PyObjC Core and Cocoa | 12.2.2 | MIT; complete original copyright, permission, and warranty notice in `third-party/PyObjC/LICENSE.txt`. The two reviewed distributions' upstream license documents are byte-identical. |
| FFmpeg in PySide6 Addons | Embedded build prefix identifies n7.1.5 | Observed libavcodec declares LGPL version 2.1 or later for both arm64 and x86_64. Its upstream `COPYING.LGPLv2.1` and `LICENSE.md` are included. |
| CPython used for review | 3.14.8 | Python Software Foundation and historical contributors; complete upstream license in `third-party/Python/LICENSE`. A release must record the interpreter it actually supplies or requires. |

macOS Cocoa/Foundation and the inspected PyObjC extension's `/usr/lib/libffi.dylib`
are supplied by macOS. No libffi source or library is vendored by this repository;
the PyObjC license's historical reference to `libffi-src` does not establish that
the inspected wheel redistributes a separate libffi library.

This repository does not bundle dependency code in its own application wheel.
The deployment instructions install dependency distributions into a bundle venv;
such a resulting application payload must be reviewed as a whole. Pip and its
vendored dependencies are also present in the existing installed app's venv;
their separate redistribution notices have not been collected here. Development
tools such as pytest, Ruff, and mypy are not part of this runtime notice snapshot.

## Preserved documents and provenance

`SOURCES.json` records original URLs/distribution paths, versions, and SHA-256
digests for every preserved upstream notice and all six reviewed runtime wheels.
Downloaded wheel bytes were verified against exact PyPI release metadata.
Text files in `third-party/` are
byte-for-byte snapshots. They include PySide6's GPLv2/GPLv3/LGPLv3 texts,
Apache-2.0, BSD-3-Clause, Qt GPL exception, and GFDL document, plus the MIT,
FFmpeg, and Python documents above. Their inclusion does not claim that every
alternative is selected for this program or that documentation licenses apply
to the program's original source.

The Qt 6.11.3 and PyObjC 12.2.2 notice texts match their previous snapshots
byte for byte. FFmpeg 7.1.5's `LICENSE.md` is unchanged; its upstream
`COPYING.LGPLv2.1` removes nine form-feed characters without changing the words.
The included copy preserves the exact new upstream bytes.

## Native payload and remaining release work

The reviewed PySide6 wheels have the tag
`cp310-abi3-macosx_13_0_universal2`; representative QtCore, libavcodec, and PyObjC
binaries contain both arm64 and x86_64 slices. Native evidence and representative
checksums are recorded in `SOURCES.json`. FFmpeg's observed configuration has
shared-library, cross-compilation, and network support enabled, avdevice and
avfilter disabled, no observed
`--enable-gpl` or `--enable-nonfree`, and the two architecture-specific compiler
settings. This evidence is narrower than a full source/build reproducibility audit.

The installed PySide6/Shiboken distribution RECORDs do not list complete LICENSE,
COPYING, NOTICE, or SPDX/SBOM legal documents. The upstream texts preserved here
recover available notices; they do not reconstruct every bundled Qt/Chromium,
FFmpeg, codec, image, font, compression, or other third-party obligation.
PySide6 Addons includes WebEngine and multimedia libraries even though this
application imports only Core, Gui, and Widgets. Do not infer the shipped payload
from those imports alone.

Before redistributing a compiled app: inventory the exact shipped Qt modules and
nested libraries; obtain their complete matching copyright/license notices and
required dependency source/build materials; review each component's compatibility;
address pip/interpreter payloads; and provide the required source to recipients.
These tasks remain open. A generic Qt documentation page for a later patch
version is not evidence of the exact 6.11.3 wheel contents.

The older installed bundle's Info.plist reports 1.0.6 while its application package
metadata reports 1.0.12. It was inspected read-only and was not updated. That
bundle is not the artifact verified by this source adoption.

## Dependency refresh on October 26, 2026

Qt was updated from 6.11.1 to 6.11.3, including fixes to event exception handling,
QAction.menu(), and QObject.thread() ownership. PyObjC was updated from 12.2.1
to 12.2.2, which supports building with Xcode 27. The Qt wheel's FFmpeg build
changed from 7.1.3 to 7.1.5, whose upstream changelog includes decoder bounds
and memory-safety fixes; this is not a complete audit of the native payload.

Qt 6.12.0 was deferred: its macOS wheel minimum rises from 13 to 14 and its
dependency closure adds separate WebEngine/PDF distributions. The manifests
retain the 6.11 family with `<6.12`; that family supports Python 3.10–3.14.
Review platform support, the new closure, notices, and GUI behavior before
removing that bound. Python itself is supplied externally, not updated here.

Upstream references:
- https://doc.qt.io/qtforpython-6/release_notes/pyside6_release_notes.html
- https://pyobjc.readthedocs.io/en/latest/changelog.html#version-12-2-2
- https://github.com/FFmpeg/FFmpeg/blob/n7.1.5/Changelog
- https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.11.3
- https://doc.qt.io/qtforpython-6/licenses.html
- https://doc.qt.io/qt-6.11/licenses-used-in-qt.html
- https://github.com/ronaldoussoren/pyobjc/tree/v12.2.2
- https://github.com/FFmpeg/FFmpeg/tree/n7.1.5
- https://github.com/python/cpython/tree/v3.14.8
