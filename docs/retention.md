# Retention Policy

This repository is intended to keep release assets stable and auditable.

## Keep

Keep releases when:

- they are still referenced by a device configuration
- they are needed for rollback
- they remain legally and operationally valid

## Replace

Do not silently replace an existing APK asset.

If a published APK must change:

1. Publish a new release or a new versioned asset
2. Record the reason in release notes
3. Update downstream references separately

## Remove

Remove or disable a release only when:

- legal or licensing issues are reported
- malware or security problems are confirmed
- the binary is known to be corrupted

When removal is necessary:

1. Record the reason
2. Notify downstream maintainers
3. Publish a replacement if needed

## Stability Rules

- Release tags should stay immutable once published
- Asset names should not be reused for different binaries
- SHA256 must be recorded for every published APK
