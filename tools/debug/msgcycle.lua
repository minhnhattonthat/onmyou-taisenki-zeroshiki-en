-- Text coverage for battle messages (str_battle_msgs and the battle lines of str_tutorial_help): each time the
-- battle shows a message, hand the drawer the next listed string instead, so every message goes through the real
-- battle window renderer in turn. 0x08102E88 loads the pending message pointer [0x02019BE0 + 4 * s16 0x02019AA0];
-- if [... + 8] (a name to put in front) is set it calls 0x0810F928, else 0x0810F9E0 with r2 = message. We replace
-- r3 at 0x08102E8A and zero r0 at 0x08102E96 so the plain path runs (docs/re/text.md "Battle messages").
--   ADDRS='0x0840C9BC,0x0840D3B0,...' built-ROM addresses (build/strings.tsv), each forced twice; logs "MC addr f".
--   KEEP='0x02019938:290,0x02019944:208': u16 values re-poked every frame so the battle never ends.
-- Run by tools/debug/msgjobs.py. Ends the run 600 frames after the last forced message (MC_END).
local M = emu.memType.gbaMemory
local keep, list = {}, {}
for a, v in tostring(KEEP or ""):gmatch("(0x%x+):(%d+)") do keep[#keep + 1] = { tonumber(a), tonumber(v) } end
for a in tostring(ADDRS or ""):gmatch("0x%x+") do list[#list + 1] = tonumber(a) end
local n, plain, end_at = 0, false, nil
L.on_frame(function(f)
  for _, k in ipairs(keep) do emu.write16(k[1], k[2], M) end
  if end_at and f >= end_at then L.log("MC_END f" .. f); end_at = nil; L.finish(0) end
end)
L.on_exec(0x08102E8A, 0x08102E8A, function()
  if end_at or n >= 2 * #list then return end
  local s = emu.getState()
  if s["cpu.r3"] == 0 then return end
  local p = list[(n // 2) + 1]
  emu.setState({ ["cpu.r3"] = p })
  plain = true
  n = n + 1
  L.log(string.format("MC %08X f%d", p, L.frame))
  if n >= 2 * #list then end_at = L.frame + 600 end
end)
L.on_exec(0x08102E96, 0x08102E96, function()
  if plain then emu.setState({ ["cpu.r0"] = 0 }); plain = false end
end)
