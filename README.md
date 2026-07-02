
# UnpackEA Graphics Library — Wii

> Extract, parse, and convert Wii EA Graphics Library (EAGL) 3D models and terrains into modern GLB files.

---

## Overview

**UnpackEA Graphics Library — Wii** is a reverse-engineered toolkit for reading and converting proprietary EA Graphics Library (EAGL) assets from Wii game titles. It decodes binary 3D model and terrain data from EA's closed format and reconstructs them as standards-compliant **GLB (glTF Binary)** files — ready for use in Blender, Unity, Unreal Engine, or any modern 3D pipeline.

This project bridges the gap between legacy console game assets and modern tooling, enabling preservation, research, and creative reuse of Wii-era EA game content.

---

## Features

- **Binary EAGL Parsing** — Deep binary parsing of EA's proprietary Wii graphics format
- **Terrain Extraction** — Full reconstruction of large-scale game terrain meshes
- **Character Model Export** — *(bone support in progress)*
- **GLB Output** — Industry-standard glTF Binary output compatible with all major 3D tools
- **Data-Driven Layout Detection** — Descriptor layouts are defined in an external JSON config, making it easy to support new mesh formats without touching parser code

---

## Gallery
### Character Models
<img width="2080" height="1093" alt="image" src="https://github.com/user-attachments/assets/aa6a0ba2-4446-4ff5-ac3a-249d7a78fcf0" />


### Terrain & World Geometry
<p align="center">
  <img src="https://github.com/user-attachments/assets/685c1258-28e8-4701-9211-1a41e5e1690e" width="49%" />
  <img width="800" height="356" alt="gif" src="https://github.com/user-attachments/assets/8d89b320-4c1b-4fef-9632-9c9be702a86c" />
  <img src="https://github.com/user-attachments/assets/35a0fdb1-4799-4cb2-8f8e-f9424e142147" width="49%" />
</p>

### 3D Model Extraction

<p align="center">
  <img width="1723" height="1095" alt="image" src="https://github.com/user-attachments/assets/d4e2d36e-f57e-4a8d-aa6d-993867566c31" />
  <img src="https://github.com/user-attachments/assets/a849cbdc-e127-4911-b255-df8b6879ba48" width="49%" />

</p>
<p align="center">

</p>
<p align="center">
  <img src="https://github.com/user-attachments/assets/ea0c8419-4577-46d1-a399-42ae9b2b9741" width="49%" />
  <img src="https://github.com/user-attachments/assets/d2b48cc6-6ffa-4a23-9b26-b99523091775" width="49%" />
  



</p>

---

## Version History

---

### Version 9 *(Current — Character Models)*
<p align="center">
  <img src="https://github.com/user-attachments/assets/7c32c93f-dca1-4447-80a9-31ce72376ced" width="80%" />
</p>
<img width="2168" height="1125" alt="image" src="https://github.com/user-attachments/assets/75bacc88-d569-4832-a3f3-05531b5cffbb" />


Continued refinement of character geometry extraction. Builds on the UV and normal reconstruction improvements from v8, with further accuracy gains in mesh topology and edge cases in the GX display list reader for character-specific descriptors.

<details>
<summary>Previous Versions</summary>

### Version 8 *(Character Models)*

<p align="center">
  <img src="https://github.com/user-attachments/assets/99add145-d321-42a0-bb0f-025e8cae6fbf" width="49%" />
  <img src="https://github.com/user-attachments/assets/352a5630-2043-42df-99ca-e2fdfe68da1c" width="49%" />
</p>

Improved UV mapping reconstruction and normal data handling for character meshes. Addressed seam artifacts and per-vertex attribute misalignment carried over from v7.

---

### Version 7 *(Character Models)*

<p align="center">
  <img src="https://github.com/user-attachments/assets/d6015233-1fd4-4586-97f6-2b437e131764" width="80%" />
</p>

First version to focus specifically on character model extraction, leveraging the data-driven layout detection system introduced in the parser rewrite (v6/v7). Initial geometry reconstruction with basic UV support.

---

### Version 6 *(Parser — Data-Driven Layout Detection + Layout C)*

<p align="center">
  <img src="https://github.com/user-attachments/assets/0696b5ae-ec83-47bb-abde-2701ef331e9d" width="80%" />
</p>

Two major advances landed in this version:

**Layout C support** (`byte[0] == 0x02`) — covers track and terrain geometry such as *TestTrackforTodd*. Unlike Layouts A/B, Layout C has a non-aligned reloc at `desc+0x09` that points directly to the GX display list rather than deriving the GX start from the UV array end. Array counts are derived from pointer gaps instead of stored fields (the descriptor's count fields hold unrelated data in this layout), and the normal stride is 4 bytes (`s8×3` + 1 pad byte) instead of 6. Detection requires `byte[0] == 0x02`, the non-aligned reloc at `+0x09` pointing past `ptr_uv`, and the standard `+0x34` / `+0x3c` / `+0x44` reloc triple.

**Data-driven layout detection** — Layout definitions were extracted from the parser into `eagl_layouts.json`. Each layout carries a list of `signature_checks` (`magic`, `reloc_exists`, `reloc_order`, `count_range`, `reloc_absent`). Rather than a hard magic-byte lookup, every layout is now **scored against every candidate descriptor offset**, and the winner is chosen if it clears a minimum score threshold and leads the runner-up by at least a defined margin. Adding support for a new layout no longer requires touching parser code — just edit the JSON.

---

### Version 4 *(Parser — GX Scan Window Fix)*

Critical fix for a mesh boundary bug in the GX display list scanner. The old scan window was bounded by `vtx_count * stride + 2048` — an estimate that routinely overran into adjacent meshes' float and byte data. Embedded `0x98` bytes in that neighboring data were misread as GX triangle-strip headers, producing spurious triangles with out-of-range normal indices, visible as **mesh tearing and corrupted faces**.

The fix bounds the scan window by the **next mesh's actual position-array pointer** instead. Descriptors are now also sorted by their pos-array pointer before GX boundaries are computed, ensuring correct ordering regardless of descriptor discovery order. `_parse_mesh` now accepts an explicit `gx_end` argument rather than estimating it from the descriptor's vertex count field.
<img width="3832" height="2045" alt="Screenshot 2026-06-15 222327" src="https://github.com/user-attachments/assets/a329ccad-8fef-4ce5-94fa-3d59e265daa6" />
</details>

---

## Getting Started

> Documentation and usage instructions coming soon.

```bash
# Clone the repository
git clone https://github.com/sirshoqckings/UnpackEA-Graphics-Lirbray-Wii.git
cd UnpackEA-Graphics-Lirbray-Wii
```

---

## Roadmap

- [x] Terrain mesh extraction
- [x] Static 3D model extraction
- [x] GLB export pipeline
- [x] Layout C support (track/terrain geometry)
- [x] Data-driven layout detection (`eagl_layouts.json`)
- [x] Character model extraction
- [x] Built-in parser for compressed .gsh textures
- [ ] Code Review and rewrite for performance/edge cases *(in progress)*
- [ ] Skeletal / bone data support *(in progress)*
- [ ] Animations *(in progress)*
- [ ] Blender Plugin
- [ ] Batch Processing
- [ ] Integrated BIG Archive extract

---

## Contributing

Contributions, reports, and reverse-engineering findings are welcome. Feel free to open an issue or submit a pull request.

---

## License

This project is intended for preservation and research purposes. All game assets belong to their respective copyright holders.

This project contains no original game assets.
