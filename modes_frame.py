#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
#
# modes_frame.py - Mode S / 1090ES frame helpers for vhmodesgen.
#
# Usage:
#   python3 modes_frame.py <hex frame> <VH mark>     e.g.
#   python3 modes_frame.py 8D7C61AD2150B5A0820820B9C954 VH-TKV
#
# What it does:
#   * VH- mark <-> 24-bit address, using vhmodesgen.py's conversion
#   * Mode S CRC-24 (generator 0x1FFF409) and address recovery from the
#     Address/Parity (AP) field of DF0/4/5/16/20/21
#   * Encoders for test frames: DF4, DF5, DF11, and DF17 TC 4 (identification),
#     TC 9-18 (airborne position, CPR), TC 19 (velocity), TC 31 (op status v2)
#   * check(): decode one hex frame and say whether it belongs to a given VH mark
#
# References: ICAO Annex 10 Vol IV and Doc 9871; RTCA DO-260B; Junzi Sun,
# "The 1090 Megahertz Riddle", 2nd ed. (TU Delft OPEN, CC BY-NC-SA 4.0).
# This was not cross-checked against those standards line by line. The encoders
# are checked by round-tripping through pyModeS (test_vhmodesgen.py).

import math
import sys

import vhmodesgen

GEN = 0x1FFF409                     # x^24 + x^23 + ... + x^10 + x^3 + 1
CHARSET = "#ABCDEFGHIJKLMNOPQRSTUVWXYZ##### ###############0123456789######"


# ---------------------------------------------------------------- VH <-> address

def vh_to_icao(mark: str) -> int:
    """'VH-TKV', 'VHTKV' or 'TKV' -> 0x7C61AD. Raises ValueError otherwise."""
    address = vhmodesgen.convert_to_mode_s(mark)
    if not address:
        raise ValueError(f"not a VH- mark: {mark!r}")
    return int(address, 16)


def icao_to_vh(addr: int):
    """0x7C61AD -> 'VH-TKV'; None if the address isn't in the VH- mark space."""
    address = f"{addr:06x}"
    return vhmodesgen.convert_to_vh(address) if vhmodesgen.is_vh_address(address) else None


# ---------------------------------------------------------------- CRC / parity

def parity(data: int, nbits: int) -> int:
    """24-bit Mode S parity of `nbits` of data (data * x^24 mod G)."""
    reg = data << 24
    for i in range(nbits + 23, 23, -1):
        if (reg >> i) & 1:
            reg ^= GEN << (i - 24)
    return reg & 0xFFFFFF


def split(frame_hex: str):
    """-> (data_bits_int, n_data_bits, last24)"""
    v = int(frame_hex, 16)
    n = len(frame_hex) * 4
    if n not in (56, 112):
        raise ValueError("frame must be 14 or 28 hex characters")
    return v >> 24, n - 24, v & 0xFFFFFF


def recovered_address(frame_hex: str) -> int:
    """For AP formats (DF0/4/5/16/20/21): AP xor parity = address.
    For DF11/17/18 the same arithmetic gives the PI overlay instead
    (0 for a good DF17/18, the interrogator code for DF11)."""
    data, n, last = split(frame_hex)
    return last ^ parity(data, n)


# ---------------------------------------------------------------- frame builders

def _frame(data: int, nbits: int, overlay: int = 0) -> str:
    """Append parity xor overlay; overlay = address for AP formats, II for DF11."""
    full = (data << 24) | (parity(data, nbits) ^ overlay)
    return f"{full:0{(nbits + 24) // 4}X}"


def df4(addr: int, alt_ft: int, fs: int = 0) -> str:
    """Surveillance altitude reply. AC field uses 25 ft (Q=1) coding.
    FS 0 = airborne, no alert, no SPI."""
    n = (alt_ft + 1000) // 25
    # 13-bit AC: bits C1 A1 C2 A2 C4 A4 M B1 Q B2 D2 B4 D4; with M=0, Q=1 the
    # 11-bit N is laid out as N[10:5] M N[4] Q N[3:0]
    ac = ((n >> 5) << 7) | (((n >> 4) & 1) << 5) | (1 << 4) | (n & 0xF)
    data = (4 << 27) | (fs << 24) | (0 << 19) | (0 << 13) | ac
    return _frame(data, 32, addr)


