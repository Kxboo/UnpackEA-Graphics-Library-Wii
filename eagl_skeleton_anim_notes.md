# EAGL `.ske` / `.anm` Reverse-Engineering Notes

Scratch doc — session covering `player_skel.ske` and `player_anims.anm`.
Companion to the mesh-side `eagl_layouts.json` / `parser.py` / `eagl_inspect.py` toolchain.
Both files are MIPS R3000 ELF relocatables, same container family as the `.o` mesh files.

---

## 1. `player_skel.ske` — Skeleton / Bone Hierarchy — **SOLVED**

> Update: full format cracked and implemented in `eagl_skeleton.py`. The
> boundary ambiguity flagged below was resolved (table starts at `0x450`,
> 16-byte header, NOT `0x460`/32-byte — confirmed by testing which boundary
> makes the `(1,1,1)` scale marker land at a consistent sub-offset across
> all 68 bones: `0x450` scores 68/68, `0x460` only 67/68). Parent-index
> field, quaternion, and rotation matrix were all verified against real
> data (chain continuity, unit quaternion magnitude, orthonormal det=+1
> rotation matrix, left/right mirror symmetry). See `eagl_skeleton.py` for
> the working parser. Sections below are kept as historical working notes.
>
> **SUPERSEDING CORRECTION (later session):** the field at bytes `[24:27]`
> (originally documented below as "WORLD-SPACE bind-pose translation") was
> proven UNRELIABLE — it produces anatomically impossible bone lengths for
> 20 of 67 non-root bones. The field at bytes `[8:11]` (originally
> "unidentified vec3") is the real ground-truth **LOCAL (parent-relative)**
> translation: composing `world_pos[i] = world_pos[parent] +
> world_matrix[parent] @ local_vec[i]` up the chain produces ZERO
> anatomically-implausible bones, exact left/right mirror symmetry to 4
> decimal places, and a monotonic head-to-toe height progression — none of
> which held under the old interpretation. Similarly, the `[12:24]` matrix
> block is just a CACHED world rotation derived from the local quaternion
> (verified by composing the quaternion chain and finding an exact match),
> not independently meaningful. **Use `quaternion` + `unknown_vec` (=
> `local_translation`) as the ground truth; do not use `matrix` or
> `translation` for posing/export/skinning.** `eagl_skeleton.py`'s
> `BoneRecord.world_translation` / `world_matrix` properties already
> implement the correct forward-kinematics composition — use those rather
> than the raw stored fields. The field descriptions immediately below are
> kept verbatim as historical working notes; see the corrected summary in
> §3 "Current Status Summary" for the authoritative version.

### Container
- ELF32, MIPS R3000, single `.data` section (file offset `0x40`, size `0x2220`).
- **No `.rel.data` section at all** — unlike mesh `.o` files, bone references are
  plain integers/indices, not linker-relocated pointers. `_build_reloc_map()`
  will correctly return `{}` for this file type; don't expect relocs here.
- Symbol table: 68× `__Bone:::Root.<name>` symbols + 1× `__Skeleton:::Root`.
  Mirrors the `__BBOX:::` / `__Model:::` convention from mesh files — reuse
  `_read_sections()` / `_read_cstr()` from `parser.py` directly, no new ELF code needed.
- **Important:** symbol `size` field is 4 (not 16) — the symbol only tags the
  first word of each slot.

### Layout (confirmed)

```
0x000 - 0x42F   Bone index table. 68 entries x 16 bytes.
                  +0x00: u32 BE bone index (0, 1, 2, ... 67) — matches symbol order
                  +0x04..0x0F: zero padding
                (This table = name/symbol -> sequential index lookup only.
                 No transform data lives here.)

0x430           Last bone slot ("BONE" / unnamed, index 67)

0x440 - 0x45F   Skeleton header (32 bytes), tagged by __Skeleton:::Root symbol
                  +0x00: u32 BE  0x060602a8  — unknown (flags? sub-counts? — NOT solved)
                  +0x04: u32 BE  0            — pad
                  +0x08: u32 BE  68           — bone_count (CONFIRMED: matches symbol count)
                  +0x0C: u32 BE  0            — pad
                  +0x10: f32 BE  1.0          \
                  +0x14: f32 BE  1.0           > looks like a root-level (1,1,1) scale
                  +0x18: f32 BE  1.0          /
                  +0x1C: i32 BE  -1           — looks like root parent_index = -1 (sentinel)
                (NOTE: this 16-byte tail at 0x450-0x45F overlaps suspiciously with
                 the start of the per-bone table below — needs re-verification,
                 see Open Questions.)

0x460 - end     Per-bone record table. 68 records x 112 bytes = 7616 bytes.
                  0x460 + 68*112 = 0x2220 = end of .data section EXACTLY. Confirmed fit.
```

