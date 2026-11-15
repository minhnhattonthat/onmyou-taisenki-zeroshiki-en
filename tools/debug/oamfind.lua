-- Which OAM entries show OBJ tiles in [TLO, THI] (default 0x3D8..0x3E8: the battle speaker name tag, tile 0x3DB
-- written by 0x08111B50)? Logs each distinct entry once: "OAM f<frame> i=.. x=.. y=.. shape=.. size=.. tile=.. pal=.."
--   python -X utf8 tools/debug/warp_all.py ROM --only battle_forest --out work/qa/oam --states work/qa/oam/st --probe tools/debug/oamfind.lua
local M = emu.memType.gbaMemory
local TLO, THI = rawget(_G, "TLO") or 0x3D8, rawget(_G, "THI") or 0x3E8  -- --var TLO=0x60 --var THI=0x80
local seen = {}
local frame = 0
L.on_frame(function()
  frame = frame + 1
  if frame % 30 ~= 0 then return end
  for i = 0, 127 do
    local a = 0x07000000 + i * 8
    local a0, a1, a2 = emu.read16(a, M), emu.read16(a + 2, M), emu.read16(a + 4, M)
    local tile = a2 & 0x3FF
    if tile >= TLO and tile <= THI and (a0 & 0x300) ~= 0x200 then
      local key = string.format("%d:%04X:%04X:%04X", i, a0, a1, a2)
      if not seen[key] then
        seen[key] = true
        L.log(string.format("OAM f%d i=%d x=%d y=%d shape=%d size=%d tile=%X pal=%d prio=%d", frame, i, a1 & 0x1FF,
          a0 & 0xFF, a0 >> 14, a1 >> 14, tile, a2 >> 12, (a2 >> 10) & 3))
      end
    end
  end
end)
