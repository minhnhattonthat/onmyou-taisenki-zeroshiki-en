-- Who reads a ROM range [LO, HI): log the first read per 0x40-byte block with PC and LR, and shoot 4 frames later.
-- For data copied by a shared routine (e.g. 0x08006EC8), LR names the caller that chose the source.
--   emu.py ROM --state-in work/states/X.mss --frames 6000 --mash 40 --script tools/debug/mapreads.lua
--          --var LO=0x0819E0BC --var HI=0x0819E530
local lo, hi = LO or 0x0819E0BC, HI or 0x0819E530
local seen, pend = {}, {}
L.on_read(lo, hi - 1, function(addr)
  local b = (addr - lo) // 0x40
  if not seen[b] then
    seen[b] = true
    local s = emu.getState()
    L.log(string.format("MR %08X blk %d pc %08X lr %08X f%d", addr, b, L.pc(), s["cpu.r14"] or -1, L.frame))
    pend[#pend + 1] = L.frame + 4
  end
end)
L.on_frame(function(f)
  for i = #pend, 1, -1 do
    if pend[i] == f then
      L.shot(string.format("mr_%06d.png", f))
      table.remove(pend, i)
    end
  end
end)