### Per-bone record (112 bytes) — **SOLVED**

Confirmed field layout, 28x f32 BIG-endian per record:

```
[0:3]    f32x3   scale              — observed (1,1,1) for every bone in this file
[3]      i32     parent_idx         — -1 for root; CONFIRMED via full chain
                                       walk, produces a perfectly sane humanoid
                                       hierarchy (see Bone Hierarchy section)
[4:8]    f32x4   quaternion (x,y,z,w) — CONFIRMED unit length (mag=1.0) for
                                       every bone tested
[8:11]   f32x3   unidentified vec3  — real per-bone data, NOT redundant with
                                       translation, exact meaning still open
                                       (see Open Questions)
[11]     f32     pad/unused (0)
[12:24]  f32x12  4x4 row-major affine matrix:
                   rows 0-2 = rotation, CONFIRMED orthonormal (pairwise dot
                   products ~0.0, determinant ~1.0 i.e. a proper rotation,
                   not a reflection); each row's 4th float = 0 (homogeneous)
[24:27]  f32x3   translation (= matrix row 3) — WORLD-SPACE bind-pose
                   position. Confirmed NOT parent-relative: magnitude grows
                   monotonically walking outward along a chain (root->hand),
                   and left/right symmetric bones (l_arm vs r_arm, l_foot vs
                   r_foot) show clean mirror-image values once correct
                   parent indices are used.
[27]     f32     homogeneous row terminator (1.0)
```

