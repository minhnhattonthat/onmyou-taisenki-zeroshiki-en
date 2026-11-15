# ROM map, compression, free space

| Range | Contents | State |
|---|---|---|
| 0x000000..0x11FFFF | Thumb code + data (text interpreter 0x0802A000..0x0802E000) | verified (traced) |
| 0x120000..0x13FFFF | string tables (`text.md`) | verified |
| 0x140000..0x1B12D4 | raw graphics / data | sweep |
| 0x1B12D4..0x25F954 | asset files from the file table at 0x4028EC (57 × (ptr, size)); font inside | verified (table) |
| 0x25F954..0x3BFFFF | LZ77 blocks (portraits, sprites, BGs) | verified (lzscan) |
| 0x3E1254..0x3F3900 | resource index tables (0x403DA4 lists (index, data) pairs per resource type) | verified for type 13 |
| 0x400000..0x41FE58 | string tables, script helpers | verified |
| 0x41FE58..0x46B000 | event scripts (`text.md`) | verified |
| 0x470000..0x4D0000 | raw tile data | sweep |
| 0x4D0000..0x6F1600 | LZ77 blocks (backgrounds, maps), tutorial scripts 0x6930A4.., music ~0x693B00..0x6F0000 | verified (lzscan, watch) |
| 0x6F1600 | `EEPROM_V124` | verified |
| **0x6F1938..0x7FFFFF** | **0xFF fill, 1.06 MiB** | free-space candidate |

- **Save type: EEPROM** (`EEPROM_V124`): stay ≤16 MiB; BPS or IPS both work. Space past 8 MiB up to 16 MiB is free
  (the cart maps 32 MiB; check EEPROM access still works if the ROM grows past 16 MiB — don't).
- **The 0xFF tail is a candidate, not proven free**: before using it, fill it with a trap value and tour (phase 3/5).
  Growing the ROM to 16 MiB and putting new text at 0x800000+ avoids the question.
- **Compression:** GBA BIOS LZ77 (type 0x10) only found so far. `tools/lzscan.py` finds 1,815 chained blocks in
  0x140000..0x6F2000 (2.6 MB → 9.5 MB). Only 82 are reached by direct u32 pointers; the rest go through resource
  tables. No Huffman (0x20) or RLE (0x30) seen. Recompressor: needed only for edited graphics (phase 8).
- Text is **uncompressed**: scripts and strings can be relocated to free space and repointed.
