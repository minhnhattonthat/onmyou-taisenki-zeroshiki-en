-- Text coverage for the shikigami battle quotes (str_quotes01..10): each time a battle asks the quote picker
-- 0x08104E70 for a line, hand it the next quote of the 10 tables instead, so every quote goes through the real
-- battle window renderer in turn. The picker selects table r5 (0..9: 0x0812BB50, 0x0812D00C, ... 0x08138FF4,
-- literals at 0x08104EDC..), entry r3 + 2*r4, and returns the pointer in r0 at 0x08104F3A (docs/re/text.md).
-- The tables are read from the running ROM, so a build that moved the quotes is followed.
--   warp_all.py ROM --only battle_forest --probe tools/debug/quotecycle.lua --probe <skill>/scripts/lua/probes/textcover.lua ...
--   START=table*1000+entry to resume part-way; logs "QC t i addr" per forced quote.
local M = emu.memType.gbaMemory
local LITS = { 0x08104EDC, 0x08104EE4, 0x08104EEC, 0x08104EF4, 0x08104EFC, 0x08104F04, 0x08104F0C, 0x08104F14,
  0x08104F1C, 0x08104F34 }
local N = PER_TABLE or 158
local t, i = 0, 0
if START then t, i = START // 1000, START % 1000 end
local done = false
L.on_exec(0x08104F3A, 0x08104F3A, function()
  if done then return end
  local s = emu.getState()
  if s["cpu.r0"] == 0 then return end
  local tab = emu.read32(LITS[t + 1], M)
  local p = emu.read32(tab + 4 * i, M)
  L.log(string.format("QC %d %d %08X f%d", t, i, p, L.frame))
  if p >= 0x08000000 and p < 0x0A000000 then emu.setState({ ["cpu.r0"] = p }) end
  i = i + 1
  if i >= N then t, i = t + 1, 0 end
  if t >= #LITS then done = true; L.log("QC_DONE f" .. L.frame) end
end)
