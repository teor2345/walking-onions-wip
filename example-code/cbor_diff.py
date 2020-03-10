#!/usr/bin/python3

#
# Example cbor-aware binary diff tool.  Note that using this with
# python's difflib is a bit overkill, since python's difflib knows how
# to avoid going quadratic pretty well.  Instead, this code is meant
# to show how to use cbor syntax to structure binary data into larger
# chunks that we can diff using a less efficient, more line-oriented
# algorithm.
#

import cbor2
import difflib

ORIG_BYTES = 0
INSERT_BYTES = 1

def apply_diff(inp, diff_str):

    diff = cbor2.loads(diff_str)

    out = []
    for c in diff['cmds']:
        if c[0] == ORIG_BYTES:
            start, end = c[1:]
            if not (0 <= start < len(inp)):
                raise ValueError()
            if not (start <= end <= len(inp)):
                raise ValueError()
            out.append(inp[start:end])
        elif c[0] == INSERT_BYTES:
            contents, = c[1:]
            out.append(contents)
        else:
            raise ValueError()

    return b"".join(out)


def extract_cbor_header(cbor):
    """Takes a cbor byte string, and returns a 3-tuple of major-type, value,
       and bytes consumed by encoding these."""

    b = cbor[0]
    major = b >> 5
    val = b & 0b11111
    itemlen = 1

    if val < 24:
        pass
    elif val <= 27:
        valbytes = 1<<(val-24)
        if len(cbor) < 1+valbytes:
            raise ValueError("truncated")
        val = int.from_bytes(cbor[1:1+valbytes], 'big')
        itemlen += valbytes
    elif val < 31:
        raise ValueError("reserved")
    else:
        assert val == 31
        if major in (2,3):
            # This is a header for an indefinite-length string.
            val = 0

    return (major, val, itemlen)


def tokenize_cbor(cbor, examine_data_items=False):

    while cbor:

        major, val, itemlen = extract_cbor_header(cbor)

        # Major values 0, 1, 7 don't have following content.
        # Major values 4 and 5 are followed by a series of cbor items.
        # Major value 6 is followed by a single cbor item.

        if major in (2, 3):
            # This is some kind of a string, and we are not analyzing
            # analyze its contents.
            if len(cbor) < itemlen + val:
                raise ValueError("truncated string")
            itemlen += val

        yield cbor[:itemlen]
        cbor = cbor[itemlen:]

        if major == 6 and value == 24 and examine_data_items:
            # This tag indicates that the next item should be a byte string,
            # and that the byte string in question should be encoded as cbor.

            major, val, itemlen = extract_cbor_header(cbor)
            if major != 2:
                # not a byte string.
                raise ValueError("Bad type after cbor tag")

            if val == 0:
                # This either an indefinite-leng item, or a zero-length
                # item.  Either way, we can't treat it as cbor.
                continue

            # Here we yield the "here comes a byte string" header, but not
            # the byte string as part of it.  We will treat that byte string
            # itself as candidate for cbor chunking.
            yield cbor[:itemlen]
            cbor = cbor[itemlen:]

def get_cbor_tokens(obj):
    try:
        return list(tokenize_cbor(obj, True))
    except ValueError:
        # Maybe we can recover by not analyzing inside binary objects?
        return list(tokenize_cbor(obj, False))

def make_diff(obj1, obj2):
    tok1 = get_cbor_tokens(obj1)
    tok2 = get_cbor_tokens(obj2)

    commands = []
    diff = {
        'cmds' : commands,
    }
    sm = difflib.SequenceMatcher(None, tok1, tok2)

    i_bytes_so_far = 0
    j_bytes_so_far = 0
    for opcode in sm.get_opcodes():
        op, i1, i2, j1, j2 = opcode

        i_bytes = sum(len(t) for t in tok1[i1:i2])
        j_bytes = sum(len(t) for t in tok2[j1:j2])
        if op in ('insert', 'replace'):
            commands.append([INSERT_BYTES,
                             obj2[j_bytes_so_far:j_bytes_so_far+j_bytes]])
        elif op == 'equal':
            # copy from the original.
            commands.append([ORIG_BYTES,
                             i_bytes_so_far,
                             i_bytes_so_far+i_bytes])
        else:
            assert op == 'delete'
            # don't have to do anything.

        i_bytes_so_far += i_bytes
        j_bytes_so_far += j_bytes

    return cbor2.dumps(diff)


if __name__ == '__main__':
    thing1 = [ "Hello world", [ "and hello", 2 ],
               { 'all' : 'your friends' } ]
    thing2 = [ "Hello world", [ "and hello", 4 ],
               { 'everybody' : 'here' },
               42 ]

    enc1 = cbor2.dumps(thing1)
    enc2 = cbor2.dumps(thing2)
    assert enc1 != enc2

    diff = make_diff(enc1, enc2)

    enc3 = apply_diff(enc1, diff)

    print("This works? The answer is", (enc2 == enc3))
