-- Who opens a text window through 0x08003614(r0, r1, r2 = win struct), and where (x, y)? Finds the code that
-- positions a window, e.g. the battle speaker name tag that is centred by character count (docs/re/font.md).
--   python -X utf8 tools/debug/warp_all.py build/marker.gba --only battle_forest --probe tools/debug/winopen.lua
-- Logs "OPEN f<frame> lr=.. r0=.. r1=.. win=.. x=.. y=.. str=.. text=<first halfwords>" once per (lr, str, x, y).
local M = emu.memType.gbaMemory
local seen = {}
local function r32(a) return emu.read16(a, M) | (emu.read16(a + 2, M) << 16) end
L.on_exec(0x08003614, 0x08003614, function()
  local s = emu.getState()
  local win = s["cpu.r2"]
  local str = r32(win + 0x1C)
  local key = string.format("%08X:%08X:%d:%d", s["cpu.r14"], str, emu.read16(win + 4, M), emu.read16(win + 6, M))
  if seen[key] then return end
  seen[key] = true
  local codes = {}
  for i = 0, 11 do
    local hw = emu.read16(str + i * 2, M)
    if hw == 0 then break end
    codes[#codes + 1] = string.format("%04X", ((hw & 0xFF) << 8) | (hw >> 8))
  end
  L.log(string.format("OPEN f%d lr=%08X r0=%X r1=%X win=%08X x=%d y=%d w=%d str=%08X text=%s",
    L.frame, s["cpu.r14"], s["cpu.r0"], s["cpu.r1"], win, emu.read16(win + 4, M), emu.read16(win + 6, M),
    emu.read16(win + 0xE, M), str, table.concat(codes, " ")))
end)
