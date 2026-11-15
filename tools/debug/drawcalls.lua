-- Which renderer draws which string: one line per distinct (routine, caller, string pointer), with the string's
-- first bytes, so tools/windows.py can map every table string / script run to its box variant.
--   python -X utf8 tools/debug/warp_all.py build/marker.gba --probe tools/debug/drawcalls.lua --out work/qa/dc
--   python -X utf8 tools/windows.py map work/qa/dc build/marker.gba
-- "DRAW f<frame> fn=<routine> lr=<caller> str=<ptr> a=<extra arg> hex=<first 64 bytes>"
local M = emu.memType.gbaMemory
local seen = {}
local function r32(a) return emu.read16(a, M) | (emu.read16(a + 2, M) << 16) end
local function dump(p)
  local t = {}
  for i = 0, 63 do
    local b = emu.read(p + i, M)
    t[#t + 1] = string.format("%02X", b)
    if b == 0 and i % 2 == 0 and emu.read(p + i + 1, M) == 0 then break end
  end
  return table.concat(t)
end
-- routine -> function(state) returning (string pointer, extra arg)
local SPEC = {
  [0x080029F0] = function(s) return r32(s["cpu.r1"] + 0x1C), s["cpu.r1"] end,       -- window glyph (struct)
  [0x080144F4] = function(s) return s["cpu.r0"], s["cpu.r1"] end,                     -- padded string drawer
  [0x080235D4] = function(s) return s["cpu.r0"], 0 end,                               -- intro strip
  [0x08023E3C] = function(s) return s["cpu.r0"], 0 end,                               -- credits strip
  [0x0803A168] = function(s) return r32(s["cpu.r13"] + 8), s["cpu.r0"] end,           -- map line (x)
  [0x08110BAC] = function(s) return r32(s["cpu.r13"] + 8), s["cpu.r0"] end,           -- battle map line
  [0x08110C88] = function(s) return r32(s["cpu.r13"] + 8), s["cpu.r0"] end,           -- battle 2-row
  [0x08110AE8] = function(s) return r32(s["cpu.r13"] + 8), s["cpu.r0"] end,           -- small-font BG label
  [0x08014098] = function(s) return s["cpu.r0"], s["cpu.r2"] end,                     -- OBJ cells (size)
  [0x08111B50] = function(s) return s["cpu.r1"], s["cpu.r0"] end,                     -- small-font name tag
}
for fn, get in pairs(SPEC) do
  L.on_exec(fn, fn, function()
    local s = emu.getState()
    local p, a = get(s)
    local lr = s["cpu.r14"]
    local key = string.format("%08X:%08X:%08X", fn, lr, p)
    if seen[key] then return end
    seen[key] = true
    local hx = ""
    if (p >= 0x02000000 and p < 0x02040000) or (p >= 0x03000000 and p < 0x03008000) or
       (p >= 0x08000000 and p < 0x0A000000) then hx = dump(p) end
    L.log(string.format("DRAW f%d fn=%08X lr=%08X str=%08X a=%X hex=%s", L.frame, fn, lr, p, a, hx))
  end)
end