Old guesses tested and rejected during derivation: flat 4x4 row-major or
column-major matrix across the WHOLE 112 bytes (failed unit-row/column
checks); 16-byte header with table starting at `0x460` (only matched 67/68
bones' scale-marker position, vs 68/68 for the correct `0x450` boundary).

### Bone hierarchy (name order = symbol/index order, NOT necessarily parent order)

```
 0 Root             18 headcontrol      36 pelvis            54 l_UpperCheekPivot
 1 Spine1           19 l_eye            37 l_upperleg         55 r_UpperCheekPivot
 2 spine2           20 r_eye            38 l_lowerleg         ...
 3 l_Clav           21 jaw              39 l_foot
 4 l_arm            22 joint58          40 l_toe
 5 l_forearm        23 r_eyebrow        41 joint28
 6 l_hand           24 r_eyebrow_in     42 r_upperleg
 7 l_palm           25 r_eyebrow_out    43 r_lowerleg
 8 l_pinky          26 l_eyebrow        44 r_foot
 9 l_pinky2         27 l_eyebrow_in     45 r_toe
10 l_middle         28 l_eyebrow_out    46 joint95
11 l_middle2        29 l_eyelid         47 BONE (unnamed)
12 l_index          30 r_eyelid
13 l_index2         31 mouth
14 l_thumb          32 L_upperlip
15 l_thumb2         33 l_mouthcorner
16 l_prop           34 r_mouthcorner
17 r_Clav           35 R_upperlip
...
```
(Full 68-name list extracted via `nm player_skel.ske`; index = symbol value / 0x10.)

Index walk order strongly implies depth-first traversal: root -> spine chain
-> left arm -> left hand fingers -> right clavicle (jumps back to spine-level)
-> ... -> neck/head/face cluster (very detailed: split eyebrows in/out, cheek
pivots, lip corners, jaw, eyes) -> pelvis -> leg chains. Actual parent indices
are NOT yet extracted (see above) — this is inferred from naming/ordering only.

`joint28`, `joint58`, `joint95`, `BONE` are unnamed/auxiliary bones (helper or
twist bones never given semantic names by original riggers).

---

## 2. `player_anims.anm` — Animation Clip Bank

### Container
- ELF32, MIPS R3000, `.data` size `0x3c2220` (~3.9 MB — matches file size).
- **DOES have `.rel.data`** (2756 entries) — more like the mesh `.o` files.
  Use `_build_reloc_map()` as normal here.
- Only 1 meaningful symbol: `__AnimationBank:::player_anims` at `0x3c2200`,
  i.e. 32 bytes before the very end of `.data`. Same "header lives at the end,
  points backward via relocs" pattern as `__BBOX:::`.

### AnimationBank header (24 bytes, BIG-endian)

```
0x3c2200: u32 BE   28      — unknown (constant? version/type tag?)
0x3c2204: u32 BE   265     — clip_count (CONFIRMED — matches expected scale
                              given file size and the long ANIM_* list in player.csv)
0x3c2208: u32 BE   0       — pad
0x3c220c: u32 BE   0       — pad
0x3c2210: reloc -> 0x3c19b4   — ptr_clip_offsets  (array A)
0x3c2214: reloc -> 0x3c1dd8   — ptr_clip_counts   (array B)
```
(Bytes immediately after 0x3c2218 are NOT part of the struct — that's where
`.data` ends and `.shstrtab` string table content (".data\0.shstrtab\0...")
bleeds into the next section. Don't mistake it for AnimationBank fields.)

### Array A — clip data offsets (`0x3c19b4`, 265 x u32 **LITTLE-endian**)

- Strictly monotonically increasing.
- `arr1[0] = 0x245c`, `arr1[264] = 0x3c199c` (lands exactly before `ptr1`
  itself at `0x3c19b4` — confirms this is the last clip's start offset and
  the table is correctly bounded).
- **Endianness is little-endian**, NOT big-endian like everything else in
  `.ske` and like the mesh-file floats. This was confirmed by comparing
  raw bytes (`5c 24 00 00`) against both interpretations — only LE gives a
  monotonic, sane-range sequence. **Mixed endianness across tables within
  the same file — important gotcha for the parser.**
- Implicit clip N size = `arr1[N+1] - arr1[N]` (last clip's size needs a
  different upper bound — probably `ptr1` itself, i.e. `0x3c19b4 - arr1[264]`).

### Array B — per-clip secondary value (`0x3c1dd8`, 265 x u32 **little-endian**)

- Also strictly increasing, small deltas (9-21 per step, avg ~14).
- Hypothesis was "bone track count per clip" — **REJECTED**: clip 0's byte
  size (79,472 bytes, from arr1[0] to arr1[1]) doesn't divide cleanly by
  arr2[0]=14 (5676.6 bytes/track, not a clean number).
- Most likely candidates not yet tested: cumulative running total of
  something PER-CLIP (deltas are too small/uniform to be byte sizes, more
  likely a count) — e.g. cumulative event-marker count, cumulative
  string-table entries (clip name length offsets?), or unrelated to arr1
  entirely (separate indexing scheme, e.g. into `player.csv`'s ANIM_STATE
  rows — note player.csv has ~236 data rows, suspiciously close to 265).

### Clip header structure — **SOLVED** (track list + per-track sub-records identified)

Each clip (located via Array A's byte offset) has a header that uses REAL
relocations — `_build_reloc_map()` from `parser.py` works unmodified here
(this file, unlike `.ske`, DOES have `.rel.data`). Confirmed structure,
verified against clip 169 (smallest clip in the file, 1224 bytes,
offset `0x2242f4`):

```
clip header (32 bytes):
  +0x00  u32 BE   unknown (e.g. 0x000fc6e4) — NOT a reloc, possibly packed
                   flags/frame-count, low halfword 0xc6e4 recurs as a magic/
                   type tag in EVERY per-track sub-record too (see below)
  +0x04  reloc -> bone_index_list   (ptr_A) — see below
  +0x08  u32 BE   unknown (e.g. 0x00030017) — NOT a reloc, two u16 halves
                   (0x0003, 0x0017=23) — possibly track_count / list_length;
                   23 is close to but doesn't exactly match observed track
                   count for this clip (17 tracks from ptr_A's list, see
                   below) — needs re-checking, may be a different count
                   (e.g. total keyframe count across all tracks)
  +0x0c  reloc -> per-track record 0   (ptr_B)
  +0x10  reloc -> per-track record 1   (ptr_C)
  +0x14  reloc -> per-track record 2   (ptr_D)
  +0x18  u32 BE   0           — pad/terminator?
  +0x1c  u32 BE   1           — unknown, possibly "more records follow" flag
                                 or version tag
```

IMPORTANT — only 3 track pointers (+0x0c/+0x10/+0x14) were directly visible
in the 32-byte header dumped so far, but ptr_A's bone list has MANY more
entries (17 bones) than that. **The per-track pointer array almost certainly
continues past +0x14 — the 32-byte window dumped was not large enough.**
This needs to be re-dumped with a bigger window (suggest 17 x 4 = 68+ bytes
from +0x0c onward) to find the full per-track pointer array, analogous to
ptr_A/ptr_B style arrays elsewhere in this format.

### Bone-index list (`ptr_A`, e.g. `0x222bd0` for clip 169)

Big-endian u16 array, ascending, NOT contiguous (skips values) — confirms
each clip animates only a SUBSET of the 68 skeleton bones:

```
clip 169: 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xc, 0xe, 0x10, 0x12, 0x14, 0x15, 0x16
        = Spine1, spine2, l_Clav, l_arm, l_forearm, l_hand, l_palm, l_pinky,
          l_pinky2, l_middle, l_index, l_thumb, l_prop, r_arm, r_hand,
          r_palm, r_pinky
```
(cross-referenced against the confirmed bone_index_map from eagl_skeleton.py
— coherent upper-body/arm animation, consistent with this being a small
gesture-type clip)

### Track data is POOLED/SHARED across clips — important structural finding

Enumerating EVERY relocation within clip 169's own byte span (1224 bytes,
`0x2242f4`-`0x2247bc`) shows only 6 relocs total, and several of their
TARGETS point to addresses BEFORE the clip's own start (e.g. `0x222bd0`,
`0x222c30`, `0x223b98` all sit in the byte range that "belongs" to the
PREVIOUS clip, clip 168, going by Array A's offsets). This means:

- Bone-index lists and/or track keyframe data are **shared/pooled** across
  multiple clips, not duplicated per-clip. A clip's header doesn't
  necessarily "own" all the data structures it references — some clips
  likely reuse another clip's track data wholesale (e.g. mirrored L/R
  animations, or idle-variant clips sharing a base track).
- This explains why Array B's per-clip secondary value didn't cleanly
  divide into clip byte size earlier — clip byte SIZE (from Array A deltas)
  measures one clip's own header+private region, not the full reachable
  data graph, since some of that graph lives in a neighboring clip's region.
- Practical implication for a parser: when extracting a clip's full data,
  walk relocations from the clip header rather than assuming
  `[arr1[i], arr1[i+1])` is a self-contained byte range. Some reloc targets
  will legitimately fall outside that range and must still be followed.

Within clip 169's own 1224-byte span, the only relocs found were:
```
+0x004 -> 0x222bd0   (bone-index list, OUTSIDE this clip's own range — shared)
+0x00c -> 0x222c30   (track record B, OUTSIDE this clip's own range — shared)
+0x010 -> 0x223b98   (track record C, OUTSIDE — shared)
+0x014 -> 0x224268   (track record D, INSIDE this clip's range — clip-local)
+0x050 -> 0x22431c   (track record E?, INSIDE — clip-local)
+0x054 -> 0x224328   (track record F?, INSIDE — clip-local)
+0x498 -> 0x09d724   (unknown, far away — possibly a shared global resource,
                       e.g. event/sound-marker table or a default-pose ref)
+0x49c -> 0x22431c   (same target as +0x050 — re-referenced)
```
So this clip has only ~4 genuinely distinct track records of its own
(D, E, F, and whatever +0x498 points to), with B and C borrowed from the
previous clip. The earlier count of "17 bones in the bone-index list" was
reading a SHARED list that may serve more than just this one clip — track
count per clip is likely smaller than 17, contradicting the earlier
provisional read. **Re-derive actual per-clip track count from clip-LOCAL
relocs only, not the full transitively-reachable bone list.**

### Per-track sub-record (header confirmed, payload NOT yet decoded)

Dumped 3 consecutive sub-records (ptr_B/C/D) from clip 169, all 32 bytes
shown, structure CONFIRMED consistent:

```
+0x00  u16 BE   bone_index        — CONFIRMED: matches skeleton bone indices
                                     EXACTLY (0x12=18=r_arm, 0x14=20=r_hand,
                                     0x15=21=r_palm — checked against
                                     eagl_skeleton.py's bone_index_map,
                                     perfect match, all 3 form a coherent
                                     right-arm chain)
+0x02  u16 BE   0xc6e4            — CONSTANT across every track record seen
                                     so far AND matches the clip header's
                                     +0x00 low halfword. Likely a magic/type
                                     tag for "animation track record."
+0x04  reloc OR u32 BE  variable  — sometimes a reloc back into the bone-
                                     index-list region (e.g. 0x1390e6,
                                     0x224260), sometimes not present as a
                                     reloc at all — inconsistent, needs more
                                     samples to characterize
+0x08  reloc -> 0x222bdc (SAME for all 3 tracks dumped) — shared pointer
                                     back near the start of the bone-index
                                     list. Possibly a "default pose" or
                                     "track count" cross-reference. Exact
                                     purpose unknown.
+0x0c  u32 BE / reloc, variable   — candidate keyframe-count field, varies
                                     per track (track B has a reloc here to
                                     0x222bfe; tracks C/D show plain values
                                     0x00120008 / 0x00120003 instead — the
                                     low byte 0x08 / 0x03 may be a real
                                     keyframe count, the 0x0012=18 prefix is
                                     unexplained, possibly itself a repeat
                                     of the bone index or unrelated)
+0x10 onward                      — NOT YET DECODED. This is presumably
                                     where actual keyframe data (rotation/
                                     position over time) begins. Raw bytes
                                     look high-entropy / not obviously
                                     float-shaped at a glance — may be
                                     compressed or quantized (e.g. s16
                                     quaternion components, consistent with
                                     the s16 position encoding already known
                                     from Layout D mesh parsing) rather than
                                     raw f32 keyframes. NOT YET TESTED.
```

### Track payload (`+0x10` onward) — partial progress, NOT solved

Dumped track D in full isolation (180 bytes total, clip-local, bone_index=18
=r_arm, confirmed via header). Findings:

- `+0x14` to `+0x28` (6 floats): small plausible values
  `(0.1389, 0.00075, 0.0034, 0.0165, 0.0028, 0.0002)` — NOT yet matched to
  any known transform component (too small/varied to obviously be a
  quaternion; could be per-keyframe deltas, or scale/bias coefficients for
  a quantized format below).
- `+0x2c = 1.0`, `+0x30 = 0.0072` — isolated floats, meaning unclear.
- **Distinctive repeating sentinel pattern found**: bytes
  `7F 7F 7F 80 80 80` (signed-byte equivalent `127,127,127,-128,-128,-128`,
  i.e. exact min/max clamp values for a signed byte) appear FOUR times in a
  row starting around `+0x3e`, each repetition preceded by a small
  4-6 byte header-ish run (e.g. `00 00 02 00 00 00 00`). This is almost
  certainly a structural marker (sub-track separator, "empty/default
  channel" sentinel, or similar) rather than real keyframe values — real
  animation data is unlikely to legitimately hit hard min/max clamps 4
  times in a row. NOT yet confirmed what it delimits.
- Track D's tail bytes are literally clip 169's own header repeated
  verbatim (`000fc6e4 d02b2200...`) — confirms track D's true end boundary
  is correct (`0x22431c`, matching the next track's start) since the next
  bytes immediately belong to a different, already-known structure.

**Conclusion: per-track keyframe payload encoding is NOT yet cracked.**
Promising next angle, not yet tried: compare the SAME bone's track across
MULTIPLE different clips of varying length — if track payload size scales
linearly with a clip's frame/duration count (visible in `player.csv`'s
implicit timing, or derivable from `ANIM_BLEND_TIME`/event timestamps),
that would confirm a keyframe-stream hypothesis and likely reveal the
per-keyframe stride by simple division. This is a more reliable path than
further single-track byte-archaeology.

**Linear-scaling hypothesis test result: REJECTED.** Tracked bone 18
(r_arm) across 6 clips of varying size (clip sizes 1224-79472 bytes) using
a global sorted index of all `0xc6e4`-tagged track headers in the file
(found by scanning every reloc target for the magic tag, not just
clip-local ones — this is a reusable technique, see snippet below). Track
size for the SAME bone varies independently of clip size (e.g. clip 10 is
tiny at 1596 bytes total but its bone-18 track alone is 10,252 bytes —
larger than the entire clip 0, which is 79,472 bytes). This makes sense in
hindsight: track size depends on how much THAT bone moves in THAT clip
(keyframe density), not overall clip duration. Rejecting this hypothesis
is still useful — it rules out a fixed-rate keyframe stream and supports
the format being genuinely sparse/event-driven per bone (consistent with
the per-clip bone-index list only including bones that bone actually
animates, which we already confirmed).

Reusable technique for finding ALL track headers file-wide (not just
clip-local ones), useful for the next session:
```python
all_track_starts = sorted(
    val for off, val in relocs.items()
    if data_start+val+4 <= len(data)
    and (struct.unpack('>I', data[data_start+val:data_start+val+4])[0] & 0xFFFF) == 0xc6e4
)
# track_size(start) = next track-start in this sorted list, minus start
```

### Outstanding items for `.anm` (next session, in priority order)

1. **Decode keyframe stride within a single isolated track.** Best
   candidate to start with: a track from a clip with VERY few keyframes
   expected (e.g. a short, simple clip) where the track itself is small
   enough to fully account for byte-by-byte. The `7F7F7F808080` sentinel
   pattern (4 repetitions seen in track D) likely delimits sub-channels —
   try assuming each repetition marks "rotation channel" vs "position
   channel" vs "scale channel" boundaries (3 channels x small header would
   roughly match 4 sentinel hits if one is a leading/trailing marker).
2. Once a stride is found, test it against the 6 small floats seen at
   track D's `+0x14..+0x28` — check if THAT span alone (using a refined
   start "+0x10" boundary) is itself a single keyframe (e.g. quaternion
   components quantized to fewer bytes, or a 6-float compressed rotation
   format) rather than searching the whole 180-byte track as one blob.
