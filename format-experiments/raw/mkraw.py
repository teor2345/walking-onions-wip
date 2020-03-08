#!/usr/bin/python

import struct
import binascii

elts = []

def add32(n):
    elts.append(struct.pack("!L", n))
def add16(n):
    elts.append(struct.pack("!H", n))
def add8(n):
    elts.append(struct.pack("!B", n))
def addBase64(s):
    elts.append(binascii.a2b_base64(s+"=========="))
def addStr(s):
    elts.append(s.encode("UTF-8") + b"\0")

# timestamp
add32(1583177518)
# lifetime
add16(3600)
# ed key
addBase64("wLZer7fYj0h1xETBrhU2pGr9mIgGtdjIjQE8KNjEaqk")
# linkspecs: v4
add32(0x801f0022)
add16(9101)
# linkspecx: v6
add16(0x2001)
add16(0xdb8)
add16(0xb0b)
add16(0)
add16(0)
add16(0)
add16(0)
add16(0x1281)
add16(9101)

# onion key
addBase64("m/8ybC5sWqVCdXZkxGq1L084ZxC7p3E//xCbDxT0uFo")

# Software version.
addStr("Tor 0.4.3.3-alpha")

# Protovers
add8(1)
add16(1)
add16(2)

add8(2)
add16(1)
add16(2)

add8(3)
add16(1)
add16(2)

add8(4)
add16(3)
add16(4)

add8(5)
add16(1)
add16(2)

add8(6)
add16(1)
add16(5)

add8(7)
add16(1)
add16(1)

add8(7)
add16(3)
add16(3)

add8(8)
add16(1)
add16(2)

add8(9)
add16(1)
add16(2)

add8(0)

# family
addBase64("H+GXMtp3KrE7TV2eVOUgI5CzyvgHMxH805pu4UfrZXc")

# country code
add16(77) # assume this is DE

# Index.
add16(9)
add32(0x9596eade)
add32(0x95bcae65)


result = b"".join(elts)

print("result is: {}".format(binascii.b2a_base64(result)))

print("  {} bytes".format(len(result)))
