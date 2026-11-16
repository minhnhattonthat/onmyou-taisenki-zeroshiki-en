-- Full OAM dump (every visible entry with the OBJ tile range it covers, 1D mapping) each time OBJ tile TILE
-- (default 0x3DB, the battle speaker name tag) is on screen, at most N times (default 3), DELAY frames apart.
-- Finds free OBJ tiles for widening a sprite:
--   python -X utf8 tools/debug/warp_all.py ROM --only battle_forest --out work/qa/oa --states work/qa/oa/st --probe tools/debug/oamall.lua
-- Log: "OAMALL f<frame> i=.. x=.. y=.. WxH tile=A..B pal=.." then "OAMUSED <sorted merged tile ranges>".
local M = emu.memType.gbaMemory
local TILE = tonumber(rawget(_G, "TILE") or 0x3DB)
local N = tonumber(rawget(_G, "N") or 3)
local DELAY = tonumber(rawget(_G, "DELAY") or 120)
local DIMS = { [0] = { {8, 8}, {16, 16}, {32, 32}, {64, 64} }, { {16, 8}, {32, 8}, {32, 16}, {64, 32} },
  { {8, 16}, {8, 32}, {16, 32}, {32, 64} } }
local done, last = 0, -100000
local frame = 0
L.on_frame(function()
  frame = frame + 1
  if done >= N or frame - last < DELAY then return end
  local hit = false
  for i = 0, 127 do
    local a = 0x07000000 + i * 8
    if (emu.read16(a, M) & 0x300) ~= 0x200 and (emu.read16(a + 4, M) & 0x3FF) == TILE then hit = true end
  end
  if not hit then return end
  done, last = done + 1, frame
  local used = {}
  for i = 0, 127 do
    local a = 0x07000000 + i * 8
    local a0, a1, a2 = emu.read16(a, M), emu.read16(a + 2, M), emu.read16(a + 4, M)
    if (a0 & 0x300) ~= 0x200 and (a0 >> 14) < 3 then
      local d = DIMS[a0 >> 14][(a1 >> 14) + 1]
      local n = (d[1] // 8) * (d[2] // 8)
      if (a0 & 0x2000) ~= 0 then n = n * 2 end -- 8bpp: two tile slots each
      local t = a2 & 0x3FF
      L.log(string.format("OAMALL f%d i=%d x=%d y=%d %dx%d tile=%X..%X pal=%d prio=%d", frame, i, a1 & 0x1FF,
        a0 & 0xFF, d[1], d[2], t, t + n - 1, a2 >> 12, (a2 >> 10) & 3))
      used[#used + 1] = { t, t + n - 1 }
    end
  end
  table.sort(used, function(p, q) return p[1] < q[1] end)
  local merged, out = {}, {}
  for _, r in ipairs(used) do
    local m = merged[#merged]
    if m and r[1] <= m[2] + 1 then m[2] = math.max(m[2], r[2]) else merged[#merged + 1] = { r[1], r[2] } end
  end
  for _, r in ipairs(merged) do out[#out + 1] = string.format("%X..%X", r[1], r[2]) end
  L.log(string.format("OAMUSED f%d %s", frame, table.concat(out, " ")))
end)
