-- Log every field graphics load 0x080089D4(index, vram slot): index into the pointer table 0x0858D190 (1170 LZ
-- blocks: indices 0..19 are the town tilesets with shop signs, graphics survey G11), with the current map id.
--   "TILESET f<frame> map=<0x02002E88> idx=<r0> lr=<caller>"
--   python -X utf8 tools/debug/warp_all.py build/onmyou_zeroshiki_en.gba --scenes S --probe tools/debug/tilesetlog.lua
local M = emu.memType.gbaMemory
local seen = {}
L.on_exec(0x080089D4, 0x080089D4, function()
  local s = emu.getState()
  local map = emu.read16(0x02002E88, M)
  local idx = s["cpu.r0"] & 0xFFFF
  local key = map * 65536 + idx
  if seen[key] then return end
  seen[key] = true
  L.log(string.format("TILESET f%d map=%d idx=%d lr=%08X", L.frame, map, idx, s["cpu.r14"]))
end)
