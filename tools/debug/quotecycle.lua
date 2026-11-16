-- Text coverage for the shikigami battle quotes (str_quotes01..10): each time a battle asks the quote picker
-- 0x08104E70 for a line, hand it the next quote of the 10 tables instead, so every quote goes through the real
-- battle window renderer in turn. The picker selects table r5 (0..9: 0x0812BB50, 0x0812D00C, ... 0x08138FF4,
-- literals at 0x08104EDC..), entry r3 + 2*r4, and returns the pointer in r0 at 0x08104F3A (docs/re/text.md).
-- The tables are read from the running ROM, so a build that moved the quotes is followed.
--   warp_all.py ROM --only battle_forest --probe tools/debug/quotecycle.lua --probe <skill>/scripts/lua/probes/textcover.lua ...
--   START=table*1000+entry to resume part-way; logs "QC t i addr" per forced quote.
--   COUNT=n: force n quotes, then end the run 600 frames later (one slice per parallel job: tools/debug/quotejobs.py).
--   KEEP='0x02019938:290,0x02019944:208': u16 values re-poked every frame (player / enemy HP) so the battle never ends.
local M = emu.memType.gbaMemory
local keep = {}
for a, v in tostring(KEEP or ""):gmatch("(0x%x+):(%d+)") do keep[#keep + 1] = { tonumber(a), tonumber(v) } end
local forced, end_at = 0, nil
L.on_frame(function(f)
  for _, k in ipairs(keep) do emu.write16(k[1], k[2], M) end
  if end_at and f >= end_at then L.log("QC_END f" .. f); end_at = nil; L.finish(0) end
end)
local LITS = { 0x08104EDC, 0x08104EE4, 0x08104EEC, 0x08104EF4, 0x08104EFC, 0x08104F04, 0x08104F0C, 0x08104F14,
  0x08104F1C, 0x08104F34 }
local N = PER_TABLE or 158
local t, i = 0, 0
if START then t, i = START // 1000, START % 1000 end
-- LIST='3068,0124': only these quotes (table*1000+entry), each forced twice (logs end with QC_END)
local list
if LIST then
  list = {}
  for n in tostring(LIST):gmatch("%d+") do list[#list + 1] = tonumber(n) end
  t, i = list[1] // 1000, list[1] % 1000
end
local done = false
L.on_exec(0x08104F3A, 0x08104F3A, function()
  if done then return end
  local s = emu.getState()
  if s["cpu.r0"] == 0 then return end
  local tab = emu.read32(LITS[t + 1], M)
  local p = emu.read32(tab + 4 * i, M)
  L.log(string.format("QC %d %d %08X f%d", t, i, p, L.frame))
  if p >= 0x08000000 and p < 0x0A000000 then emu.setState({ ["cpu.r0"] = p }) end
  forced = forced + 1
  if list then
    -- each listed quote is forced twice: the picker's result is sometimes not drawn
    local n = list[(forced // 2) + 1]
    if not n then done = true; end_at = L.frame + 600; return end
    t, i = n // 1000, n % 1000
    return
  end
  i = i + 1
  if i >= N then t, i = t + 1, 0 end
  if COUNT and forced >= COUNT then done = true; end_at = L.frame + 600 end
  if t >= #LITS then done = true; L.log("QC_DONE f" .. L.frame) end
end)