def _squawk_id13(code: str) -> int:
    """'1200' -> 13-bit ID field (C1 A1 C2 A2 C4 A4 X B1 D1 B2 D2 B4 D4)."""
    a, b, c, d = (int(x) for x in code)
    bit = lambda v, k: (v >> k) & 1
    seq = [bit(c, 0), bit(a, 0), bit(c, 1), bit(a, 1), bit(c, 2), bit(a, 2), 0,
           bit(b, 0), bit(d, 0), bit(b, 1), bit(d, 1), bit(b, 2), bit(d, 2)]
    v = 0
    for s in seq:
        v = (v << 1) | s
    return v


def df5(addr: int, squawk: str, fs: int = 0) -> str:
    data = (5 << 27) | (fs << 24) | _squawk_id13(squawk)
    return _frame(data, 32, addr)


def df11(addr: int, ca: int = 5, ii: int = 0) -> str:
    """All-call reply. CA 5 = level 2+, airborne. PI = parity xor II."""
    data = (11 << 27) | (ca << 24) | addr
    return _frame(data, 32, ii)


def df17(addr: int, me: int, ca: int = 5) -> str:
    data = (17 << 83) | (ca << 80) | (addr << 56) | me
    return _frame(data, 88, 0)


def me_ident(callsign: str, tc: int = 4, cat: int = 1) -> int:
    """TC 4 + CA 1 = emitter category A1 (light, < 15 500 lb)."""
    cs = callsign.upper().ljust(8)[:8]
    me = (tc << 51) | (cat << 48)
    for i, ch in enumerate(cs):
        me |= CHARSET.index(ch) << (42 - 6 * i)
    return me


def _nl(lat: float) -> int:
    if lat == 0:
        return 59
    if abs(lat) == 87:
        return 2
    if abs(lat) > 87:
        return 1
    nz = 15
    a = 1 - math.cos(math.pi / (2 * nz))
    b = math.cos(math.pi / 180 * abs(lat)) ** 2
    return math.floor(2 * math.pi / math.acos(1 - a / b))


def cpr_encode(lat: float, lon: float, odd: int):
    nb = 2 ** 17
    dlat = 360 / (60 - odd)
    yz = math.floor(nb * ((lat % dlat) / dlat) + 0.5)
    rlat = dlat * (yz / nb + math.floor(lat / dlat))
    dlon = 360 / max(_nl(rlat) - odd, 1)
    xz = math.floor(nb * ((lon % dlon) / dlon) + 0.5)
    return yz % nb, xz % nb


def me_airborne_pos(lat, lon, alt_ft, odd, tc=11, nicb=0, ss=0, t=0) -> int:
    n = (alt_ft + 1000) // 25
    alt = ((n >> 4) << 5) | (1 << 4) | (n & 0xF)
    yz, xz = cpr_encode(lat, lon, odd)
    return ((tc << 51) | (ss << 49) | (nicb << 48) | (alt << 36) | (t << 35) |
            (odd << 34) | (yz << 17) | xz)


def me_velocity(gs_kt: float, trk_deg: float, vr_fpm: int = 0, nacv: int = 1,
                vr_src_baro: int = 1) -> int:
    """TC 19 subtype 1 (ground speed). geo-baro difference left as 'no info'."""
    vew = gs_kt * math.sin(math.radians(trk_deg))
    vns = gs_kt * math.cos(math.radians(trk_deg))
    dew, dns = int(vew < 0), int(vns < 0)
    vew_f, vns_f = round(abs(vew)) + 1, round(abs(vns)) + 1
    svr = int(vr_fpm < 0)
    vr_f = round(abs(vr_fpm) / 64) + 1
    return ((19 << 51) | (1 << 48) | (nacv << 43) | (dew << 42) | (vew_f << 32) |
            (dns << 31) | (vns_f << 21) | (vr_src_baro << 20) | (svr << 19) |
            (vr_f << 10))


