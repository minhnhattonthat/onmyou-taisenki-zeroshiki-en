-- Log RAM bytes at chosen frames (run beside warp.lua). See docs/re/debug.md.
--   emu.py ROM --out D --script tools/debug/warp.lua --script tools/debug/ramlog.lua --var "SCENE='menu_party'"
--     --var "AT='12000,13000'" --var "RANGES='0x02007BDC:2,0x0200273C:16'"
-- AT = frames to log at; RANGES = ADDR:LEN list. Each log line: RAM f<frame> <addr>: hex bytes.
local M = emu.memType.gbaMemory
local at = {}
for f in tostring(AT or ""):gmatch("%d+") do at[tonumber(f)] = true end
L.on_frame(function(f)
  if not at[f] then return end
  for a, n in (RANGES or ""):gmatch("(0x%x+):(%d+)") do
    local addr, t = tonumber(a), {}
    for i = 0, tonumber(n) - 1 do t[#t + 1] = string.format("%02X", emu.read(addr + i, M)) end
    L.log(string.format("RAM f%d %08X: %s", f, addr, table.concat(t, " ")))
  end
end)
