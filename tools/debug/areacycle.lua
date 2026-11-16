-- Text coverage for the area names (str_areas): the map menu draws the area name with the padded drawer
-- 0x080144F4, called at 0x080163F6 with r0 = word [0x0840B334 + 4 * area] (224 words; area from the cursor's map
-- point). Each time it runs, hand it the next distinct pointer of that table instead, so every area name goes
-- through the real drawer. Move the cursor to make it redraw (tools/debug/areajobs.py presses right/left).
--   logs "AC k addr f" per forced name and "AC_DONE" after the last; words START..END-1 (default 0..224).
local M = emu.memType.gbaMemory
local BASE, N = 0x0840B334, END or 224
local seen, k, done = {}, START or 0, false
L.on_exec(0x080163F6, 0x080163F6, function()
  if done then return end
  local p
  repeat
    p = emu.read32(BASE + 4 * k, M)
    k = k + 1
  until k >= N or (p >= 0x08000000 and p < 0x0A000000 and not seen[p])
  if p >= 0x08000000 and p < 0x0A000000 and not seen[p] then
    seen[p] = true
    L.log(string.format("AC %d %08X f%d", k - 1, p, L.frame))
    emu.setState({ ["cpu.r0"] = p })
  end
  if k >= N then done = true; L.log("AC_DONE f" .. L.frame) end
end)
