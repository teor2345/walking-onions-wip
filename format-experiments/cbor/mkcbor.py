#!/usr/bin/python

import binascii
import cbor
import zlib

def b64(s):
    return binascii.a2b_base64(s+"============")

def b16(s):
    return binascii.a2b_hex(s)

ob1 = dict(
    ts= ( 1583177518, 3600 ),
    ed= b64("wLZer7fYj0h1xETBrhU2pGr9mIgGtdjIjQE8KNjEaqk"),
    ls= [ (1, b16("801f0022"), 9101) ,
          (2, b16("20010db80b0b00000000000000001281"), 9101) ] ,
    ok= b64("m/8ybC5sWqVCdXZkxGq1L084ZxC7p3E//xCbDxT0uFo"),
    sw= "Tor 0.4.3.3-alpha",
    pv = [ (1,1,2), (2,1,2), (3,1,2), (4,3,4), (5,1,2),
           (6,1,5), (7,1,1), (7,3,3), (8,1,2), (9,1,2) ],
    fm= b64("H+GXMtp3KrE7TV2eVOUgI5CzyvgHMxH805pu4UfrZXc"),
    cc=77,
    idx = (9, 0x9596eade, 0x95bcae65) )

enc = cbor.dumps(ob1)
print("result with string keys is {}".format(binascii.b2a_hex(enc)))
print("    ({} bytes long) {}".format(len(enc), type(enc)))
print("    compresses to {} bytes".format(len(zlib.compress(enc,9))))

ob2 = dict( enumerate(ob1.values()) )
print(ob2)
enc = cbor.dumps(ob2)
print("result with int keys is {}".format(binascii.b2a_hex(enc)))
print("    ({} bytes long) {}".format(len(enc), type(enc)))
print("    compresses to {} bytes".format(len(zlib.compress(enc,9))))


ob3 = [
    9, 0x9596eade, 0x95bcae65,
    1583177518, 3600,
    b64("wLZer7fYj0h1xETBrhU2pGr9mIgGtdjIjQE8KNjEaqk"),
    [ b16("01801f00229101"),
      b16("0220010db80b0b000000000000000012819101") ],
    b64("m/8ybC5sWqVCdXZkxGq1L084ZxC7p3E//xCbDxT0uFo"),
    "Tor 0.4.3.3-alpha",
    [ 1,1,2, 2,1,2, 3,1,2, 4,3,4, 5,1,2,
      6,1,5, 7,1,1, 7,3,3, 8,1,2, 9,1,2 ],
    { 1: b64("H+GXMtp3KrE7TV2eVOUgI5CzyvgHMxH805pu4UfrZXc"),
      2: 77 } ]

enc = cbor.dumps(ob3)
print("result with overtinyfication keys is {}".format(binascii.b2a_hex(enc)))
print("    ({} bytes long) {}".format(len(enc), type(enc)))
print("    compresses to {} bytes".format(len(zlib.compress(enc,9))))
