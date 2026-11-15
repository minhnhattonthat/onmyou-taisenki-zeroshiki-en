-- Who calls the map-line renderers 0x0803A168 / 0x08110BAC / 0x08110AE8(x, y, pal, map, [sp] dest, [sp+4] base, [sp+8] str)
-- and the 2-row battle caller 0x08110C88 (same args), with what x/y? One line per distinct (routine, lr, str, x):
--   python -X utf8 tools/debug/warp_all.py build/marker.gba --only battle_forest --out work/qa/lc --states work/qa/lc/st --probe tools/debug/linecalls.lua
-- "LINE f<frame> fn=.. lr=.. x=.. y=.. pal=.. map=.. dest=.. base=.. str=.. text=<first codes>"
local M = emu.memType.gbaMemory
local seen = {}
local function r32(a) return emu.read16(a, M) | (emu.read16(a + 2, M) << 16) end
local function hook(fn)
  L.on_exec(fn, fn, function()
    local s = emu.getState()
    local sp, lr = s["cpu.r13"], s["cpu.r14"]
    local str = r32(sp + 8)
    local key = string.format("%08X:%08X:%08X:%d", fn, lr, str, s["cpu.r0"])
    if seen[key] then return end
    seen[key] = true
    local codes = {}
    for i = 0, 15 do
      local b1 = emu.read(str + i * 2, M)
      if b1 == 0 then break end
      codes[#codes + 1] = string.format("%02X%02X", b1, emu.read(str + i * 2 + 1, M))
    end
    L.log(string.format("LINE f%d fn=%08X lr=%08X x=%d y=%d pal=%X map=%X dest=%X base=%X str=%08X text=%s",
      L.frame, fn, lr, s["cpu.r0"], s["cpu.r1"], s["cpu.r2"], s["cpu.r3"], r32(sp), r32(sp + 4), str,
      table.concat(codes, " ")))
  end)
end
hook(0x0803A168)
hook(0x08110BAC)
hook(0x08110C88)
hook(0x08110AE8) -- small font (type 12), one 8x8 tile per char at map column x + i: battle name tags
