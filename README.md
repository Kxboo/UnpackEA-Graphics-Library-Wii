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
- **Character Model Export** *(In Development)* — Skeletal mesh extraction with geometry and UV mapping
- **GLB Output** — Industry-standard glTF Binary output compatible with all major 3D tools
- **Mesh Fidelity** — High-accuracy vertex, normal, and UV data reconstruction

---

## Gallery
### Character Models
<img width="2112" height="1139" alt="Screenshot 2026-06-19 222532" src="https://github.com/user-attachments/assets/ad835815-c3ff-4c4c-8bd2-f6ef54409592" />

### Terrain & World Geometry
<p align="center">
  <img src="https://github.com/user-attachments/assets/685c1258-28e8-4701-9211-1a41e5e1690e" width="49%" />
  <img src="https://github.com/user-attachments/assets/35a0fdb1-4799-4cb2-8f8e-f9424e142147" width="49%" />
</p>

### 3D Model Extraction

<p align="center">
  <img src="https://github.com/user-attachments/assets/71defffe-eb6c-43ff-8fe5-a15fedbabbac" width="49%" />
  <img src="https://github.com/user-attachments/assets/a849cbdc-e127-4911-b255-df8b6879ba48" width="49%" />
</p>
<p align="center">
  <img src="https://github.com/user-attachments/assets/7977d7e1-75d6-4683-b476-0b0257402a18" width="49%" />
  <img src="https://github.com/user-attachments/assets/5ba5a0cc-1e86-4be0-a89e-ef2edb31c19f" width="49%" />
</p>
<p align="center">
  <img src="https://github.com/user-attachments/assets/ea0c8419-4577-46d1-a399-42ae9b2b9741" width="49%" />
  <img src="https://github.com/user-attachments/assets/d2b48cc6-6ffa-4a23-9b26-b99523091775" width="49%" />
</p>
---

## In Development — Character Export

Character model extraction is actively being developed. Each iteration improves mesh accuracy, UV reconstruction, and geometry fidelity.

---
### Version 9 *(Current)*
<p align="center">
  <img src="[https://github.com/user-attachments/assets/d6015233-1fd4-4586-97f6-2b437e131764](https://github.com/user-attachments/assets/7c32c93f-dca1-4447-80a9-31ce72376ced)" width="80%" />
</p>
<img width="2112" height="1139" alt="Screenshot 2026-06-19 222532" src="https://github.com/user-attachments/assets/ad835815-c3ff-4c4c-8bd2-f6ef54409592" />
<details>
<summary>Previous Versions</summary>
  
### Version 8 

<p align="center">
  <img src="https://github.com/user-attachments/assets/99add145-d321-42a0-bb0f-025e8cae6fbf" width="49%" />
  <img src="https://github.com/user-attachments/assets/352a5630-2043-42df-99ca-e2fdfe68da1c" width="49%" />
</p>

---

### Version 7

<p align="center">
  <img src="https://github.com/user-attachments/assets/d6015233-1fd4-4586-97f6-2b437e131764" width="80%" />
</p>

### Version 6

<p align="center">
  <img src="https://github.com/user-attachments/assets/0696b5ae-ec83-47bb-abde-2701ef331e9d" width="80%" />
</p>

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
- [ ] Character model extraction *(in progress)*
- [ ] Skeletal / bone data support
- [ ] Texture extraction and embedding
- [ ] Full CLI interface

---

## Contributing

Contributions, bug reports, and reverse-engineering findings are welcome. Feel free to open an issue or submit a pull request.

---

## License

This project is intended for preservation and research purposes. All game assets belong to their respective copyright holders.