3. Re-derive actual per-clip track count from clip-LOCAL relocs only
   (technique demonstrated above with `find_tracks_in_clip`), and re-test
   whether `arr2[i]` (the clip-index secondary array) matches this
   clip-local track count — NOT YET RE-TESTED after the pooling discovery.
4. Investigate the `+0x498` reloc in clip 169 pointing to `0x09d724` — far
   outside any nearby clip's range, doesn't match the `0xc6e4` track-magic
   pattern when checked. Could be an event/sound-marker table, a shared
   default-pose fallback, or something else entirely. Low priority but
   flagged as unexplained.
5. Bind `.ske` (DONE) and `.anm` (in progress) together: once keyframe
   format is solved, validate by confirming decoded values land in
   plausible ranges relative to the corresponding bone's bind-pose
   quaternion/translation from `eagl_skeleton.py`.

### Per-track sub-record — header REFINED (8 bytes, not 16), payload still open

New finding this session: the fixed track header is only **8 bytes**, not
16. Established by diffing 8 different bone-20 (r_hand) tracks of identical
total size (108 bytes) from different clips, checking which byte positions
stay constant across all 8 samples:

```
+0x00-0x07   CONSTANT across all 8 tracks: bone_idx+0xc6e4 magic (4 bytes)
             + a second reloc'd pointer (4 bytes) that resolves to the SAME
             shared global address (0x23d0) in every sample — likely a
             common default-pose / fallback table (same suspected role as
             the unexplained clip-level +0x498 reloc noted earlier).
+0x08-0x0b   VARIES per track — reloc into that clip's own bone-index-list
             region (expected, since this is naturally clip-specific).
+0x0c-0x0d   VARIES — small values seen (0x000e, 0x000f) in the bone-20
             sample set. Meaning NOT CONFIRMED — possibly a linked-list
             style "other track" bone index, possibly unrelated.
+0x0e-0x0f   CONSTANT: 0x0001 across all 8 samples.
+0x10-0x11   CONSTANT: 0x0300 across all 8 samples — likely a real
             sub-header (format/channel-count tag?). NOT CONFIRMED.
+0x12-0x13   VARIES — 2 bytes, sits immediately before the float run below.
```

