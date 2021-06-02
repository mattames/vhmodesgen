#!/usr/bin/env python3
import argparse

# Copyright Matt Ames <matt.ames7bc@gmail.com>
# Copyright Matt Evans <matt@mattevans.email> https://github.com/Matty666/ - thanks for the complete re-write!

# Quick bit of Python to programmatically convert a Mode S address into an Austrailan VH- ICAO registration.
# Note the second and third characters count to 36 instead of 26.


def convert_to_base_36_char(value: int):
    return chr(value + 0x41) if value < 26 else chr(value + 0x30 - 26)


def convert_from_base_36_char(value: str):
    return ord(value) - 0x30 + 26 if ord(value) <= 0x39 else ord(value) - 0x41


def format_address(mode_s_address: int):
    return f"{hex(mode_s_address)[2:].upper()}"


def output_all_mode_s_addresses():
    for mode_s_address in range(0x7C0000, 0x7C822D):
        address = format_address(mode_s_address)

        print(f"{address}  {convert_to_vh(address)}")


def convert_to_mode_s(vh: str):
    if len(vh) == 6:
        l = convert_from_base_36_char(vh[3]) * (36 ** 2)
        m = convert_from_base_36_char(vh[4]) * 36
        r = convert_from_base_36_char(vh[5])
        return format_address((l + m + r) | 0x7C0000)
    return ""


def convert_to_vh(mode_s: str):
    address = int(mode_s, 16) & 0xFFFF
    r = address % 36
    m = (address // 36) % 36
    l = (address // 36) // 36
    return f"VH-{convert_to_base_36_char(l)}{convert_to_base_36_char(m)}{convert_to_base_36_char(r)}"


parser = argparse.ArgumentParser(description='Convert from mode s address to VH- ICAO registrations')
parser.add_argument("--vh", "-vh", action="store", dest="vh", help="Convert VH reg in format 'VH-XXX' to "
                                                                   "mode s address")
parser.add_argument("--mode-s", "-s", action="store", dest="mode_s", help="Convert mode s address in format "
                                                                          "'0x7CXXXX' to VH reg")
args = parser.parse_args()

if not args.vh and not args.mode_s:
    parser.print_help()
    exit(1)

if args.vh:
    vh = args.vh.upper()
    print(f"{vh} : {convert_to_mode_s(vh)}")

if args.mode_s:
    mode_s = args.mode_s.upper()
    print(f"{mode_s} : {convert_to_vh(mode_s)}")
