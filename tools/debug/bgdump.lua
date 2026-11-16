-- BG tilemap dump around a screen rectangle once an OBJ tile shows (default: the dialogue speaker plate, OBJ tile
-- 0x68): logs DISPCNT, each BGnCNT and the map entries of tile rows R0..R1, cols C0..C1 for every enabled BG (map
-- entries as tile:pal:hflip:vflip). Then shot + stop.
--   python -X utf8 tools/debug/warp_all.py build/onmyou_zeroshiki_en.gba --only intro_event --out work/qa/bgd --probe tools/debug/bgdump.lua
-- Vars: TILE=0x68 R0=11 R1=15 C0=0 C1=10 DELAY=20
local M = emu.memType.gbaMemory
local TILE = tonumber(rawget(_G, "TILE") or 0x68)
local R0, R1 = tonumber(rawget(_G, "R0") or 11), tonumber(rawget(_G, "R1") or 15)
local C0, C1 = tonumber(rawget(_G, "C0") or 0), tonumber(rawget(_G, "C1") or 10)
local DELAY = tonumber(rawget(_G, "DELAY") or 20)
local due
L.on_frame(function()
  if not due then
    if AT and L.frame < AT then return end  -- AT=3600: only a showing from that frame on
    for i = 0, 127 do
      local a = 0x07000000 + i * 8
      if (emu.read16(a + 4, M) & 0x3FF) == TILE and (emu.read16(a, M) & 0x300) ~= 0x200 then
        due = L.frame + DELAY
        break
      end
    end
    return
  end
  if L.frame ~= due then return end
  local disp = emu.read16(0x04000000, M)
  L.log(string.format("BGDUMP f%d DISPCNT=%04X", L.frame, disp))
  for bg = 0, 3 do
    local cnt = emu.read16(0x04000008 + bg * 2, M)
    local sbb, cbb = (cnt >> 8) & 31, (cnt >> 2) & 3
    L.log(string.format("BG%d on=%d CNT=%04X prio=%d cbb=%d sbb=%d size=%d map=%08X", bg, (disp >> (8 + bg)) & 1,
      cnt, cnt & 3, cbb, sbb, cnt >> 14, 0x06000000 + sbb * 0x800))
    if (disp >> (8 + bg)) & 1 == 1 then
      for r = R0, R1 do
        local row = {}
        for c = C0, C1 do
          local e = emu.read16(0x06000000 + sbb * 0x800 + (r * 32 + c) * 2, M)
          row[#row + 1] = string.format("%03X:%X%s", e & 0x3FF, e >> 12, ((e >> 10) & 3) ~= 0 and "f" .. ((e >> 10) & 3) or "")
        end
        L.log(string.format("  r%02d %s", r, table.concat(row, " ")))
      end
    end
  end
  local v = {}
  for a = 0x06000000, 0x06017FFF, 2 do
    local w = emu.read16(a, M)
    v[#v + 1] = string.char(w & 0xFF, w >> 8)
  end
  L.write_file("bgdump_vram.bin", table.concat(v))
  local p = {}
  for a = 0x05000000, 0x050003FF, 2 do
    local w = emu.read16(a, M)
    p[#p + 1] = string.char(w & 0xFF, w >> 8)
  end
  L.write_file("bgdump_pal.bin", table.concat(p))
  L.shot("bgdump.png")
end)
