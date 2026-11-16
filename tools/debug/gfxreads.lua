-- Who reads a graphics region (graphics survey rows G5/G7/G8): log the first read of each 0x200-byte block of
-- [LO, HI) with the PC and frame, and take a shot a few frames after each new block so the screen shows what uses it.
--   emu.py ROM --state-in work/states/battle_forest.mss --frames 6000 --mash 40 --script tools/debug/gfxreads.lua
--          --var LO=0x0822E3F4 --var HI=0x082563F4
local lo, hi = LO or 0x0822E3F4, HI or 0x082563F4
local seen, pend = {}, {}
L.on_read(lo, hi - 1, function(addr)
  local b = (addr - lo) // 0x200
  if not seen[b] then
    seen[b] = true
    L.log(string.format("GR %08X blk %d pc %08X f%d", addr, b, L.pc(), L.frame))
    pend[#pend + 1] = L.frame + 4
  end
end)
L.on_frame(function(f)
  for i = #pend, 1, -1 do
    if pend[i] == f then
      L.shot(string.format("gr_%06d.png", f))
      table.remove(pend, i)
    end
  end
end)