**Confirmed reusable float run**: starting at `+0x14` (corrected from the
prior session's `+0x10` guess — off by one 4-byte word), there is a clean
run of **6 big-endian f32 values**, small and plausible (e.g.
`0.0268, 0.2810, 0.0070, 0.0299, 0.2032, 0.0128`). Independently reproduced
in TWO separate tracks now (track D from the prior session, and this
session's bone-20/108-byte sample) at the same relative offset, same
"6 small floats then garbage" shape. High confidence this is real
structured data — leading hypotheses: (a) two 3-component vectors used as
quantization min/max or scale/bias for what follows, or (b) the first
components of an actual keyframe before the encoding changes/compresses.

**Byte-value analysis of the post-float-run tail** (`+0x2c` onward):
entropy ~4.9 bits/byte (vs 8.0 max random), with a strong non-uniform
spike at byte values `0x00` (11 of 60 bytes) and `0xFF` (7 of 60 bytes).
This clustering at numeric extremes is the signature of clamped/quantized
fixed-point data, not raw floats and not high-entropy compressed data.
Reinforces (without proving) a quantized-keyframe hypothesis, and echoes
the prior session's `7F7F7F808080` sentinel finding (also clamp-like,
different track).

**Tried and inconclusive this session:**
- Searched for periodic `0xFFFF` markers in the post-float-run tail —
  positions found do NOT form a clean fixed stride (diffs of 13, 19) —
  likely incidental, not a structural delimiter.
- Found two bone-20 tracks with byte-for-byte IDENTICAL full payloads
  (different clips) — confirms pooling/reuse happens at the individual
  TRACK level too, not just the clip's bone-index list. Didn't directly
  help crack the byte format but useful for a future dedup-aware exporter.

### Where to resume next session

Most promising unexplored angle: **treat the 6-float run as a literal
decode key** (e.g. per-axis quantization scale/bias) and try reconstructing
candidate quantized values from the bytes immediately following, using
those 6 floats as multipliers/offsets — check whether the result lands in
a sane rotation/position range. More targeted than further blind
stride-searching. Concretely:

1. Take the 6 floats as 2 groups of 3 (e.g. `scale_xyz` + `bias_xyz`, or
   `min_xyz` + `max_xyz`).
2. Read the next N bytes as u8/s8 quantized components, apply
   `value = byte/255 * scale + bias` (or `min + byte/255*(max-min)`), check
   whether 3-at-a-time groupings produce unit-length-ish vectors (normalized
   quaternion axis) or small bone-relative deltas (position offsets).
3. If u8/s8 doesn't fit, retry with u16/s16 pairs (halves candidate
   keyframe count, doubles per-component precision) — Layout D mesh
   parsing already established this engine's preference for s16
   quantization elsewhere, so it's a strong prior here too.
