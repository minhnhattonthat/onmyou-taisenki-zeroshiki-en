-- Who calls the OBJ-cell text renderer 0x08014098(str, tile index, size, flag, [sp] max), and with what?
-- (docs/re/font.md "Full renderer list"). One log line per distinct (lr, str):
--   python -X utf8 tools/debug/warp_all.py build/marker.gba --only battle_forest --out work/qa/oc --states work/qa/oc/st --probe tools/debug/objcalls.lua
-- "OBJ f<frame> lr=.. str=.. tile=.. size=.. flag=.. max=.. text=<first codes>"
local M = emu.memType.gbaMemory
local seen = {}
local function r32(a) return emu.read16(a, M) | (emu.read16(a + 2, M) << 16) end
L.on_exec(0x08014098, 0x08014098, function()
  local s = emu.getState()
  local str, lr = s["cpu.r0"], s["cpu.r14"]
  local key = string.format("%08X:%08X", lr, str)
  if seen[key] then return end
  seen[key] = true
  local codes = {}
  for i = 0, 15 do
    local b1 = emu.read(str + i * 2, M)
    if b1 == 0 then break end
    codes[#codes + 1] = string.format("%02X%02X", b1, emu.read(str + i * 2 + 1, M))
  end
  L.log(string.format("OBJ f%d lr=%08X str=%08X tile=%X size=%d flag=%d max=%d text=%s", L.frame, lr, str,
    s["cpu.r1"], s["cpu.r2"], s["cpu.r3"], r32(s["cpu.r13"]), table.concat(codes, " ")))
end)
