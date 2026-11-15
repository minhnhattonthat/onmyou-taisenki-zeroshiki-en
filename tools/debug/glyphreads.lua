-- Which code draws text? Logs each distinct (pc, lr) that reads font glyph data, per scene, so every renderer
-- (dialogue, name tag, menus, battle, credits...) can be listed with its plotter and caller.
--   python -X utf8 tools/debug/warp_all.py build/marker.gba --probe tools/debug/glyphreads.lua --out work/qa/glyphs
-- Log lines: "GLYPH f<frame> font=<big|small> pc=<reader> lr=<r14> r0..r3=<args at the read>".
-- Ranges: big 16x16 font 0x1B4E74..0x2247F3, small font 0x1B12D4..0x1B4E73 (docs/re/font.md).
local seen = {}
local function hit(which)
  return function(addr)
    local s = emu.getState()
    local pc, lr = L.pc(), s["cpu.r14"]
    local key = which .. pc .. ":" .. lr
    if seen[key] then return end
    seen[key] = true
    L.log(string.format("GLYPH f%d font=%s pc=%08X lr=%08X addr=%08X r0=%08X r1=%08X r2=%08X r3=%08X", L.frame,
      which, pc, lr, addr, s["cpu.r0"], s["cpu.r1"], s["cpu.r2"], s["cpu.r3"]))
  end
end
L.on_read(0x081B4E74, 0x082247F3, hit("big"))
L.on_read(0x081B12D4, 0x081B4E73, hit("small"))
