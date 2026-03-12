#!/usr/bin/env python3

import argparse
import hashlib
import json
import struct
import zipfile
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Tuple

RES_STRING_POOL_TYPE = 0x0001
RES_XML_TYPE = 0x0003
RES_XML_START_ELEMENT_TYPE = 0x0102
TYPE_STRING = 0x03


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_asset_name(package: str, version: str, abi: str) -> str:
    extension = ".xapk" if abi == "xapk" else ".apk"
    if abi in {"universal", "xapk"}:
        return f"{package}-{version}{extension}"
    return f"{package}-{version}-{abi}{extension}"


def read_u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def read_length8(data: bytes, offset: int) -> tuple[int, int]:
    length = data[offset]
    offset += 1
    if length & 0x80:
        length = ((length & 0x7F) << 8) | data[offset]
        offset += 1
    return length, offset


def read_length16(data: bytes, offset: int) -> tuple[int, int]:
    length = read_u16(data, offset)
    offset += 2
    if length & 0x8000:
        length = ((length & 0x7FFF) << 16) | read_u16(data, offset)
        offset += 2
    return length, offset


def decode_string_pool(chunk: bytes) -> list[str]:
    string_count = read_u32(chunk, 8)
    flags = read_u32(chunk, 16)
    strings_start = read_u32(chunk, 20)
    is_utf8 = bool(flags & 0x100)
    offsets = [read_u32(chunk, 28 + index * 4) for index in range(string_count)]
    strings: list[str] = []

    for string_offset in offsets:
        cursor = strings_start + string_offset
        if is_utf8:
            _, cursor = read_length8(chunk, cursor)
            byte_length, cursor = read_length8(chunk, cursor)
            raw = chunk[cursor : cursor + byte_length]
            strings.append(raw.decode("utf-8", errors="replace"))
        else:
            char_length, cursor = read_length16(chunk, cursor)
            raw = chunk[cursor : cursor + char_length * 2]
            strings.append(raw.decode("utf-16le", errors="replace"))

    return strings


def parse_binary_manifest(manifest: bytes) -> Dict[str, str]:
    if read_u16(manifest, 0) != RES_XML_TYPE:
        raise ValueError("AndroidManifest.xml is not in binary XML format")

    strings: list[str] = []
    offset = 8
    metadata: Dict[str, str] = {}

    while offset + 8 <= len(manifest):
        chunk_type = read_u16(manifest, offset)
        chunk_size = read_u32(manifest, offset + 4)
        if chunk_size < 8:
            raise ValueError("invalid AndroidManifest.xml chunk size")

        chunk = manifest[offset : offset + chunk_size]

        if chunk_type == RES_STRING_POOL_TYPE:
            strings = decode_string_pool(chunk)
        elif chunk_type == RES_XML_START_ELEMENT_TYPE and strings:
            name_index = read_u32(chunk, 20)
            attribute_count = read_u16(chunk, 28)
            tag_name = strings[name_index] if 0 <= name_index < len(strings) else ""

            if tag_name == "manifest":
                for attribute_index in range(attribute_count):
                    attr_offset = 36 + attribute_index * 20
                    raw_name_index = read_u32(chunk, attr_offset + 4)
                    raw_value_index = read_u32(chunk, attr_offset + 8)
                    typed_value_type = chunk[attr_offset + 15]
                    typed_value_data = read_u32(chunk, attr_offset + 16)

                    attr_name = strings[raw_name_index] if 0 <= raw_name_index < len(strings) else ""
                    raw_value = (
                        strings[raw_value_index]
                        if 0 <= raw_value_index < len(strings)
                        else None
                    )

                    if typed_value_type == TYPE_STRING and 0 <= typed_value_data < len(strings):
                        typed_value = strings[typed_value_data]
                    else:
                        typed_value = str(typed_value_data)

                    value = raw_value or typed_value
                    if attr_name == "package":
                        metadata["package"] = value
                    elif attr_name == "versionName":
                        metadata["version"] = value

            if tag_name == "application" and "app_name" not in metadata:
                for attribute_index in range(attribute_count):
                    attr_offset = 36 + attribute_index * 20
                    raw_name_index = read_u32(chunk, attr_offset + 4)
                    raw_value_index = read_u32(chunk, attr_offset + 8)
                    typed_value_type = chunk[attr_offset + 15]
                    typed_value_data = read_u32(chunk, attr_offset + 16)

                    attr_name = strings[raw_name_index] if 0 <= raw_name_index < len(strings) else ""
                    if attr_name != "label":
                        continue

                    if 0 <= raw_value_index < len(strings):
                        metadata["app_name"] = strings[raw_value_index]
                    elif typed_value_type == TYPE_STRING and 0 <= typed_value_data < len(strings):
                        metadata["app_name"] = strings[typed_value_data]

        offset += chunk_size

    return metadata