def me_opstatus_v2(nacp: int, sil: int, sda: int, nica: int = 0, gva: int = 0,
                   nicbaro: int = 1, sils: int = 0, saf: int = 1) -> int:
    """TC 31 airborne, version 2. Capability class left at 0 (not modelled).
    OM: SAF (single-antenna flag) ME bit 30, SDA ME bits 31-32."""
    cc = 0
    om = (saf << 10) | (sda << 8)
    return ((31 << 51) | (0 << 48) | (cc << 32) | (om << 16) | (2 << 13) |
            (nica << 12) | (nacp << 8) | (gva << 6) | (sil << 4) |
            (nicbaro << 3) | (0 << 2) | (sils << 1))


# ---------------------------------------------------------------- checking

def check(frame_hex: str, mark: str) -> str:
    """Does this frame belong to `mark`? Returns a one-line verdict."""
    want = vh_to_icao(mark)
    data, n, last = split(frame_hex)
    df = data >> (n - 5)
    if df > 24:
        df = 24
    if df in (17, 18, 11):
        aa = (data >> (n - 32)) & 0xFFFFFF
        pi = recovered_address(frame_hex)
        ok_crc = (pi == 0) if df != 11 else (pi < 16)
        who = icao_to_vh(aa) or "not a VH mark"
        out = f"DF{df} AA={aa:06X} ({who}) parity {'OK' if ok_crc else 'BAD'}"
        if df == 11:
            out += f", II={pi}"
        if df == 17 and ok_crc:
            tc = (data >> 51) & 0x1F
            out += f", TC={tc}"
            if 1 <= tc <= 4:
                cs = "".join(CHARSET[(data >> (42 - 6 * i)) & 0x3F] for i in range(8)).strip()
                cat = "ABCD"[4 - tc] + str((data >> 48) & 7)
                out += f", flight ID '{cs}', emitter {cat}"
                reg = vhmodesgen.normalise_vh(mark)
                cs_ok = cs in (reg, "VH" + reg)
                out += "" if cs_ok else " (flight ID is not the registration)"
        match = ok_crc and aa == want
    else:
        aa = recovered_address(frame_hex)
        who = icao_to_vh(aa) or "not a VH mark"
        out = f"DF{df} address recovered from AP = {aa:06X} ({who})"
        match = aa == want
        if not match:
            out += " - no match: either another aircraft or a corrupted frame (AP can't tell which)"
    return out + f" -> {'MATCHES' if match else 'does not match'} {mark.upper()} ({want:06X})"


# ---------------------------------------------------------------- example frames

def example_frames(mark: str = "VH-TKV", lat: float = -34.0403, lon: float = 150.6872,
                   alt_ft: int = 1500):
    """Synthetic frames for one aircraft (default: VH-TKV over Camden, 1500 ft)."""
    a = vh_to_icao(mark)
    reg = vhmodesgen.normalise_vh(mark)
    return {
        "ident": df17(a, me_ident(reg)),
        "ident_vh": df17(a, me_ident("VH" + reg)),
        "pos_even": df17(a, me_airborne_pos(lat, lon, alt_ft, 0)),
        "pos_odd": df17(a, me_airborne_pos(lat, lon, alt_ft, 1)),
        "pos_nic0": df17(a, me_airborne_pos(lat, lon, alt_ft, 0, tc=18)),
        "velocity": df17(a, me_velocity(110, 225, -512)),
        "opstat_tabs_example": df17(a, me_opstatus_v2(nacp=9, sil=1, sda=1)),
        "opstat_no_integrity": df17(a, me_opstatus_v2(nacp=0, sil=0, sda=0)),
        "df4": df4(a, alt_ft),
        "df5": df5(a, "1200"),
        "df11": df11(a),
    }


def main(argv):
    if len(argv) == 2:
        print(check(argv[0], argv[1]))
        return 0
    if len(argv) == 1 and argv[0] in ("--examples", "-e"):
        for name, frame in example_frames().items():
            print(f"{name:22s} {frame}")
        return 0
    print("usage: modes_frame.py <hex frame> <VH mark>\n"
          "       modes_frame.py --examples", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
