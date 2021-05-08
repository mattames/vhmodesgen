#!/usr/bin/env python3

# Copyright 2021 Matt Ames

# Quick bit of Python to programmatically convert a Mode S address into an Austrailan VH- ICAO registration.
# Note the second and third characters count to 36 instead of 26.

i=0x7C0000              # VH- Addresses begin at 0x7C0000
for a in range(26):
    for b in range(36):
        for c in range(36):
            if (b<26 and c<26):
                print(hex(i)[2:].upper().zfill(2), "VH-" + chr(a+65) + chr(b+65) + chr(c+65), a, b, c)
            i += 1