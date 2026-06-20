"""
eagl_parser.py
--------------
Parser for EA Sports EAGL Wii .o model files.
No UI dependencies — import and use from any script.

Usage:
    from eagl_parser import parse_o_file, build_obj

    result = parse_o_file("rc_controller.o")
    obj_text = build_obj(result)
    with open("rc_controller.obj", "w") as f:
        f.write(obj_text)

    # Or use the convenience one-liner:
    from eagl_parser import convert
    log_lines = convert("rc_controller.o", "rc_controller.obj")
"""

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ParseResult:
    model_name: str
    material_name: str
    positions: list[tuple[float, float, float]]
    normals: list[tuple[float, float, float]]
    uvs: list[tuple[float, float]]
    # Each face is a triple of (pos_idx, norm_idx, uv_idx), all 0-based
    faces: list[tuple[tuple[int,int,int], tuple[int,int,int], tuple[int,int,int]]]
    log: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.faces) > 0


# ---------------------------------------------------------------------------
# ELF helpers
# ---------------------------------------------------------------------------

def _read_sections(data: bytes) -> tuple[list[dict], int]:
    """Return list of section dicts and the .data section start offset."""
    e_shoff     = struct.unpack_from("<I", data, 32)[0]
    e_shentsize = struct.unpack_from("<H", data, 46)[0]
    e_shnum     = struct.unpack_from("<H", data, 48)[0]
    e_shstrndx  = struct.unpack_from("<H", data, 50)[0]

    sections = []
    for i in range(e_shnum):
        o = e_shoff + i * e_shentsize
        sh = struct.unpack_from("<IIIIIIIIII", data, o)
        sections.append({
            "name_idx": sh[0], "type": sh[1],
            "offset": sh[4], "size": sh[5],
            "link": sh[6], "info": sh[7], "entsize": sh[9],
        })

    shstrtab = sections[e_shstrndx]
    base = shstrtab["offset"]
    for s in sections:
        end = base + s["name_idx"]
        while data[end] != 0:
            end += 1
        s["name"] = data[base + s["name_idx"]:end].decode("ascii", errors="replace")

    return sections, sections[1]["offset"]   # .data is always section 1


# ---------------------------------------------------------------------------
# Symbol / string helpers
# ---------------------------------------------------------------------------

def _read_cstr(data: bytes, offset: int) -> str:
    end = offset
    while data[end] != 0:
        end += 1
    return data[offset:end].decode("ascii", errors="replace")


