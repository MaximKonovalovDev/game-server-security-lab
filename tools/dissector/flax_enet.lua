-- flax_enet.lua - Wireshark dissector for Flax Engine 1.12 game traffic
--
-- Transport: ENet over UDP (Flax ENetDriver.cpp: 1 channel, no compression,
-- no checksum). Game messages (Flax NetworkMessage) ride as raw channel-0
-- packet payloads: packet-id byte + little-endian fields.
--
-- ENet-core command coverage absorbed from cgutman/wireshark-enet-dissector
-- (GPLv3, tools/reference/) + verified against lsalzman/enet protocol.h:
-- CONNECT/VERIFY full field layout, DISCONNECT data, BANDWIDTH_LIMIT,
-- THROTTLE_CONFIGURE, SEND_FRAGMENT start seq.
--
-- Install: copy to "%APPDATA%\Wireshark\plugins\flax_enet.lua" (or
-- Wireshark's personal plugins dir) and restart Wireshark. Filter: udp.port 7777

local NAME = "flax_enet"
local p_flax = Proto(NAME, "Flax Engine Game (ENet)")

-- ENet constants ------------------------------------------------------------
local CMD_NONE, CMD_ACK, CMD_CONNECT, CMD_VERIFY, CMD_DISCONNECT = 0, 1, 2, 3, 4
local CMD_PING, CMD_SEND_RELIABLE, CMD_SEND_UNRELIABLE, CMD_SEND_FRAGMENT = 5, 6, 7, 8
local CMD_SEND_UNSEQUENCED, CMD_BANDWIDTH, CMD_THROTTLE = 9, 10, 11
local CMD_NAMES = {[1]="ACK", [2]="CONNECT", [3]="VERIFY_CONNECT", [4]="DISCONNECT",
                   [5]="PING", [6]="SEND_RELIABLE", [7]="SEND_UNRELIABLE",
                   [8]="SEND_FRAGMENT", [9]="SEND_UNSEQUENCED",
                   [10]="BANDWIDTH_LIMIT", [11]="THROTTLE_CONFIGURE"}

-- Game packet ids -----------------------------------------------------------
local GAME_NAMES = {[1]="ConnectionRequest", [2]="ConnectionResponse", [3]="PlayerList",
                    [4]="PlayerConnected", [5]="PlayerDisconnected", [6]="PlayerTransform",
                    [7]="PlayersTransform", [8]="ChatMessage", [200]="CombatEvent"}

-- Header fields -------------------------------------------------------------
local f_header = ProtoField.uint16(NAME .. ".header", "Header")
local f_peer_id = ProtoField.uint16(NAME .. ".peer_id", "Peer ID", base.HEX)
local f_session = ProtoField.uint8(NAME .. ".session", "Session ID", base.DEC)
local f_flags = ProtoField.uint16(NAME .. ".flags", "Flags", base.HEX)
local f_sent_time = ProtoField.uint16(NAME .. ".sent_time", "Sent Time", base.DEC)

-- Command fields ------------------------------------------------------------
local f_command = ProtoField.uint8(NAME .. ".command", "Command", base.HEX, CMD_NAMES)
local f_cmd_flags = ProtoField.uint8(NAME .. ".cmd_flags", "Command Flags", base.HEX)
local f_channel = ProtoField.uint8(NAME .. ".channel", "Channel", base.DEC)
local f_seq = ProtoField.uint16(NAME .. ".seq", "Reliable Sequence", base.DEC)
local f_acked_seq = ProtoField.uint16(NAME .. ".acked_seq", "Acked Sequence", base.DEC)
local f_data_len = ProtoField.uint16(NAME .. ".data_len", "Data Length", base.DEC)
local f_unrel_seq = ProtoField.uint16(NAME .. ".unrel_seq", "Unreliable Sequence", base.DEC)
local f_group = ProtoField.uint16(NAME .. ".group", "Unsequenced Group", base.DEC)
local f_frag_total = ProtoField.uint32(NAME .. ".frag_total", "Fragment Total Length", base.DEC)
local f_frag_num = ProtoField.uint32(NAME .. ".frag_num", "Fragment Number", base.DEC)
local f_frag_count = ProtoField.uint32(NAME .. ".frag_count", "Fragment Count", base.DEC)
local f_frag_offset = ProtoField.uint32(NAME .. ".frag_offset", "Fragment Offset", base.DEC)
local f_out_peer = ProtoField.uint16(NAME .. ".out_peer", "Outgoing Peer ID", base.HEX)
local f_mtu = ProtoField.uint32(NAME .. ".mtu", "MTU", base.DEC)
local f_window = ProtoField.uint32(NAME .. ".window", "Window Size", base.DEC)
local f_channels = ProtoField.uint32(NAME .. ".channels", "Channel Count", base.DEC)
local f_connect_id = ProtoField.uint32(NAME .. ".connect_id", "Connect ID", base.HEX)
local f_connect_data = ProtoField.uint32(NAME .. ".connect_data", "Connect Data", base.HEX)
local f_disconnect_data = ProtoField.uint32(NAME .. ".disconnect_data", "Disconnect Data", base.HEX)
local f_in_bw = ProtoField.uint32(NAME .. ".in_bw", "Incoming Bandwidth", base.DEC)
local f_out_bw = ProtoField.uint32(NAME .. ".out_bw", "Outgoing Bandwidth", base.DEC)
local f_throttle_interval = ProtoField.uint32(NAME .. ".throttle_interval", "Throttle Interval", base.DEC)
local f_throttle_accel = ProtoField.uint32(NAME .. ".throttle_accel", "Throttle Acceleration", base.DEC)
local f_throttle_decel = ProtoField.uint32(NAME .. ".throttle_decel", "Throttle Deceleration", base.DEC)
local f_frag_start_seq = ProtoField.uint16(NAME .. ".frag_start_seq", "Fragment Start Seq", base.DEC)
local f_bandwidth = ProtoField.uint32(NAME .. ".bandwidth", "Bandwidth", base.DEC)

-- Game message fields -------------------------------------------------------
local f_game_id = ProtoField.uint8(NAME .. ".game_id", "Packet ID", base.DEC, GAME_NAMES)
local f_game_name = ProtoField.string(NAME .. ".username", "Username")
local f_game_token_len = ProtoField.int32(NAME .. ".token_len", "Token Length", base.DEC)
local f_game_token = ProtoField.bytes(NAME .. ".token", "Token")
local f_game_state = ProtoField.uint8(NAME .. ".state", "State", base.DEC, {[0]="Accepted", [1]="Rejected"})
local f_game_guid = ProtoField.string(NAME .. ".guid", "Guid")
local f_game_count = ProtoField.int32(NAME .. ".count", "Count", base.DEC)
local f_game_msg = ProtoField.string(NAME .. ".message", "Message")
local f_game_has_sender = ProtoField.uint8(NAME .. ".has_sender", "Has Sender", base.DEC)
local f_game_event = ProtoField.uint8(NAME .. ".event", "Combat Event", base.DEC,
                                      {[0]="Hit", [1]="Damage", [2]="Death", [3]="Dismember"})
local f_game_attacker = ProtoField.int32(NAME .. ".attacker", "Attacker", base.DEC)
local f_game_target = ProtoField.int32(NAME .. ".target", "Target", base.DEC)
local f_game_damage = ProtoField.float(NAME .. ".damage", "Damage")
local f_game_pos = ProtoField.string(NAME .. ".pos", "Position")
local f_game_rot = ProtoField.string(NAME .. ".rot", "Rotation")
local f_game_raw = ProtoField.bytes(NAME .. ".raw", "Raw Payload")

p_flax.fields = { f_header, f_peer_id, f_session, f_flags, f_sent_time,
                  f_command, f_cmd_flags, f_channel, f_seq, f_acked_seq,
                  f_data_len, f_unrel_seq, f_group, f_frag_total, f_frag_num,
                  f_frag_count, f_frag_offset, f_frag_start_seq,
                  f_out_peer, f_mtu, f_window, f_channels, f_connect_id,
                  f_connect_data, f_disconnect_data, f_in_bw, f_out_bw,
                  f_throttle_interval, f_throttle_accel, f_throttle_decel,
                  f_bandwidth,
                  f_game_id, f_game_name, f_game_token_len, f_game_token,
                  f_game_state, f_game_guid, f_game_count, f_game_msg,
                  f_game_has_sender, f_game_event, f_game_attacker, f_game_target,
                  f_game_damage, f_game_pos, f_game_rot, f_game_raw }

-- Helpers -------------------------------------------------------------------

local function be16(buf, off) return buf:range(off, 2):uint() end
local function le16(buf, off) return buf:range(off, 2):le_uint() end
local function le32(buf, off) return buf:range(off, 4):le_uint() end
local function le32s(buf, off) return buf:range(off, 4):le_int() end
local function lef32(buf, off) return buf:range(off, 4):le_float() end

-- .NET Guid layout: int LE + 2 shorts LE + 8 raw bytes
local function parse_guid(buf, off)
    local a = le32(buf, off)
    local b = le16(buf, off + 4)
    local c = le16(buf, off + 6)
    local d = buf:range(off + 8, 8)
    return string.format("%08x-%04x-%04x-%s-%s", a, b, c, d:raw():sub(1, 2), d:raw():sub(3, 8))
end

-- string: u16le char count + UTF-16LE bytes
local function parse_game_string(buf, off)
    local n = le16(buf, off)
    local bytes = buf:range(off + 2, n * 2)
    local s = bytes:raw()
    local out = {}
    for i = 1, n do
        local code = s:byte(i * 2 - 1) + s:byte(i * 2) * 256
        out[#out + 1] = string.char(code)
    end
    return table.concat(out), off + 2 + n * 2
end

local function add_guid(tvb, tree, label, off)
    tree:add(f_game_guid, tvb:range(off, 16), parse_guid(tvb, off)):append_text(" (" .. label .. ")")
end

-- Game message dissector (payload = packet id + fields) ----------------------

local function dissect_game(tvb, tree, payload_off, payload_len)
    if payload_len < 1 then return end
    local subtree = tree:add(p_flax, "Game Message")
    local id = tvb:range(payload_off, 1):uint()
    subtree:add(f_game_id, tvb:range(payload_off, 1))
    subtree:append_text(" [" .. (GAME_NAMES[id] or "Unknown") .. "]")
    local off = payload_off + 1

    if id == 1 then -- ConnectionRequest: str username, i32 tokenLen, token
        local name, noff = parse_game_string(tvb, off)
        subtree:add(f_game_name, tvb:range(off, noff - off), name)
        off = noff
        if off + 4 <= payload_off + payload_len then
            local tlen = le32s(tvb, off)
            subtree:add(f_game_token_len, tvb:range(off, 4))
            off = off + 4
            if tlen > 0 and tlen <= 1024 and off + tlen <= payload_off + payload_len then
                subtree:add(f_game_token, tvb:range(off, tlen))
            end
        end
    elseif id == 2 then -- ConnectionResponse: u8 state, guid
        subtree:add(f_game_state, tvb:range(off, 1))
        if off + 17 <= payload_off + payload_len then
            add_guid(tvb, subtree, "id", off + 1)
        end
    elseif id == 3 then -- PlayerList: i32 count, count x (str, guid)
        local count = le32s(tvb, off)
        subtree:add(f_game_count, tvb:range(off, 4))
        off = off + 4
        for i = 1, math.min(count, 256) do
            if off + 2 > payload_off + payload_len then break end
            local name, noff = parse_game_string(tvb, off)
            subtree:add(f_game_name, tvb:range(off, noff - off), string.format("[%d] %s", i, name))
            off = noff
            if off + 16 <= payload_off + payload_len then
                add_guid(tvb, subtree, "player", off)
                off = off + 16
            else break end
        end
        if count > 256 then
            subtree:add_expert_info(PI_MALFORMED, PI_WARN, "Count " .. count .. " exceeds sane cap (allocation DoS?)")
        end
    elseif id == 4 then -- PlayerConnected: guid, str
        if off + 16 <= payload_off + payload_len then add_guid(tvb, subtree, "id", off) end
        off = off + 16
        local name, noff = parse_game_string(tvb, off)
        subtree:add(f_game_name, tvb:range(off, noff - off), name)
        off = noff
    elseif id == 5 then -- PlayerDisconnected: guid
        if off + 16 <= payload_off + payload_len then add_guid(tvb, subtree, "id", off) end
    elseif id == 7 then -- PlayersTransform: i32 count, count x (guid, vec3, quat)
        local count = le32s(tvb, off)
        subtree:add(f_game_count, tvb:range(off, 4))
        if count > 256 then
            subtree:add_expert_info(PI_MALFORMED, PI_WARN, "Count " .. count .. " exceeds sane cap (allocation DoS?)")
        end
        off = off + 4
        for i = 1, math.min(count, 256) do
            if off + 44 <= payload_off + payload_len then
                add_guid(tvb, subtree, "player", off)
                local x, y, z = lef32(tvb, off + 16), lef32(tvb, off + 20), lef32(tvb, off + 24)
                subtree:add(f_game_pos, tvb:range(off + 16, 12), string.format("(%g, %g, %g)", x, y, z))
                local qx, qy, qz, qw = lef32(tvb, off + 28), lef32(tvb, off + 32), lef32(tvb, off + 36), lef32(tvb, off + 40)
                subtree:add(f_game_rot, tvb:range(off + 28, 16), string.format("(%g, %g, %g, %g)", qx, qy, qz, qw))
                off = off + 44
            else break end
        end
    elseif id == 8 then -- ChatMessage: str, bool hasSender, guid?
        local msg, noff = parse_game_string(tvb, off)
        subtree:add(f_game_msg, tvb:range(off, noff - off), msg)
        off = noff
        if off < payload_off + payload_len then
            local has = tvb:range(off, 1):uint()
            subtree:add(f_game_has_sender, tvb:range(off, 1))
            off = off + 1
            if has == 1 and off + 16 <= payload_off + payload_len then
                add_guid(tvb, subtree, "sender", off)
            end
        end
    elseif id == 200 then -- CombatEvent: u8 event, i32 attacker, i32 target, f32 damage, u8 kind, bool crit, 3 x f32
        subtree:add(f_game_event, tvb:range(off, 1))
        subtree:add(f_game_attacker, tvb:range(off + 1, 4))
        subtree:add(f_game_target, tvb:range(off + 5, 4))
        subtree:add(f_game_damage, tvb:range(off + 9, 4))
    end
end

-- Main dissector --------------------------------------------------------------

function p_flax.dissector(tvb, pkt, tree)
    local len = tvb:len()
    if len < 2 then return 0 end

    local t = tree:add(p_flax, tvb(0, len))
    t:add(f_header, tvb(0, 2))

    local h16 = be16(tvb, 0)
    local flags = h16 & 0xC000
    local session = (h16 >> 12) & 0x3
    local peer_id = h16 & 0x0FFF
    t:add(f_peer_id, tvb(0, 2), peer_id)
    t:add(f_session, tvb(0, 2), session)
    t:add(f_flags, tvb(0, 2), flags)

    local off = 2
    if (h16 & 0x8000) ~= 0 then -- SENT_TIME flag
        t:add(f_sent_time, tvb(off, 2))
        off = off + 2
    end

    while off + 4 <= len do
        local cid = tvb:range(off, 1):uint()
        local channel = tvb:range(off + 1, 1):uint()
        local seq = be16(tvb, off + 2)
        local base_cmd = cid & 0x0F
        local cmd_flags = cid & 0xF0

        local ct = t:add(p_flax, "Command: " .. (CMD_NAMES[base_cmd] or ("Unknown(" .. base_cmd .. ")")))
        ct:add(f_command, tvb(off, 1))
        if cmd_flags ~= 0 then
            ct:add(f_cmd_flags, tvb(off, 1), cmd_flags)
            if cmd_flags & 0x80 ~= 0 then ct:append_text(" [ACK requested]") end
            if cmd_flags & 0x40 ~= 0 then ct:append_text(" [UNSEQUENCED]") end
        end
        ct:add(f_channel, tvb(off + 1, 1))
        ct:add(f_seq, tvb(off + 2, 2))
        off = off + 4

        if base_cmd == CMD_ACK then
            ct:add(f_acked_seq, tvb(off, 2))
            ct:add(f_sent_time, tvb(off + 2, 2))
            off = off + 4
        elseif base_cmd == CMD_CONNECT then
            ct:add(f_out_peer, tvb(off, 2))
            ct:add(f_mtu, tvb(off + 4, 4))
            ct:add(f_window, tvb(off + 8, 4))
            ct:add(f_channels, tvb(off + 12, 4))
            ct:add(f_in_bw, tvb(off + 16, 4))
            ct:add(f_out_bw, tvb(off + 20, 4))
            ct:add(f_throttle_interval, tvb(off + 24, 4))
            ct:add(f_throttle_accel, tvb(off + 28, 4))
            ct:add(f_throttle_decel, tvb(off + 32, 4))
            ct:add(f_connect_id, tvb(off + 36, 4))
            ct:add(f_connect_data, tvb(off + 40, 4))
            off = off + 44
        elseif base_cmd == CMD_VERIFY then
            ct:add(f_out_peer, tvb(off, 2))
            ct:add(f_mtu, tvb(off + 4, 4))
            ct:add(f_window, tvb(off + 8, 4))
            ct:add(f_channels, tvb(off + 12, 4))
            ct:add(f_in_bw, tvb(off + 16, 4))
            ct:add(f_out_bw, tvb(off + 20, 4))
            ct:add(f_throttle_interval, tvb(off + 24, 4))
            ct:add(f_throttle_accel, tvb(off + 28, 4))
            ct:add(f_throttle_decel, tvb(off + 32, 4))
            ct:add(f_connect_id, tvb(off + 36, 4))
            off = off + 40
        elseif base_cmd == CMD_DISCONNECT then
            ct:add(f_disconnect_data, tvb(off, 4))
            off = off + 4
        elseif base_cmd == CMD_PING then
            -- no body
        elseif base_cmd == CMD_SEND_RELIABLE then
            if off + 2 > len then break end
            local dlen = be16(tvb, off)
            ct:add(f_data_len, tvb(off, 2), dlen)
            off = off + 2
            if dlen > 0 and off + dlen <= len then
                if channel == 0 then
                    dissect_game(tvb, ct, off, dlen)
                else
                    ct:add(f_game_raw, tvb(off, dlen))
                end
            end
            off = off + dlen
        elseif base_cmd == CMD_SEND_UNRELIABLE then
            ct:add(f_unrel_seq, tvb(off, 2))
            local dlen = be16(tvb, off + 2)
            ct:add(f_data_len, tvb(off + 2, 2), dlen)
            off = off + 4
            if dlen > 0 and off + dlen <= len then
                if channel == 0 then
                    dissect_game(tvb, ct, off, dlen)
                else
                    ct:add(f_game_raw, tvb(off, dlen))
                end
            end
            off = off + dlen
        elseif base_cmd == CMD_SEND_UNSEQUENCED then
            ct:add(f_group, tvb(off, 2))
            local dlen = be16(tvb, off + 2)
            ct:add(f_data_len, tvb(off + 2, 2), dlen)
            off = off + 4
            if dlen > 0 and off + dlen <= len then
                if channel == 0 then dissect_game(tvb, ct, off, dlen) end
            end
            off = off + dlen
        elseif base_cmd == CMD_SEND_FRAGMENT then
            ct:add(f_frag_start_seq, tvb(off, 2))
            ct:add(f_frag_count, tvb(off + 4, 4))
            ct:add(f_frag_num, tvb(off + 8, 4))
            ct:add(f_frag_total, tvb(off + 12, 4))
            ct:add(f_frag_offset, tvb(off + 16, 4))
            local dlen = be16(tvb, off + 2)
            ct:add(f_data_len, tvb(off + 2, 2), dlen)
            off = off + 20 + dlen
        elseif base_cmd == CMD_BANDWIDTH then
            ct:add(f_in_bw, tvb(off, 4))
            ct:add(f_out_bw, tvb(off + 4, 4))
            off = off + 8
        elseif base_cmd == CMD_THROTTLE then
            ct:add(f_throttle_interval, tvb(off, 4))
            ct:add(f_throttle_accel, tvb(off + 4, 4))
            ct:add(f_throttle_decel, tvb(off + 8, 4))
            off = off + 12
        else
            break
        end
    end

    pkt.cols.info:set("Flax " .. (CMD_NAMES[base_cmd or 0] or "?") .. " peer=" .. peer_id)
    return len
end

local udp_port = DissectorTable.get("udp.port")
udp_port:add(7777, p_flax)
