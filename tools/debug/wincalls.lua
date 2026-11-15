-- Who calls the window glyph routine 0x080029F0(flag, win), and with what? (docs/re/font.md "Renderer catalogue")
-- Logs the first calls per (caller lr, win struct): "WIN f<frame> lr=.. win=.. n=.. str=.. code=.. x=.. y=.. base=..".
--   python -X utf8 tools/debug/warp_all.py build/marker.gba --only intro_scroll --probe tools/debug/wincalls.lua
-- LIMIT calls are logged per key (default 40), so a line's n/x sequence shows whether the window VWF sees it as
-- sequential (n = last n + 1, same string).
local M = emu.memType.gbaMemory
local LIMIT = 40
local count = {}
local function r32(a) return emu.read16(a, M) | (emu.read16(a + 2, M) << 16) end
L.on_exec(0x080029F0, 0x080029F0, function()
  local s = emu.getState()
  local win, lr = s["cpu.r1"], s["cpu.r14"]
  local key = string.format("%08X:%08X", lr, win)
  count[key] = (count[key] or 0) + 1
  if count[key] > LIMIT then return end
  local np = r32(win + 0x20)
  local n = r32(np)
  local str = r32(win + 0x1C)
  local hw = emu.read16(str + n * 2, M)
  L.log(string.format("WIN f%d lr=%08X win=%08X np=%08X n=%d str=%08X code=%04X x=%d y=%d base=%d,%d flag=%d",
    L.frame, lr, win, np, n, str, ((hw & 0xFF) << 8) | (hw >> 8), emu.read16(win + 4, M), emu.read16(win + 6, M),
    emu.read16(win + 0x12, M), emu.read16(win + 0x14, M), s["cpu.r0"]))
end)
