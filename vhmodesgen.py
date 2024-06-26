#!/usr/bin/env python3
import argparse

# Copyright Matt Ames <matt.ames7bc@gmail.com>
# Copyright Matt Evans <matt@mattevans.email> https://github.com/Matty666/ - thanks for the complete re-write!

# Quick bit of Python to programmatically convert a Mode S address into an Austrailan VH- ICAO registration.
# Note the second and third characters count to 36 instead of 26 - since this has been first published, it was
# discovered that this is due to CASA issuing registrations with numbers in them as well as letters, e.g. a
# valid callsign would be VH-X3V.

# Australian Mode S addresses are assigned the range 0x7C0000 to 0x7FFFFF 
# ref - https://www.icao.int/WACAF/Documents/Meetings/2023/Workshop-24-Bits/Guidelines%20for%20ICAO%2024%20Bits%20Adresses%20Assignment.pdf

# APPENDIX A - Table 9-1. Allocation of aircraft addresses to States 

# Australian bit mask - 0111 1––– –––– –––– –––– –––– 

# Range is 0x7C0000 to 0x7FFFF


# Some observed ranges are:-
# 7CF0xx - ground
# 7CF1xx - ???
# 7CF2xx - ???
# 7CF3xx - ground
# 7CF4xx - ground
# 7CF5xx - ground
# 7CF6xx - ground
# 7CF7CA - SSM1	TWR
# 7CF7CB - SSM2 TWR
# 7CF7CC - SSM3 TWR
# 7CF7CD - SSM4 TWR
# 7CF8xx - Military
# 7CF9xx - Military
# 7CFAxx - Military
# 7CFBxx - ???
# 7CFCxx - Gyrocopters seen in this range
# 7CFDxx - Gyrocopters seen in this range
# 7CFExx - ??
# 7CFFxx - ??
# 7D00xx - Gyrocopters seen in this range

# The address space goes into special characters at the following address, which is the start of the special / not assigned for registereed aircraft range:- 

# 7CB640  VH-:AA

# This special range then overflows back into the regular VH-AAA range here:-
# 7CD9B0  VH-AAA
# 7CFFFF  VH-HUP

# Some of the RAAus IDs:-
# 7CBBFE - R1722 - 19-1722
# 7CC3B7 - R8563 - 24-8563
# 7CC3EF - R8735 - 24-8735
# 7CC45C - R9081 - 23-9081
# 7CC502 - R8845 - 23-8845
# 7CC5EC - R7010 - 24-7010
# 7CC50F - R1675 - 23-1675
#
# Other random stuff:-
# 7CB647 - FLTDES1 - balloon of some type



def convert_to_base_36_char(value: int):
    return chr(value + 0x41) if value < 26 else chr(value + 0x30 - 26)


def convert_from_base_36_char(value: str):
    return ord(value) - 0x30 + 26 if ord(value) <= 0x39 else ord(value) - 0x41


def format_address(mode_s_address: int):
    return f"{hex(mode_s_address)[2:].upper()}"


def output_all_mode_s_addresses():
    for mode_s_address in range(0x7C0000, (0x7CFFFF + 1)):  # Upper limit was (0x7CF63F + 1)
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
parser.add_argument("--all", "-a", action="store_true", help="Output all mode s addresses")

try:
    args = parser.parse_args()
except:
    parser.print_help()
    exit(0)

if args.vh:
    vh = args.vh.upper()
    print(f"{vh} : {convert_to_mode_s(vh)}")

if args.mode_s:
    mode_s = args.mode_s.upper()
    print(f"{mode_s} : {convert_to_vh(mode_s)}")

if args.all:
    output_all_mode_s_addresses()
