# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.18] - 2025-09-25

### Added
- Add minicypher dependency

### Changed
- Replace mdb_tools util.cypher imports with minicypher

---

## [0.2.17] - 2025-09-18

### Removed
- Obsolete versioning machinery and references from codebase
- Legacy version handling code and associated tests

### Fixed
- Test suite cleanup by removing outdated test situations

### Changed
- Documentation updated to remove obsolete versioning references

### Security
- Updated requests from 2.32.3 to 2.32.4 to address security vulnerabilities
- Updated urllib3 from 2.4.0 to 2.5.0 to address security vulnerabilities

---

## [0.2.16] - 2024-XX-XX

### Added
- Method to get key property of Node in entity.py

### Security
- Updated vulnerable dependencies in pyproject.toml

---

## [0.2.15] - 2024-XX-XX

### Fixed
- Private attributes now return None if not set instead of raising errors

---

## [0.0.50] - 2023-01-18

### Added
- First release of `bento-meta`!

---

For older versions and detailed commit history, see: https://github.com/CBIIT/bento-meta/commits/master