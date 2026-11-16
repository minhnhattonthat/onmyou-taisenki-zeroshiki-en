-- Who writes VALUE to WATCH_LO..WATCH_HI? Unlike the skill's watch.lua (first hit per PC only) this logs every
-- matching write (up to MAX), with lr and r0..r3, so a late write by a PC already seen at boot still shows.
--   put the vars in a small .lua and pass it first:  WATCH_LO=0x0600034A WATCH_HI=0x0600034B VALUE=0x8141
--   python -X utf8 tools/debug/warp_all.py ROM --only intro_event --out work/qa/vw --probe vars.lua --probe tools/debug/valwatch.lua
-- VALUE nil = any value. BIOS PCs (CpuSet 0xB84.., LZ77 0x11E4..) mean a DMA-less copy: see lr / r0 for the source.
local lo = assert(WATCH_LO, "set WATCH_LO")
local hi, want, max = WATCH_HI or lo, VALUE, MAX or 40
local n = 0
L.on_write(lo, hi, function(addr, value)
  if want and value ~= want then return end
  if FROM and L.frame < FROM then return end  -- FROM=3200: ignore writes before that frame
  n = n + 1
  if n > max then return end
  local s = emu.getState()
  L.log(string.format("VW f%d pc=%08X lr=%08X addr=%08X val=%s r0=%08X r1=%08X r2=%08X r3=%08X r4=%08X r5=%08X r6=%08X r7=%08X",
    L.frame, L.pc(), s["cpu.r14"], addr or 0, tostring(value), s["cpu.r0"], s["cpu.r1"], s["cpu.r2"], s["cpu.r3"],
    s["cpu.r4"], s["cpu.r5"], s["cpu.r6"], s["cpu.r7"]))
end)
