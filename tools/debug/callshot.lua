-- Shot of whatever a routine draws: on the first calls of PC (var PC, hex string, default 0x0803A168) logs
-- "CALLSHOT f<frame> lr=.. r0..r3=.. sp0..sp2=.." and takes a shot DELAY frames later (var DELAY, default 30).
--   python -X utf8 tools/debug/warp_all.py build/marker.gba --only intro_scroll --probe tools/debug/callshot.lua
local M = emu.memType.gbaMemory
local pc = tonumber(PC or "0803A168", 16)
local delay = tonumber(DELAY or "30")
local n, due = 0, {}
local function r32(a) return emu.read16(a, M) | (emu.read16(a + 2, M) << 16) end
L.on_exec(pc, pc, function()
  n = n + 1
  if n > 12 then return end
  local s = emu.getState()
  local sp = s["cpu.r13"]
  L.log(string.format("CALLSHOT f%d lr=%08X r0=%08X r1=%08X r2=%08X r3=%08X sp0=%08X sp1=%08X sp2=%08X", L.frame,
    s["cpu.r14"], s["cpu.r0"], s["cpu.r1"], s["cpu.r2"], s["cpu.r3"], r32(sp), r32(sp + 4), r32(sp + 8)))
  due[L.frame + delay] = true
end)
L.on_frame(function()
  if due[L.frame] then L.shot(string.format("callshot_f%d", L.frame)) end
end)
