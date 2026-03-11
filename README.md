# apks

This repository stores APK binaries that do not have a stable public download URL.

It is a distribution repository only. APK files must be uploaded as GitHub Release assets, not committed into Git history.

## Purpose

- Keep reviewed APK binaries in one place
- Provide stable download URLs through GitHub Releases
- Preserve release history for manual audit

## Out of Scope

- User app requests
- App review and approval workflow
- Device registry generation
- Business metadata management

Those responsibilities stay in the separate `apk-sync` repository.

## Repository Layout

- `README.md`: repository purpose and operator entry point
- `docs/publishing.md`: how maintainers publish a new APK release
- `docs/retention.md`: retention, replacement, and removal rules

## Release Rules

- Do not commit `.apk` files into Git history
- Use one GitHub Release per `package + version`
- Put APK binaries in Release assets
- Record SHA256 in the release notes
- Keep old releases for traceability

## Naming Conventions

Recommended tag format:

```text
<package>-<version>
```

Examples:

```text
org.videolan.vlc-3.7.0
com.example.app-1.2.3
```

Recommended asset format:

```text
<package>-<version>.apk
<package>-<version>-<abi>.apk
```

Examples:

```text
org.videolan.vlc-3.7.0.apk
org.videolan.vlc-3.7.0-arm64-v8a.apk
```

## Maintainer Docs

- Publishing process: [`docs/publishing.md`](./docs/publishing.md)
- Retention and takedown rules: [`docs/retention.md`](./docs/retention.md)