def _extract_names(data: bytes, sections: list[dict]) -> tuple[str, str]:
    """Return (model_name, material_name) from the symbol table."""
    sym_sec = next((s for s in sections if s["name"] == ".symtab"), None)
    str_sec = next((s for s in sections if s["name"] == ".strtab"), None)
    if not sym_sec or not str_sec:
        return "model", "material"

    model_name    = ""
    material_name = ""
    str_base      = str_sec["offset"]
    entry_size    = sym_sec["entsize"] or 16

    for i in range(sym_sec["size"] // entry_size):
        o = sym_sec["offset"] + i * entry_size
        name_idx = struct.unpack_from("<I", data, o)[0]
        name = _read_cstr(data, str_base + name_idx)
        if ":::".join(("__Model", "")) in name + ":::":
            # __Model:::some_name
            parts = name.split(":::")
            if len(parts) >= 2:
                model_name = parts[1]
        if "TAR:::RUNTIME_ALLOC" in name:
            # e.g. 1=dartguncolor,1;
            import re
            m = re.search(r"1=([^,;]+)", name)
            if m:
                material_name = m.group(1)

    return model_name or "model", material_name or "material"


# ---------------------------------------------------------------------------
# Relocation table → array pointer map
# ---------------------------------------------------------------------------

def _read_pointers(data: bytes, sections: list[dict], data_start: int) -> list[tuple[int, int]]:
    """
    Parse .rel.data and return sorted list of (at_offset, points_to_offset)
    for every R_MIPS_32 (type 2) relocation entry.
    """
    rel_sec = next((s for s in sections if s["name"] == ".rel.data"), None)
    if not rel_sec:
        return []

    pointers = []
    for i in range(rel_sec["size"] // 8):
        o = rel_sec["offset"] + i * 8
        r_off, r_info = struct.unpack_from("<II", data, o)
        if (r_info & 0xFF) == 2:   # R_MIPS_32
            stored = struct.unpack_from("<I", data, data_start + r_off)[0]
            pointers.append((r_off, stored))

    pointers.sort(key=lambda p: p[1])
    return pointers


# ---------------------------------------------------------------------------
# GX display list scanner
# ---------------------------------------------------------------------------

def _scan_gx_strips(
    data_section: bytes,
    max_pos_idx: int,
    max_uv_idx: int,
) -> list[list[tuple[int, int, int]]]:
    """
    Scan for 0x98 (GX TRI_STRIP) commands.
    Returns list of strips; each strip is a list of (pos_idx, norm_idx, uv_idx).
    """
    strips = []
    i = 0
    n = len(data_section)
    while i < n - 3:
        if data_section[i] == 0x98:
            vc = (data_section[i + 1] << 8) | data_section[i + 2]
            if 3 <= vc <= 200 and i + 3 + vc * 3 <= n:
                valid = True
                for v in range(vc):
                    base = i + 3 + v * 3
                    pi = data_section[base]
                    ti = data_section[base + 2]
                    if pi > max_pos_idx or ti > max_uv_idx:
                        valid = False
                        break
                if valid:
                    verts = []
                    for v in range(vc):
                        base = i + 3 + v * 3
                        verts.append((
                            data_section[base],
                            data_section[base + 1],
                            data_section[base + 2],
                        ))
                    strips.append(verts)
                    i += 3 + vc * 3
                    continue
        i += 1
    return strips


def _strips_to_faces(
    strips: list[list[tuple[int, int, int]]],
) -> list[tuple[tuple[int,int,int], tuple[int,int,int], tuple[int,int,int]]]:
    """Expand triangle strips to individual triangles, skipping degenerates."""
    faces = []
    for strip in strips:
        for j in range(len(strip) - 2):
            if j % 2 == 0:
                a, b, c = strip[j], strip[j + 1], strip[j + 2]
            else:
                a, b, c = strip[j + 1], strip[j], strip[j + 2]
            # skip degenerate (any two verts share same position index)
            if a[0] == b[0] or b[0] == c[0] or a[0] == c[0]:
                continue
            faces.append((a, b, c))
    return faces


# ---------------------------------------------------------------------------
# Main parse entry point
# ---------------------------------------------------------------------------

def parse_o_file(path: str | Path) -> ParseResult:
    """
    Parse an EA Sports EAGL Wii .o file.
    Returns a ParseResult (check .ok before using).
    """
    path = Path(path)
    data = path.read_bytes()
    log = []

    # --- ELF validation ---
    if data[:4] != b"\x7fELF":
        return ParseResult("", "", [], [], [], [], log=["Not an ELF file"])
    log.append(f"ELF OK  ({len(data)} bytes)")

    sections, data_start = _read_sections(data)
    data_sec = next((s for s in sections if s["name"] == ".data"), None)
    if not data_sec:
        return ParseResult("", "", [], [], [], [], log=log + ["No .data section"])

    log.append(f".data @ 0x{data_start:04x}  size 0x{data_sec['size']:04x}")

    # --- Names ---
    model_name, material_name = _extract_names(data, sections)
    log.append(f"Model: {model_name}  material: {material_name}")

    # --- Pointer map ---
    pointers = _read_pointers(data, sections, data_start)
    unique_targets = sorted(set(p[1] for p in pointers))
    log.append(f"Reloc pointers: {len(pointers)}  unique targets: {len(unique_targets)}")

    # Locate the three arrays by following the same heuristic as the extractor:
    #   positions  = pointer whose target is 0x010
    #   normals    = next pointer target above positions
    #   uvs        = next pointer target above normals
    #   gx         = next pointer target above uvs
    pos_target  = next((t for t in unique_targets if t == 0x010), None)
    if pos_target is None:
        return ParseResult(model_name, material_name, [], [], [], [],
                           log=log + ["Cannot find position array (no ptr to 0x010)"])

    above_pos  = [t for t in unique_targets if t > pos_target]
    above_norm = [t for t in unique_targets if t > (above_pos[0]  if above_pos  else pos_target)]
    above_uv   = [t for t in unique_targets if t > (above_norm[0] if above_norm else pos_target)]

    if not above_pos or not above_norm or not above_uv:
        return ParseResult(model_name, material_name, [], [], [], [],
                           log=log + ["Cannot resolve norm/UV/GX array offsets"])

    pos_off  = pos_target
    norm_off = above_pos[0]
    uv_off   = above_norm[0]
    gx_off   = above_uv[0]

    # --- Count arrays from gaps ---
    n_pos  = (norm_off - pos_off) // 12
    n_norm = (uv_off   - norm_off) // 6
    n_uv   = (gx_off   - uv_off)  // 8

    log.append(f"Array counts — pos: {n_pos}  norm: {n_norm}  uv: {n_uv}")

    if not (1 <= n_pos <= 2000 and 1 <= n_norm <= 2000 and 1 <= n_uv <= 2000):
        return ParseResult(model_name, material_name, [], [], [], [],
                           log=log + [f"Implausible array sizes, aborting"])

    # --- Read positions (BE float3, stride 12) ---
    positions: list[tuple[float,float,float]] = []
    for i in range(n_pos):
        o = data_start + pos_off + i * 12
        x, y, z = struct.unpack_from(">fff", data, o)
        positions.append((x, y, z))

    # --- Read normals (s8×3, stride 6, ÷127) ---
    normals: list[tuple[float,float,float]] = []
    for i in range(n_norm):
        o = data_start + norm_off + i * 6
        nx, ny, nz = struct.unpack_from("bbb", data, o)
        normals.append((nx / 127.0, ny / 127.0, nz / 127.0))

    # --- Read UVs (BE float2, stride 8, V flipped) ---
    uvs: list[tuple[float,float]] = []
    for i in range(n_uv):
        o = data_start + uv_off + i * 8
        u, v = struct.unpack_from(">ff", data, o)
        uvs.append((u, 1.0 - v))

    # --- GX display list scan ---
    data_section = data[data_start : data_start + data_sec["size"]]
    strips = _scan_gx_strips(data_section, max_pos_idx=n_pos - 1, max_uv_idx=n_uv - 1)
    faces  = _strips_to_faces(strips)

    log.append(f"GX strips: {len(strips)}  triangles: {len(faces)}")

    if not faces:
        log.append("WARNING: no faces extracted")

    return ParseResult(
        model_name=model_name,
        material_name=material_name,
        positions=positions,
        normals=normals,
        uvs=uvs,
        faces=faces,
        log=log,
    )


# ---------------------------------------------------------------------------
# OBJ builder
# ---------------------------------------------------------------------------

def build_obj(result: ParseResult) -> str:
    """Convert a ParseResult into a Wavefront OBJ string."""
    lines = [
        f"# {result.model_name}",
        "# Exported from EA Sports .o (EAGL Wii) file",
        "",
        f"o {result.model_name}",
        "",
    ]
    for x, y, z in result.positions:
        lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
    lines.append("")
    for u, v in result.uvs:
        lines.append(f"vt {u:.6f} {v:.6f}")
    lines.append("")
    for nx, ny, nz in result.normals:
        lines.append(f"vn {nx:.6f} {ny:.6f} {nz:.6f}")
    lines.append("")
    lines.append(f"usemtl {result.material_name}")
    lines.append("")
    for a, b, c in result.faces:
        def fmt(v):
            return f"{v[0]+1}/{v[2]+1}/{v[1]+1}"
        lines.append(f"f {fmt(a)} {fmt(b)} {fmt(c)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------

def convert(input_path: str | Path, output_path: str | Path) -> list[str]:
    """
    Parse input_path and write OBJ to output_path.
    Returns the log lines from parsing.
    """
    result = parse_o_file(input_path)
    if result.ok:
        obj_text = build_obj(result)
        Path(output_path).write_text(obj_text)
        result.log.append(f"Written → {output_path}")
    else:
        result.log.append("Conversion failed — no OBJ written")
    return result.log


# ---------------------------------------------------------------------------
# CLI fallback
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python eagl_parser.py <file.o> [output.obj]")
        sys.exit(1)
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else inp.with_suffix(".obj")
    for line in convert(inp, out):
        print(line)
