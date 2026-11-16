-- Text coverage for the View foe header (str_tutorial_help 410C64..410C7C): the header is 【kind の name】 and
-- the code (0x081180C6.., 0x0811AA8E..) picks 妖怪 for foe id > 0x4B and 白虎 for id 0x4B. Foe id =
-- s16 [0x02019974 + 2*(3*side + active)] (0x081119E4). This holds the enemy side's three slots
-- (0x0201997A..0x0201997E) at FOE (default 0x4C) every frame, from a battle state; then press L on the
-- command ring to open View foe. Run beside the textcover probe (see docs/status.md).
local M = emu.memType.gbaMemory
local foe = tonumber(FOE or "0x4C")
L.on_frame(function()
  for a = 0x0201997A, 0x0201997E, 2 do emu.write16(a, foe, M) end
end)
