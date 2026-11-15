-- Log every distinct ROM address read in the text areas (string tables, script regions), with the first PC.
-- Used with build.py --relocate-all: tools/debug/stale_reads.py flags reads that land in a vacated room, i.e. text
-- some code still reaches by its old address. Add to a warp run: warp_all.py ROM --probe tools/debug/romreads.lua
local ranges = {
  {0x08125E00, 0x0813FFFF},  -- string tables 1
  {0x08400000, 0x0846A103},  -- string tables 2 + main script region
  {0x086918E8, 0x08693977},  -- tutorial scripts
}
local seen = {}
for _, r in ipairs(ranges) do
  L.on_read(r[1], r[2], function(addr)
    if not seen[addr] then
      seen[addr] = true
      L.log(string.format("R %08X %08X f%d", addr, L.pc(), L.frame))
    end
  end)
end
