-- Does the game ever touch the EWRAM the English engine keeps for itself (0x0203FF00..0x0203FFFF, vwf.py state)?
-- Logs one line per distinct PC that reads or writes there: "EWRAM_TOUCH f<frame> <r|w> pc=... addr=...".
--   python -X utf8 tools/debug/warp_all.py rom/<orig>.gba --probe tools/debug/ewram_watch.lua --out work/qa/ewram
-- Run it on the ORIGINAL ROM (no VWF code): any hit means the game uses that RAM and the VWF state must move.
-- warp.lua's own bytecode lives at 0x0203F000.. (below this range).
local lo, hi = 0x0203FF00, 0x0203FFFF
local seen = {}
local function hit(kind)
  return function(addr)
    local pc, lr = L.pc(), emu.getState()["cpu.r14"]
    local late = L.frame > 400  -- boot clears EWRAM before ~f300; anything later is real use
    local key = kind .. pc .. ":" .. lr .. tostring(late)
    if seen[key] then return end
    seen[key] = true
    L.log(string.format("EWRAM_TOUCH f%d %s %s pc=%08X lr=%08X addr=%08X", L.frame, late and "LATE" or "boot", kind,
      pc, lr, addr or 0))
  end
end
L.on_write(lo, hi, hit("w"))
L.on_read(lo, hi, hit("r"))
