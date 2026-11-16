-- Warp to a named scene from a cold boot (phase 2 debug tool). See docs/re/debug.md.
--   emu.py ROM --out work/qa/warp --script tools/debug/warp.lua --var "SCENE='ch2_start'" --frames 6000 --mash 40 --sheet
-- Globals: SCENE (required), SCENES_FILE (default <repo>/tools/debug/scenes.txt), HOLD (frames to run after the
-- scene is reached, default 600; then scene.png + final.png are written and the run stops), GOD (battle: refill the
-- player's HP every frame), WIN (battle: zero the enemy's HP once, to reach the win screen).
--
-- How it works: the scene's input route runs from power-on. Kinds other than `boot`/`top` start a new game with the
-- fixed name-entry route; when the game calls StartScript(1001) (0x0802A39C, the intro), warp.lua swaps in its own
-- bytecode script built in EWRAM (0x0203F000): /029 story flags, /144 map x y (place the player), /082 (fade in),
-- then the scene's own raw bytecode. `script` scenes wait until the field runs (mode 0x02005074 == 2) and then make
-- the field run event script [0x020037BE] via mode 8, the same path the game uses.
local M = emu.memType.gbaMemory
local MODE, TOP, SID_VAR, CUR_OP = 0x02005074, 0x03003523, 0x020037BE, 0x02002DD8
local BUF = 0x0203F000
local NEWGAME = "600:-|6:start|150:-|6:start|150:-|6:a|400:-|6:start|200:-|6:left|20:-|6:a|400:-"
local DEADLINE = 15000

local function repo_root()
  local o = OUT:gsub("\\", "/")
  local r = o:match("^(.*)/work/") or o:match("^(.*)/build/")
  return r or "."
end

