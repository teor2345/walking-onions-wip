#!/usr/bin/python3

import snip_pb2
import binascii

def b64(s):
    return binascii.a2b_base64(s+"=========")
def b16(s):
    return binascii.a2b_hex(s)

snip = snip_pb2.Snip()
snip.timestamp = 1583177518
snip.lifetime = 3600
snip.ed_id_key = b64("wLZer7fYj0h1xETBrhU2pGr9mIgGtdjIjQE8KNjEaqk")
snip.ntor_key = b64("m/8ybC5sWqVCdXZkxGq1L084ZxC7p3E//xCbDxT0uFo")

snip.linkspecs.append(b16("01801f00229101"))
snip.linkspecs.append(b16("0220010db80b0b000000000000000012819102"))

# Software version.
snip.software = "Tor 0.4.3.3-alpha"

def pv(n,lo,hi):
    pv = snip.protovers.add()
    pv.p = n
    pv.lo = lo
    pv.hi = hi

# Protovers
pv(1,1,2)
pv(2,1,2)
pv(3,1,2)
pv(4,3,4)
pv(4,1,2)
pv(6,1,5)
pv(7,1,1)
pv(7,3,3)
pv(8,1,2)
pv(9,1,2)

# family
snip.family = b64("H+GXMtp3KrE7TV2eVOUgI5CzyvgHMxH805pu4UfrZXc")

# country code
snip.cc = "de"

# Index.
snip.idxtype = 9
snip.idxlow = 0x9596eade
snip.idxhigh = 0x95bcae65

result = snip.SerializeToString()

print("result is: {}".format(binascii.b2a_base64(result)))

print("  {} bytes".format(len(result)))
