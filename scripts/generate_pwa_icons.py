import os
import struct
import zlib

def create_png(width, height, filename):
    # Palette/Colors:
    # Background: #0B72E7 (11, 114, 231)
    # Center circle: #0F172A (15, 23, 42)
    # Lightning / Star: #38BDF8 / #FBBF24
    raw_data = bytearray()
    cx, cy = width // 2, height // 2
    r_outer = width * 0.44
    r_inner = width * 0.38

    for y in range(height):
        raw_data.append(0) # Filter type 0 (None)
        for x in range(width):
            dx = x - cx
            dy = y - cy
            dist = (dx * dx + dy * dy) ** 0.5

            if dist > r_outer:
                # Outside rounded icon
                raw_data.extend([11, 114, 231, 255])
            elif dist > r_inner:
                # Border ring
                raw_data.extend([56, 189, 248, 255])
            else:
                # Inner dark blue canvas
                # Lightning bolt shape approximation
                # Center bolt:
                is_bolt = False
                nx = (x - cx) / width
                ny = (y - cy) / height

                # Simplified lightning polygon test
                if (-0.15 <= nx <= 0.15) and (-0.25 <= ny <= 0.25):
                    if (-ny * 0.6 + nx) > -0.05 and (-ny * 0.6 + nx) < 0.15:
                        is_bolt = True

                if is_bolt:
                    raw_data.extend([251, 191, 36, 255]) # Golden yellow
                else:
                    raw_data.extend([15, 23, 42, 255])   # Midnight blue

    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xffffffff)
        return struct.pack(">I", len(data)) + c + crc

    png_bytes = b"\x89PNG\r\n\x1a\n"
    # IHDR
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png_bytes += chunk(b"IHDR", ihdr)
    # IDAT
    compressed = zlib.compress(bytes(raw_data), 9)
    png_bytes += chunk(b"IDAT", compressed)
    # IEND
    png_bytes += chunk(b"IEND", b"")

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "wb") as f:
        f.write(png_bytes)
    print(f"Created {filename} ({width}x{height})")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icons_dir = os.path.join(base_dir, "static", "icons")
    create_png(192, 192, os.path.join(icons_dir, "icon-192.png"))
    create_png(512, 512, os.path.join(icons_dir, "icon-512.png"))
