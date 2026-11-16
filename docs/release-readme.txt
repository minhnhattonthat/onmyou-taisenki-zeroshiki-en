Onmyou Taisenki Zeroshiki - English translation {version}
=========================================================

Unofficial English fan translation of Onmyou Taisenki Zeroshiki (Game Boy Advance, Bandai, 2005).
This zip holds only a patch. No game data is included: you need your own dump of the Japanese cartridge.
Do not share patched ROMs.

How to patch
------------
1. Get the Japanese ROM (No-Intro: "Onmyou Taisenki Zeroshiki (Japan)", AGB-BITJ). It must match:
     size   {base_size} bytes
     CRC32  {base_crc32}
     MD5    {base_md5}
     SHA-1  {base_sha1}
2. Apply {patch} with a BPS patcher: Rom Patcher JS (https://www.marcrobledo.com/RomPatcher.js/),
   Flips or beat.
3. The patched ROM should be:
     size   {new_size} bytes (it grows to 9 MiB: the English text and font code live past the original 8 MiB)
     CRC32  {new_crc32}
     SHA-1  {new_sha1}

Play it in any GBA emulator or on a flash cart. Tested in Mesen 2.2.1 (GBA core).
Start a NEW game: saves from the Japanese version can hold Japanese names and text, so start fresh.

What is translated
------------------
- Story, all event dialogue, NPCs, shikigami contract scenes, tutorial: English.
- Menus, items, skills, shikigami names and kinds, battle messages and quotes, save screen, area names: English.
- Graphics with text: the title logo, menu buttons, battle banners and plates, the Drive wheel, shop signs,
  super-move cut-in names: redrawn in English.
- Name entry: an English (ABC) tab next to the kana grid; the player's default name is Riku.
- Staff credits: English.
- Left in Japanese on purpose: the title screen's copyright notice, the kana sound effects drawn over battle
  hits, and the kana tab of the name-entry grid.

Known issues
------------
- The link-cable (two-player) menus are translated but were not tested with a second console.
- The speaker name plate can show the old and new names overlapped for a frame or two when the speaker changes.
- Report bugs at https://github.com/minhnhattonthat/onmyou-taisenki-zeroshiki-en/issues (a savestate helps).

Credits
-------
Translation, hacking and tools: minhnhattonthat, with extensive AI assistance (Claude by Anthropic, reviews by
OpenAI Codex). Corrections are very welcome.
Onmyou Taisenki Zeroshiki is (c) Bandai; the Onmyou Taisenki anime (c) its rights holders. This project is not
affiliated with them.
