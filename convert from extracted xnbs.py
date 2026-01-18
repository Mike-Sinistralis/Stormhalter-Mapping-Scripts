import glob
import os
import struct
from PIL import Image
import lz4.block
import numpy as np
import soundfile as sf


def main():
    source_path = r".\unzip\**\*.xnb"
    destination_path = r".\unxnb"

    for sfn in glob.glob(source_path, recursive=True):
        # Get relative path from unzip folder, preserving subfolder structure
        # e.g., .\unzip\Bitmaps\001.xnb -> Bitmaps\001.xnb -> .\unxnb\Bitmaps\001.png
        rel_path = os.path.relpath(sfn, r".\unzip")
        dfn = os.path.join(destination_path, rel_path)
        dfn = os.path.splitext(dfn)[0]
        xnb_to_png(sfn, dfn)


def xnb_to_png(sfn, dfn):
    with open(sfn, "rb") as f:
        data = f.read()
        offset = 0
    print(f"Processing {sfn} ({len(data)} bytes)")

    if len(data) < 14:
        print("err File too small to be an XNB")
        return

    # Parse XNB header
    magic_xnb = data[offset:offset + 3]
    offset += 3
    if magic_xnb != b"XNB":
        print("err XNB magic is missing")
        return

    # target_platform = data[offset]
    offset += 1

    # version = data[offset]
    offset += 1

    flags = data[offset]
    offset += 1

    # file_size = struct.unpack("<I", data[6:10])[0]
    offset += 4

    if flags & 0x40:  # LZ4 compressed
        decompressed_size = struct.unpack("<I", data[offset:offset + 4])[0]
        offset += 4
        data = lz4.block.decompress(data[offset:], uncompressed_size=decompressed_size)
    else:
        data = data[offset:]
    offset = 0

    type_reader_count, offset = read_7bit_encoded_int(data, offset)
    if type_reader_count != 1:
        print("err Program can only handle 1 reader")
        return

    type_reader_length, offset = read_7bit_encoded_int(data, offset)

    type_reader = data[offset:offset + type_reader_length]
    offset += type_reader_length

    # type_reader_version = struct.unpack("<I", data[offset:offset+4])[0]
    offset += 4

    shared_resource_count, offset = read_7bit_encoded_int(data, offset)
    if shared_resource_count != 0:
        print("err Program dosen't deal with shared resources")
        return

    primary_asset, offset = read_7bit_encoded_int(data, offset)
    if primary_asset != 1:
        print("err Program only allows primary asset 1")
        return

    if type_reader == b"Microsoft.Xna.Framework.Content.Texture2DReader":
        surface_format = struct.unpack("<I", data[offset:offset+4])[0]
        offset += 4
        if surface_format:
            print("err Program only allows surface format 0")
            return

        width = struct.unpack("<I", data[offset:offset+4])[0]
        offset += 4

        height = struct.unpack("<I", data[offset:offset+4])[0]
        offset += 4

        mip_count = struct.unpack("<I", data[offset:offset+4])[0]
        offset += 4

        if mip_count != 1:
            print("err Program only allows 1 mip")
            return

        data_size = struct.unpack("<I", data[offset:offset+4])[0]
        offset += 4

        pixel_data = data[offset:offset + data_size]
        offset += data_size

        expected_size = width * height * 4
        if len(pixel_data) != expected_size:
            print(f"err Expected {expected_size} bytes of RGBA data, got {len(pixel_data)}")
            return

        img = Image.frombytes("RGBA", (width, height), bytes(pixel_data))
        dfn = dfn + ".png"
        os.makedirs(os.path.dirname(dfn), exist_ok=True)
        img.save(dfn, "PNG")
        return

    elif type_reader == b"Microsoft.Xna.Framework.Content.SoundEffectReader":
        format_size = struct.unpack("<I", data[offset:offset + 4])[0]
        offset += 4
        if format_size < 16:
            print("err Invalid wave format size")
            return
        format_tag, number_channels, samples_per_second, \
            average_bytes_per_second, block_align, bits_per_sample = \
            struct.unpack("<HHIIHH", data[offset:offset + 16])
        # if format_size >= 18:
        #     extra_size = struct.unpack("<H", data[offset:offset + 2])[0]
        offset += format_size

        data_size = struct.unpack("<I", data[offset:offset + 4])[0]
        offset += 4
        audio_data = data[offset:offset + data_size]
        offset += data_size
        if len(audio_data) != data_size:
            print(f"err Expected {data_size} bytes of audio data, got {len(audio_data)}")
            return

        # print(f"format_tag {format_tag}")
        # print(f"number_channels {number_channels}")
        # print(f"samples_per_second {samples_per_second}")
        # print(f"average_bytes_per_second {average_bytes_per_second}")
        # print(f"block_align {block_align}")
        # print(f"bits_per_sample {bits_per_sample}")

        if (format_tag == 1
        and bits_per_sample == 16):
            dtype = np.int16
            subtype = 'PCM_16'
        elif (format_tag == 3
        and bits_per_sample == 32):
            dtype = np.float32
            subtype = 'FLOAT'
        else:
            print(f"err Program can't handle format tag {format_tag} and bits pre sample {bits_per_sample}")
            return
        audio_data = np.frombuffer(audio_data, dtype=dtype)
        if number_channels != 1:
            audio_data = audio_data.reshape(-1, number_channels)
        dfn = dfn + ".wav"
        os.makedirs(os.path.dirname(dfn), exist_ok=True)
        sf.write(dfn, audio_data, samples_per_second, format='WAV', subtype=subtype)

    else:
        print(f"err Program can't handle {type_reader}")
        return


def read_7bit_encoded_int(data, offset):
    result = 0
    bits_read = 0
    while True:
        value = data[offset]
        offset += 1
        result |= (value & 0x7f) << bits_read
        bits_read += 7
        if not value & 0x80:
            break
    return result, offset


if __name__ == "__main__":
    main()
