# UnpackEA Graphics Library — Wii

> Extract, parse, and convert Wii EA Graphics Library (EAGL) models, terrain, skeletons, and animations into modern GLB files.

---

## Overview

**UnpackEA Graphics Library — Wii** is a reverse-engineered toolkit for reading and converting proprietary EA Graphics Library (EAGL) assets from Wii-era game titles. It reconstructs binary model, terrain, skeleton, and animation data as standards-compliant **GLB (glTF Binary)** files, ready for Blender, Unity, Unreal Engine, and modern preservation workflows.

The project bridges legacy console assets and modern tooling while documenting the format carefully: layouts and codecs are verified against real asset corpora and the game runtime rather than inferred from appearance alone.

---

## Features

- **Binary EAGL Parsing** — Deep parsing of proprietary Wii EAGL asset formats
- **Terrain Extraction** — Reconstruction of large-scale game terrain and world geometry
- **Character Model Export** — Static character mesh extraction with skeleton-aware export
- **Skeletal Export** — 68-bone hierarchy, names, and bind-pose parsing
- **Full Animation Export** — All 265 clips in the current `player_anims.anm` corpus export to GLB
- **GLB Output** — Standards-compliant glTF Binary for major 3D tools
- **GX Display List Recovery** — Defensive vertex-stride detection and bounds validation to prevent silent geometry corruption
- **Codec Validation** — Decoder layouts, channel mapping, and output ranges are checked against the game executable and corpus-wide regression tests
- **Data-Driven Layout Detection** — Mesh layouts live in external JSON definitions, so additional formats can be added without changing parser code


---

## Gallery

### Character Models
<img width="1907" height="1072" alt="Screenshot 2026-07-02 092528" src="https://github.com/user-attachments/assets/f010026e-e3b5-441b-a8b4-c2dc18da5d33" />

### Terrain & World Geometry
<p align="center">
 <img width="666" height="375" alt="terrain-removebg-preview" src="https://github.com/user-attachments/assets/c813dfc7-f2e5-496d-ad84-e562d942b89b" />
  <img width="800" height="356" alt="gif" src="https://github.com/user-attachments/assets/8d89b320-4c1b-4fef-9632-9c9be702a86c" />
</p>

### 3D Model Extraction
<p align="center">
  <img width="1723" height="1095" alt="Screenshot 2026-07-02 082427" src="https://github.com/user-attachments/assets/a601bccd-e2b5-4290-a3da-798f60b7c871" />
</p>
<p align="center">
  <img src="https://github.com/user-attachments/assets/a849cbdc-e127-4911-b255-df8b6879ba48" width="49%" />
  <img src="https://github.com/user-attachments/assets/ea0c8419-4577-46d1-a399-42ae9b2b9741" width="49%" />
  <img src="https://github.com/user-attachments/assets/d2b48cc6-6ffa-4a23-9b26-b99523091775" width="49%" />
</p>

---

## Version History

### Version 10 *(Current — Complete Animation Pipeline)*

Animation support is now complete for the current EA Playground `player_anims.anm` bank: **265/265 clips export successfully to GLB**, with zero structural export failures and zero out-of-range bone references.

The exporter combines the `.anm` bank with the 68-bone `.ske` skeleton and produces one animated GLB per clip. Its five observed runtime codecs were decoded from the game's Gekko/Broadway PowerPC implementation and validated across the full corpus:

| Codec combination | Clips | Exported data |
|---|---:|---|
| `FnDeltaQFast` + `FnDeltaF3` | 224 | Quaternion rotation + XYZ translation |
| `FnDeltaQFast` + `FnDeltaF1` | 20 | Quaternion rotation + single-axis translation |
| `FnDeltaSingleQ` + `FnDeltaQFast` | 9 | Two complementary rotation tracks |
| `FnStatelessQ` + `FnStatelessF3` | 12 | Keyframe quaternion rotation + vector translation |
| **Total** | **265** | **One GLB per clip** |