local function parse_scenes(path)
  local t = {}
  for line in io.lines(path) do
    local l = line:gsub("#.*", ""):match("^%s*(.-)%s*$")
    if l ~= "" then
      local name, kind, rest = l:match("^(%S+)%s+(%S+)%s*(.*)$")
      if not name then error("bad scene line: " .. line) end
      local s = { name = name, kind = kind, args = {}, opt = {} }
      for tok in rest:gmatch("%S+") do
        local k, v = tok:match("^([%w_]+)=(.*)$")
        if k then s.opt[k] = v else s.args[#s.args + 1] = tok end
      end
      t[name] = s
    end
  end
  return t
end

local function queue_route(r)
  for step in r:gmatch("[^|]+") do
    local n, b = step:match("^(%d+):(%S+)$")
    if not n then error("bad press step: " .. step) end
    L.press(b, tonumber(n))
  end
end

local function d4(n)
  n = tonumber(n)
  if n < 0 then return string.format("-%03d", -n) end
  return string.format("%04d", n)
end

assert(SCENE, "set --var \"SCENE='name'\" (names: tools/debug/scenes.txt)")
local scenes = parse_scenes(SCENES_FILE or (repo_root() .. "/tools/debug/scenes.txt"))
local S = scenes[SCENE] or error("unknown scene " .. tostring(SCENE))
local hold = tonumber(HOLD or S.opt.hold or (S.kind == "script" and 45 or 600))
L.log("warp " .. S.name .. " kind=" .. S.kind)

local reached_at, finished = nil, false
local function reached(what)
  if reached_at then return end
  reached_at = L.frame
  L.log(string.format("SCENE_OK %s f%d %s", S.name, L.frame, what or ""))
  if S.opt.press and S.kind ~= "boot" then queue_route(S.opt.press) end
end

-- poke=ADDR:VAL[,ADDR:VAL]: u16 writes for 10 frames once the scene is reached (battle_lose: player HP = 1);
-- poke_after=N starts them N frames later instead (after the press route has opened a menu that rebuilds RAM)
if S.opt.poke then
  local after = tonumber(S.opt.poke_after or 0)
  L.on_frame(function(f)
    if reached_at and f - reached_at >= after and f - reached_at < after + 10 then
      for a, v in S.opt.poke:gmatch("(0x%x+):(%d+)") do emu.write16(tonumber(a), tonumber(v), M) end
    end
  end)
end

-- Build the injected script for the new-game kinds.
local function build_inject()
  local parts = {}
  for f in (S.opt.flags or ""):gmatch("[^,]+") do
    local n, v = f:match("^(%d+)=?(%d*)$")
    parts[#parts + 1] = "/0290000" .. d4(n) .. d4(v ~= "" and v or 1)
  end
  local map = S.opt.map or (S.kind == "field" and S.args[1]) or "23"
  parts[#parts + 1] = "/144" .. d4(map) .. "00000000"
  parts[#parts + 1] = "/135" .. d4(S.opt.x or 8) .. d4(S.opt.y or 8) .. "00000000/082"
  if S.kind == "raw" then parts[#parts + 1] = S.args[1] end
  parts[#parts + 1] = "/999"
  return table.concat(parts)
end

-- until_op=H: the scene counts as reached only once the script interpreter runs opcode H (hex, e.g. 073 = a
-- dialogue page, 035 = battle start). Script scenes default to 073 so the proof shot shows the event's text.
-- A comma list means any of them; script scenes default to 073,036,098 (text follows each of these).
local want_op = S.opt.until_op or (S.kind == "script" and "073,036,098" or nil)
local want = {}
for h in (want_op or ""):gmatch("[^,]+") do want[tonumber(h, 16)] = true end
local function op_ok() return not want_op or want[emu.read16(CUR_OP, M)] == true end

if S.kind == "boot" then
  queue_route(S.opt.press or "")
  L.on_frame(function()
    if not reached_at and L.route_done() and op_ok() then reached("route done" .. (want_op and " + op" or "")) end
  end)
elseif S.kind == "top" then
  local n, set = tonumber(S.args[1]), false
  L.on_frame(function()
    local top = emu.read(TOP, M)
    if not set and top == 3 and L.frame > 700 then
      set = true
      emu.write(TOP, n, M)
    elseif set and not reached_at and top >= n then
      reached("top=" .. top)
    end
  end)
elseif S.kind == "script" or S.kind == "field" or S.kind == "raw" then
  queue_route(NEWGAME)
  local inject, armed, fired = build_inject(), false, false
  local sid = S.kind == "script" and tonumber(S.args[1]) or nil
  local started = false
  L.log("inject " .. inject)
  L.on_exec(0x0802A39C, 0x0802A39C, function()
    local r0 = emu.getState()["cpu.r0"]
    L.log(string.format("f%d StartScript %d", L.frame, r0))
    if not fired and r0 == 1001 then armed = true end
    if sid and r0 == sid and fired then started = true end
  end)
  if sid then
    L.on_frame(function()
      if started and not reached_at and op_ok() then
        reached(string.format("script %d op %03X", sid, emu.read16(CUR_OP, M)))
      end
    end)
  end
  L.on_exec(0x0802A404, 0x0802A404, function()  -- r4 = script pointer, about to be stored and run
    if not armed then return end
    armed, fired = false, true
    for i = 1, #inject do emu.write(BUF + i - 1, inject:byte(i), M) end
    emu.write(BUF + #inject, 0, M)
    emu.setState({ ["cpu.r4"] = BUF })
  end)
  local field, kicked = 0, false
  L.on_frame(function()
    if not fired then return end
    if emu.read(MODE, M) == 2 then field = field + 1 else field = 0 end
    if field == 60 and not kicked then
      kicked = true
      if sid then
        emu.write16(SID_VAR, sid, M)
        emu.write32(0x02002E84, 0, M)  -- interpreter "waiting" flag; the field leaves it 1, which stalls /230
        emu.write(MODE, tonumber(S.opt.kick or 6), M)
      elseif S.kind == "field" then
        reached("field map " .. S.args[1])
      end
    end
    if S.kind == "raw" and not reached_at and op_ok() and (want_op or kicked) then
      reached(want_op and string.format("op %03X", emu.read16(CUR_OP, M)) or "raw done")
    end
  end)
else
  error("unknown scene kind " .. S.kind)
end

if TRACE then  -- --var TRACE=1: log every change of top state, mode, opcode and map
  local last = ""
  L.on_frame(function(f)
    local cur = string.format("top=%d mode=%d op=%03X map=%d 27A4=%d 2E84=%d", emu.read(TOP, M), emu.read(MODE, M),
      emu.read16(CUR_OP, M), emu.read16(0x02002E88, M), emu.read16(0x020027A4, M), emu.read32(0x02002E84, M))
    if cur ~= last then L.log("f" .. f .. " " .. cur); last = cur end
  end)
end

local seq = tonumber(SEQ or 0)  -- --var SEQ=N: a shot every N frames from SCENE_OK to the end (QA contact sheets)
L.on_frame(function(f)
  if finished then return end
  if seq > 0 and reached_at and (f - reached_at) % seq == 0 then L.shot(string.format("seq_%06d.png", f)) end
  if not reached_at and f > (tonumber(S.opt.deadline) or DEADLINE) then
    L.shot("final.png")
    L.fail("scene " .. S.name .. " not reached by frame " .. f)
    finished = true
  elseif reached_at and f >= reached_at + hold and L.route_done() then
    finished = true
    L.shot("scene.png")
    L.shot("final.png")
    L.log("final frame " .. f)
    if STATE_OUT then L.save_state(STATE_OUT, function() L.finish(0) end) else L.finish(0) end
  end
end)