def parse_manifest_metadata(apk_path: Path) -> Dict[str, str]:
    with zipfile.ZipFile(apk_path) as apk_file:
        manifest = apk_file.read("AndroidManifest.xml")

    return parse_binary_manifest(manifest)


def parse_xapk_metadata(package_path: Path) -> Dict[str, str]:
    with zipfile.ZipFile(package_path) as archive:
        names = archive.namelist()

        if "manifest.json" in names:
            manifest_json = json.loads(archive.read("manifest.json").decode("utf-8"))
            metadata: Dict[str, str] = {}

            package_name = manifest_json.get("package_name") or manifest_json.get("packageName")
            version_name = manifest_json.get("version_name") or manifest_json.get("versionName")
            app_name = manifest_json.get("name") or manifest_json.get("app_name")

            if isinstance(package_name, str) and package_name.strip():
                metadata["package"] = package_name.strip()
            if isinstance(version_name, str) and version_name.strip():
                metadata["version"] = version_name.strip()
            elif isinstance(version_name, int):
                metadata["version"] = str(version_name)
            if isinstance(app_name, str) and app_name.strip():
                metadata["app_name"] = app_name.strip()

            if metadata.get("package") and metadata.get("version"):
                return metadata

        nested_apks = sorted(name for name in names if name.lower().endswith(".apk"))
        if not nested_apks:
            raise ValueError("XAPK does not contain manifest.json metadata or nested APK files")

        primary_apk = next((name for name in nested_apks if name.startswith("base")), nested_apks[0])
        nested_manifest = archive.read(primary_apk)

    with zipfile.ZipFile(package_path) as archive:
        with archive.open(primary_apk) as apk_handle:
            apk_bytes = apk_handle.read()

    from io import BytesIO
    with zipfile.ZipFile(BytesIO(apk_bytes)) as nested_archive:
        manifest = nested_archive.read("AndroidManifest.xml")

    return parse_binary_manifest(manifest)


def infer_metadata(
    package_path: Path,
    app_name: Optional[str],
    package: Optional[str],
    version: Optional[str],
) -> Tuple[str, str, str]:
    suffix = package_path.suffix.lower()
    if suffix == ".xapk":
        manifest_metadata = parse_xapk_metadata(package_path)
    else:
        manifest_metadata = parse_manifest_metadata(package_path)

    resolved_package = package or manifest_metadata.get("package")
    resolved_version = version or manifest_metadata.get("version")
    resolved_app_name = app_name or manifest_metadata.get("app_name") or package_path.stem

    if not resolved_package:
        raise SystemExit("error: package not provided and could not be read from package file")
    if not resolved_version:
        raise SystemExit("error: version not provided and could not be read from package file")

    return resolved_app_name, resolved_package, resolved_version


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate GitHub Release metadata for an APK or XAPK asset"
    )
    parser.add_argument("apk_file", help="Path to the APK or XAPK file")
    parser.add_argument("--app-name", help="User-facing app name")
    parser.add_argument("--package", help="Android package name")
    parser.add_argument("--version", help="App version")
    parser.add_argument(
        "--abi",
        default="universal",
        help="ABI label for the release asset, default: universal",
    )
    parser.add_argument(
        "--source",
        default="Internal mirror from approved maintainer workflow",
        help="Original source or operator note",
    )
    parser.add_argument(
        "--uploaded-by",
        default="PaulLee",
        help="Maintainer name to include in the release body",
    )

    args = parser.parse_args()

    apk_path = Path(args.apk_file).expanduser().resolve()
    if not apk_path.is_file():
        raise SystemExit(f"error: package file not found: {apk_path}")
    if apk_path.suffix.lower() not in {".apk", ".xapk"}:
        raise SystemExit("error: package file must end with .apk or .xapk")

    app_name, package, version = infer_metadata(
        apk_path,
        app_name=args.app_name,
        package=args.package,
        version=args.version,
    )
    sha256 = sha256_file(apk_path)
    asset_name = build_asset_name(package, version, args.abi)
    tag = f"{package}-{version}"
    title = f"{app_name} {version}"
    uploaded_at = date.today().isoformat()

    print(f"Package file: {apk_path}")
    print(f"Original file name: {apk_path.name}")
    print(f"Suggested asset name: {asset_name}")
    print(f"Tag: {tag}")
    print(f"Title: {title}")
    print(f"SHA256: {sha256}")
    print()
    print("Release body:")
    print(f"# {title}")
    print()
    print(f"Package: {package}")
    print(f"Version: {version}")
    print(f"Asset: {asset_name}")
    print(f"SHA256: {sha256}")
    print(f"Source: {args.source}")
    print(f"ABI: {args.abi}")
    print(f"Uploaded by: {args.uploaded_by}")
    print(f"Uploaded at: {uploaded_at}")
    print("Notes: <optional notes>")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