4. ~~Cheap, high-value check~~ **DONE (later session) — result: `+0x0c` is
   NOT a uniform fixed field.** Tested the quantization-decode idea (item
   1-3 above) first: neither u8 nor s16 decoding of the payload bytes using
   the 6-float run as scale/bias produced unit-magnitude or otherwise
   convincing vectors — that hypothesis is now considered weak (not
   disproven, but not supported either; deprioritize unless a better
   scale/bias source is found). Pivoted to checking `+0x0c` across many
   tracks instead:
   - Confirmed `+0x0c` is SOMETIMES a real reloc (pointer), sometimes a
     plain value — inconsistent across tracks of the same bone. When it IS
     a reloc, the target is a **single-BYTE bone-index list** (different
     encoding from `ptr_A`'s u16 list seen earlier!), immediately followed
     by another track's `bone_idx+0xc6e4` header and a small u16 value
     (e.g. `0x0036`=54).
   - When `+0x0c` is NOT a reloc, its hi16/lo16 split does NOT consistently
     equal the track's own bone index (only 6/127 sampled tracks matched),
     and values range wildly (10 to 600+) — too large and inconsistent to
     be a simple keyframe count or bone-index field on its own.
   - **Working theory (NOT confirmed): the fixed 8-byte header established
     earlier is likely followed by a VARIABLE-LENGTH section** (possibly
     itself another small bone-index/reference list, byte-encoded), not a
     uniform fixed-offset field — which would explain why every fixed-offset
     hypothesis tested so far (this session and prior) has been
     inconsistent across samples. This reframes the problem: rather than
     looking for fixed-offset fields, the next attempt should try to find
     a LENGTH or COUNT byte near the start of the variable section and use
     it to walk forward correctly per-track, the same way `+0x08/+0x0c`
     style relocations were chained in the clip-level header.
5. Re-derive actual per-clip track count from clip-LOCAL relocs only
   (technique already demonstrated via `find_tracks_in_clip` in the prior
   session), and re-test whether `arr2[i]` (the clip-index secondary array)
   matches this clip-local track count — still not re-tested after the
   pooling discovery.
6. Investigate the `+0x498` reloc in clip 169 pointing to `0x09d724` — far
   outside any nearby clip's range, doesn't match the `0xc6e4` track-magic
   pattern. Low priority, flagged as unexplained.
7. Bind `.ske` (DONE) and `.anm` (in progress) together once keyframe
   format is solved: validate decoded values against the corresponding
   bone's bind-pose quaternion/translation from `eagl_skeleton.py`.

Reusable technique for finding ALL track headers file-wide:
```python
all_track_starts = sorted(
    val for off, val in relocs.items()
    if data_start+val+4 <= len(data)
    and (struct.unpack('>I', data[data_start+val:data_start+val+4])[0] & 0xFFFF) == 0xc6e4
)
# track_size(start) = next track-start in this sorted list, minus start
```

## 3. Current Status Summary

**`.ske` — SOLVED, including correct local/world transform semantics.**
Working parser: `eagl_skeleton.py`. All 68 bones, correct parent hierarchy.
Ground truth per bone: `quaternion` (local rotation) + `unknown_vec` (local,
parent-relative translation, aliased as `local_translation`). World-space
pose is computed via forward kinematics (`BoneRecord.world_matrix` /
`world_translation` properties), NOT read directly from the stored `matrix`
or `translation` fields — those are a derived/cached world rotation and an
unreliable field respectively (see correction note in §1). Validated via
exact world-matrix recomposition match, zero anatomically-implausible bone
lengths, and left/right mirror symmetry to 4 decimal places.

**`.anm` — Clip index solved, track header REFINED (8-byte fixed header,
confirmed by cross-track diffing), keyframe payload still NOT solved.**
Confirmed: 265 clips, LE clip-offset/secondary arrays, BE clip headers using
real ELF relocations, per-track sub-records tagged with a
`bone_index + 0xc6e4` magic header, track data POOLED/shared across
neighboring clips AND across individual tracks (two byte-identical bone-20
tracks found in different clips). A clean run of 6 small f32 values
immediately follows the header at a now-confirmed fixed offset (`+0x14`)
in every sample checked — strong candidate for a quantization scale/bias
key. The keyframe stream itself (rotation/position over time) remains
unknown; byte-entropy analysis of the payload tail points toward
clamped/quantized fixed-point data rather than raw floats or compressed
high-entropy data. See "Where to resume next session" above for the
concrete next experiment (decode payload bytes using the 6-float run as a
scale/bias key).

## 4. Reusable Infrastructure Confirmed Working

- `parser.py`'s `_read_sections()`, `_read_cstr()`, `_build_reloc_map()` work
  unmodified against both `.ske` and `.anm` (same ELF container family).
- `_build_reloc_map()` correctly returns `{}` for `.ske` (no `.rel.data`) —
  don't treat that as an error condition, it's expected for this file type.
- Symbol-table-driven anchoring (the `__Bone:::`, `__Skeleton:::`,
  `__AnimationBank:::` convention) is exactly analogous to `__BBOX:::` /
  `__Model:::` already handled in `_extract_names()` / `_extract_bbox()` —
  a new `_extract_skeleton_anchor()` / `_extract_animbank_anchor()` helper
  can follow the same shape.
