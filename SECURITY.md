<!-- SPDX-FileCopyrightText: 2026 Greg Pfountz -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Security Policy

## System and Scope

Conway's Game of Life is a local, single-user macOS desktop application
maintained by Greg Pfountz. Review `src/gameoflife/`, dependencies and package
configuration, `scripts/`, `redeploy.sh`, and build/install instructions.

The current application has no application-defined network service, account
system, external pattern importer, clipboard importer, or saved-game parser.
Gameplay uses local UI input and built-in patterns. Window geometry persists
through QSettings; simulation state remains in memory. Reassess this boundary
when new input, persistence, networking, or distribution features are added.

## Threat Model and Trust Boundaries

Protect the user's files, local settings, process privileges, and build and
repository integrity. Consider malformed local settings, UI input, package
resources, archive inputs to verification tools, and Git metadata processed
by developer tools. Establish who can control each input and how it reaches
the affected operation before assigning security impact.

The OS, installed interpreter, dependencies, application code/resources, and
developer-selected checkout, tools, destinations, and Git configuration are
trusted execution inputs. Building or installing a malicious checkout or
dependency already executes code; identify any additional trust boundary
crossed rather than treating that execution alone as a new vulnerability.

Developer workflows may contact package indexes and Git remotes and write
build outputs, an explicitly selected bundle, and clone-local Git state.
These capabilities are separate from normal desktop gameplay.

## Security Invariants

- Normal gameplay and legal-text viewing remain local and do not transmit
  user data or invoke external commands.
- Displayed legal text remains inert text; viewing it must not execute
  markup, commands, or embedded resource references.
- Data handled by tooling must not introduce unintended command execution,
  arbitrary filesystem writes, or disclosure beyond its intended operation.
- Versioning operations preserve unrelated worktree edits, partial staging,
  the active Git index, and unrelated hooks. Ambiguous publication state
  must fail explicitly rather than authorize destructive reconciliation.
- Resource and artifact checks report missing or altered required notices.
  Their hashes establish consistency with recorded bytes, not authenticity
  of the application or safety of its dependencies.

## Reportable Findings and Severity Context

Report demonstrated trust-boundary violations with a reachable input and
concrete confidentiality, integrity, or availability impact. Include required
local access, user interaction, affected privileges, and deployment context.
Local-only exposure does not automatically exclude a finding.

Dependency findings need evidence about the actual affected payload and
reachable behavior. Neither an advisory alone nor an unused Python import
establishes exploitability or safety of bundled native components.

## Exclusions and Accepted Risk

Ordinary simulation, rendering, and layout bugs without security impact are
outside security review. CPU or memory growth caused solely by the operator's
own simulation is a performance concern; externally triggerable exhaustion or
impact beyond that session requires separate assessment.

No vulnerability-specific exclusions or accepted security risks are recorded.

## Known Limitations

The sparse universe has no population or work budget and advances on the GUI
thread. The application is not established as an OS-sandboxed or self-contained
distribution. Build dependencies use minimum versions without a lockfile.

Tests express intended behavior and do not prove security controls. Legal
resource verification is not a security audit, dependency provenance check,
signature check, or approval of a release payload.
