#!/usr/bin/env python3

i=0
for a in range(26):
    for b in range(36):
        for c in range(36):
            if (b<26 and c<26):
                print(hex(i+8126464)[2:].upper().zfill(2), "VH-" + chr(a+65) + chr(b+65) + chr(c+65), a, b, c)
            i += 1

    

# Note the second and third characters count to 36 instead of 26...