Key improvements:

- **Complete codec coverage** — `FnDeltaQFast`, `FnDeltaF3`, `FnDeltaF1`, `FnDeltaSingleQ`, `FnStatelessQ`, and `FnStatelessF3` are implemented for every combination exercised by the bank.
- **Correct bone/channel resolution** — vector-channel entries use the engine’s encoded pose-target layout, avoiding the earlier incorrect `entry // 3` interpretation.
- **Stateless animation support** — keyframe-based quaternion and vector tracks, including runtime-style interpolation, are exported for the 12 previously uncovered clips.
- **Complementary rotation tracks** — the nine `FnDeltaSingleQ` clips are correctly handled as two non-overlapping rotation tracks, not rotation plus translation.
- **Clean-room regression** — a fresh installation exported all 265 clips successfully; the regenerated GLBs matched the development output byte-for-byte.

> Known limits: sparse stateless keyframe-time tables are not exercised by this corpus; extra stateless channels fall back to bind pose; playback timing currently uses a documented 30 FPS placeholder. Runtime and numeric validation are complete, but a final visual check in Blender remains worthwhile for confirming coordinate and quaternion conventions.

<details>
<summary>Previous Versions</summary>

### Version 9 *(GX Display-List Reliability)*

Fixed a class of silent-corruption bugs in the GX display-list reader where a mis-guessed vertex stride could produce confidently wrong geometry instead of visibly failing.

- **Normal-index bounds checks** — final triangle extraction now validates normal indices alongside position and UV indices.
- **Full stride probing** — position, normal, and UV index widths are evaluated in combination rather than only varying UV width.
- **Safe zero-score fallback** — ambiguous stride probes now retain the original declaration and surface as an empty mesh instead of selecting an arbitrary bad match.

**Result:** EVERY `.o` increased triangles, with zero remaining out-of-bounds normal-index references across all.

---

### Version 8 *(Character Models)*

Two-part fix for `INDEX8`/`INDEX16` stride detection on meshes whose GX attribute list is offset unexpectedly or whose `TEX0` entry uses type `0x00`.

- Recover the real attribute list at `off_attr + 8` when the primary slot is invalid.
- Infer `INDEX16` UVs when the stream and surrounding attributes require it, even if the descriptor reports `0x00`.

---

### Version 7 *(Character Models)*

First focused character-model extraction release, building on data-driven layout detection and adding initial geometry reconstruction with UV support.

---

### Version 6 *(Parser — Data-Driven Layout Detection + Layout C)*

Added Layout C support for track and terrain geometry, including its non-aligned GX display-list relocation and four-byte normal stride. Mesh layout definitions were moved to `eagl_layouts.json`, where signature checks are used to select the best matching layout.

---

### Version 4 *(Parser — GX Scan Window Fix)*

Fixed mesh-boundary detection in the GX scanner. Scan ranges are now bounded by the next mesh’s actual position-array pointer, preventing neighboring data from being misread as triangle-strip commands.

</details>

---

## Getting Started

> Documentation and usage instructions is under construction. 

```bash
# Clone the repository
git clone <repository-url>
cd <repository-directory>

# Export the current animation corpus
python anm_exporter.py
```

---

## Roadmap

- [x] Static 3D model extraction
- [x] GLB export pipeline
- [x] Data-driven layout detection (`eagl_layouts.json`)
- [x] Terrain support
- [x] Character model extraction
- [x] Built-in parser for compressed `.gsh` textures
- [x] Defensive parser rewrite and edge-case review
- [x] Skeletal support
- [x] Full animation support
- [ ] Mesh skin weights / fully skinned character export *(in progress)*
- [ ] Batch processing
- [ ] Blender plugin
- [ ] Integrated BIG archive extraction

---

## Contributing

Contributions, reports, and reverse-engineering findings are welcome. Please open an issue or submit a pull request.

---

## License

This project is intended for preservation and research purposes. All game assets belong to their respective copyright holders.

This project contains no original game assets.
