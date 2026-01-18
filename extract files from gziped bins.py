import os
import gzip
import zipfile

source_path = r"C:\Users\mzimm\Downloads\Stormhalter"
destination_path = r".\unzip"
names = ("Data", "Kesmai", "Stormhalter", "UI")

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def extract_zip(bin_path: str, out_root: str) -> None:
    # ZIP file: extract all members as-is
    with zipfile.ZipFile(bin_path, "r") as z:
        for member in z.infolist():
            # Skip directory entries
            if member.is_dir():
                continue
            out_path = os.path.join(out_root, member.filename)
            ensure_dir(os.path.dirname(out_path))
            with z.open(member, "r") as src, open(out_path, "wb") as dst:
                dst.write(src.read())

def extract_custom_gzip(bin_path: str, out_root: str) -> None:
    # Original custom format inside gzip stream
    with gzip.open(bin_path, "rb") as source_file:
        _ = source_file.read(4)  # discard unknown header bytes
        byte = source_file.read(1)
        while byte != b"":
            name_length = int.from_bytes(byte, byteorder="big")
            name_bytes = source_file.read(name_length)
            rel_name = name_bytes.decode("utf-8")

            out_path = os.path.join(out_root, rel_name)

            size_bytes = source_file.read(4)
            n = int.from_bytes(size_bytes, byteorder="little")
            data = source_file.read(n)

            # Strip UTF-8 BOM if present
            if data[:3] == b"\xef\xbb\xbf":
                data = data[3:]

            ensure_dir(os.path.dirname(out_path))
            with open(out_path, "wb") as dstfile:
                dstfile.write(data)

            byte = source_file.read(1)

for name in names:
    bin_path = os.path.join(source_path, name + ".bin")
    out_root = os.path.join(destination_path, name)

    print(f"\n== {name} ==")
    print(f"Input:  {bin_path}")
    print(f"Output: {out_root}")

    with open(bin_path, "rb") as f:
        sig = f.read(4)

    # ZIP signature: PK\x03\x04 (or PK\x05\x06 empty zip, PK\x07\x08 spanned)
    if sig[:2] == b"PK":
        print("Detected ZIP container.")
        extract_zip(bin_path, out_root)
    # GZIP signature: 1f 8b
    elif sig[:2] == b"\x1f\x8b":
        print("Detected GZIP stream (custom bundle).")
        extract_custom_gzip(bin_path, out_root)
    else:
        raise RuntimeError(f"{name}.bin: unknown format signature {sig!r}")

print("\nDone.")

