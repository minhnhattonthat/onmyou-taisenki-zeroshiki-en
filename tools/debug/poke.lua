-- Generic u16 poke for emu.py runs from a savestate (warp.lua scenes have their own poke=):
--   --script tools/debug/poke.lua --var "POKE='02019944:0001'" --var AT=300 --var FOR=1
-- writes each ADDR:VAL (hex, comma-separated) from frame AT (default 1) for FOR frames (default 1).
-- e.g. enemy HP 0x02019944 = 1 so the next hit wins the battle (battle win banner / results).
-- CAP=1: write only while the current value is above VAL (player HP 0x02019938 capped at 1 from a state taken
-- before the battle: the first enemy hit then loses it).
local M = emu.memType.gbaMemory
local at, n = tonumber(AT or "1"), tonumber(FOR or "1")
local list = {}
for a, v in (POKE or ""):gmatch("(%x+):(%x+)") do list[#list + 1] = { tonumber(a, 16), tonumber(v, 16) } end
L.on_frame(function()
  if L.frame < at or L.frame >= at + n then return end
  for _, p in ipairs(list) do
    if not CAP or emu.read16(p[1], M) > p[2] then emu.write16(p[1], p[2], M) end
  end
  if L.frame == at then L.log("POKE f" .. L.frame) end
end)
