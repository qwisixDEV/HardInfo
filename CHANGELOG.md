# Changelog

All notable changes to this project are documented here.

## [Unreleased] — 0.0.3

### Added
- Disk, network, security, license and health collectors with typed models.
- Disk benchmark (150 MB, cancellable, hard 512 MB cap, temporary file cleanup).
- System tab sub-tabs: Overview / Disks / Network / Security.
- JSON report schema 2 with a `health` section; extended text report.
- Centralized admin gate and transactional registry tweaks with atomic backups.
- SHA256/Authenticode verification for downloaded drivers; no automatic execution.
- pytest suite covering security regressions, registry transactions, collectors,
  reports and an offscreen GUI smoke test.

### Fixed
- `QMessageBox.getText` replaced with a validated `QInputDialog` call.
- OEM driver name injection through `pnputil` prevented by strict validation.
- PowerShell WMI output encoding and Windows install-date parsing.
- Broken/corrupt registry backup files are quarantined instead of silently ignored.
- `closeEvent` now stops all worker threads, not only the two original ones.

### Security
- Destructive actions are disabled without administrator privileges.
- KMS activation warning now explicitly describes replacement of a digital license.
- Downloaded installers are never launched automatically.
