-- Are OBJ tiles TLO..THI (default 0x3C0..0x3DA, just below the battle name tag) ever non-blank? Every 15 frames
-- each tile in the range is read from VRAM (0x06010000 + tile * 32, catches DMA too); logs the first frame each
-- tile holds pixels, and once at the end a summary. Use it to prove tiles free before an engine patch takes them:
--   python -X utf8 tools/debug/warp_all.py ROM --only battle_forest,battle_win --out work/qa/vf --states work/qa/vf/st --probe tools/debug/vramfree.lua
-- Log: "VRAMUSE f<frame> tile=<hex>" per newly used tile, "VRAMFREE f<frame> never used: <ranges>" every 600 frames.
local M = emu.memType.gbaMemory
local TLO = tonumber(rawget(_G, "TLO") or 0x3C0)
local THI = tonumber(rawget(_G, "THI") or 0x3DA)
local used = {}
local frame = 0
L.on_frame(function()
  frame = frame + 1
  if frame % 15 ~= 0 then return end
  for t = TLO, THI do
    if not used[t] then
      local a = 0x06010000 + t * 32
      for o = 0, 30, 2 do
        if emu.read16(a + o, M) ~= 0 then
          used[t] = frame
          L.log(string.format("VRAMUSE f%d tile=%X", frame, t))
          break
        end
      end
    end
  end
  if frame % 600 == 0 then
    local out, s = {}, nil
    for t = TLO, THI + 1 do
      local free = t <= THI and not used[t]
      if free and not s then s = t end
      if not free and s then out[#out + 1] = string.format("%X..%X", s, t - 1); s = nil end
    end
    L.log(string.format("VRAMFREE f%d never used: %s", frame, table.concat(out, " ")))
  end
end)
