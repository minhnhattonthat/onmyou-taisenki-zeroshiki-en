-- Tile destinations of the map-line renderers (x, y, pal, map, [sp] dest, [sp+4] base, [sp+8] str): 0x0803A168
-- (big font), 0x0803A0A4 / 0x08110AE8 (small font), 0x0803A178 (name-entry grid thunk), 0x08110BAC (battle).
-- One line per distinct (routine, caller, dest), with the first bytes of the string, so overlapping fields show up.
--   python -X utf8 tools/debug/warp_all.py build/qa.gba --only name_entry --out work/qa/mc --states work/qa/mc/st --probe tools/debug/mapcalls.lua
-- "MAP fn=.. lr=.. x=.. y=.. dest=.. base=.. str=.. hex=.."
local M = emu.memType.gbaMemory
local seen = {}
local function r32(a) return emu.read16(a, M) | (emu.read16(a + 2, M) << 16) end
for _, fn in ipairs({0x0803A168, 0x0803A0A4, 0x08110AE8, 0x0803A178, 0x08110BAC}) do
  L.on_exec(fn, fn, function()
    local s = emu.getState()
    local sp = s["cpu.r13"]
    local dest, str = r32(sp), r32(sp + 8)
    local key = string.format("%08X:%08X:%08X", fn, s["cpu.r14"], dest)
    if seen[key] then return end
    seen[key] = true
    local t = {}
    for i = 0, 15 do t[#t + 1] = string.format("%02X", emu.read(str + i, M)) end
    L.log(string.format("MAP fn=%08X lr=%08X x=%d y=%d dest=%08X base=%08X str=%08X hex=%s", fn, s["cpu.r14"],
      s["cpu.r0"], s["cpu.r1"], dest, r32(sp + 4), str, table.concat(t)))
  end)
end
