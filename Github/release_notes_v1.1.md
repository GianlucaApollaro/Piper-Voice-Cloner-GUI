# Piper Voice Cloner GUI v1.1 - Release Notes

This release introduces robust UI localization, automated dataset export checks, and translation view enhancements to ensure a seamless experience when switching between English and Italian languages.

## Improvements

### Internationalization & UI Polish
- Standardized error dialog titles across all views to use dynamically localized titles instead of hardcoded Italian strings.
- Added translation keys in both English and Italian dictionaries for all UI exceptions, file prefixes, and error messages.
- Updated the Translation view to support fully localized log notifications and custom default text file output names.
- Unified the Whisper model dependency installation and loading console outputs inside the Docker container to standard English.

### Robust Model Exporting
- Integrated upfront validation in the Export tab to verify that the dataset configuration file (config.json) exists on the host machine before executing the Docker export command.
- Avoids incomplete exports and confusing generic logs by alerting users immediately with clear, localized warning messages if the configuration file is missing.

### Maintenance & Clean Packaging
- Configured Git ignore lists and packing scripts to strictly skip graph visualization artifacts (graphify-out, graph.html, and graph.json) from release packages and version control.
