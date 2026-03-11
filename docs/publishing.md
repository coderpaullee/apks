# Publishing APKs

This repository publishes APK binaries through GitHub Releases.

## When to Use This Repository

Use `apks` when:

- the APK does not have a stable public download URL
- the APK needs to be mirrored for device access
- maintainers need a controlled binary distribution point

Do not use `apks` for:

- unreviewed user uploads
- development builds
- files that already have a stable trusted public release URL

## Publishing Steps

1. Verify the APK source, package name, version, and file integrity.
2. Compute the APK SHA256.
3. Create a Git tag using `<package>-<version>`.
4. Create a GitHub Release from that tag.
5. Upload the APK as a Release asset.
6. Copy the body template from [`.github/release-template.md`](../.github/release-template.md).
7. Fill in the SHA256, source note, and ABI in the release body.

## Release Template

Recommended release title:

```text
<app name> <version>
```

Recommended release body:

```text
Package: <package.name>
Version: <version>
Asset: <package.name>-<version>.apk
SHA256: <sha256>
Source: <original source or internal note>
ABI: <universal | arm64-v8a | armeabi-v7a | x86_64>
Uploaded by: <maintainer name>
Uploaded at: <YYYY-MM-DD>
Notes: <optional notes>
```

Copy-ready file:

- [`.github/release-template.md`](../.github/release-template.md)

## Asset Naming

Use one of these formats:

```text
<package>-<version>.apk
<package>-<version>-<abi>.apk
```

Examples:

```text
org.videolan.vlc-3.7.0.apk
org.videolan.vlc-3.7.0-arm64-v8a.apk
```

## Operating Rules

- Do not replace an existing asset in place
- If a binary changes, publish a new release or a new versioned asset
- Keep naming deterministic so other systems can reference assets later
- Prefer public releases if devices need anonymous download access
