#!/usr/bin/env python3

#for i in range(1, 33326):
i=0
for a in range(26):
    for b in range(26):
        for c in range(26):
            print(hex(i+8126464)[2:].zfill(2), [i], chr(a+65), chr(b+65), chr(c+65))
            i += 1

    

# 1-33325 
# 0x7C0000 (8126464) to (0x7C822D) 8159789