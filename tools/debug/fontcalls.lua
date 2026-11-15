-- Every call site that looks up a 16x16 font glyph: resource lookup 0x080059A0(type, code) with type 13 (font).
-- Renderers that copy whole glyph tiles by BIOS CpuSet (intro scroll, credits) don't show in glyphreads.lua's
-- reader pcs, but they all look the glyph up here first. One line per distinct caller (lr):
--   "FONTCALL f<frame> lr=<caller> code=<sjis> sp0=<[sp]> r4..r7=<..>"
--   python -X utf8 tools/debug/warp_all.py build/marker.gba --probe tools/debug/fontcalls.lua --out work/qa/fcalls
-- --var "FONTTYPE=12" logs the small 8x8 font instead (any resource type works).
local M = emu.memType.gbaMemory
local want = tonumber(FONTTYPE or 13)
local seen = {}
L.on_exec(0x080059A0, 0x080059A0, function()
  local s = emu.getState()
  if s["cpu.r0"] ~= want then return end
  local lr = s["cpu.r14"]
  if seen[lr] then return end
  seen[lr] = true
  L.log(string.format("FONTCALL t%d f%d lr=%08X code=%04X r2=%08X r3=%08X r4=%08X r5=%08X r6=%08X r7=%08X", want, L.frame, lr,
    s["cpu.r1"] & 0xFFFF, s["cpu.r2"], s["cpu.r3"], s["cpu.r4"], s["cpu.r5"], s["cpu.r6"], s["cpu.r7"]))
end)
