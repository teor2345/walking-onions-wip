
# Document Formats: ENDIVEs and SNIPs

Here we specify a pair of related document formats that we will
use for specifying SNIPs and ENDIVEs.

Recall from proposal 300 that a SNIP is a set of information about
a single relay, plus proof from the directory authorities that the
given relay occupies a given range in a certain routing index.
For example, we can imagine that a SNIP might say:

    * Relay X has the following IP, port, and onion key.
    * In the routing index Y, it occupies positions 0x20002
      through 0x23000.
    * This SNIP is valid on 2020-12-09 00:00:00, for one hour.
    * Here is a signature of all the above text, using a threshold
      signature algorithm.

You can think of a SNIP as a signed combination of a routerstatus,
a microdescriptor ... together with a little bit of the randomized
routing table from Tor's current path selection code, all wrapped
in a signature.

Every relay holds a set of SNIPs, and serves them to clients when
the client is extending by routing index.

An ENDIVE is a complete set of SNIPs.  Relays download ENDIVEs, or
diffs between ENDIVEs, once every voting period.  We'll explain
some ways below to make these diffs small, even though some of the
information in them (particularly SNIP signatures and index
ranges) will tend to change with every period.

## Preliminaries and scope

### Some goals for our formats

We want SNIPs to be small, since they need to be sent on the wire
one at a time, and won't get much benefit from compression.  (To
avoid a side-channel, we want CREATED cells to all be the same
size, which means we need to pad up to the largest size possible
for a SNIP.)

We want ENDIVEs to be compressible, and small.  If we can continue
getting benefit from diffs, we should.

We should preserve (or loosen) our policy of requiring only loose
time synchronization between clients and relays.

### Notes on Metaformat

In the format descriptions below, we will describe a set of
documents in the CBOR metaformat, as specified in RFC 7049.  If
you're not familiar with CBOR, you can think of it as a simple
binary version of JSON, optimized first for simplicity of
implementation and second for space.

I've chosen CBOR because it's schema-free (you can parse it
without knowing what it is), terse, dumpable as text, extensible,
standardized, and very easy to parse and encode.

We will choose to represent nearly everything as maps whose
whose keys are short integers: this is slightly shorter in its
encoding than string-based dictionaries.  (We could make things
even shorter by using arrays, but that would have future-proofing
implications.)

We'll use CDDL (defined in RFC 8610) to describe the data in a way
that can be validated -- and hopefully, in a way that will make it
comprehensible.

We make the following restrictions to CBOR documents that Tor
implementations will generate:

   * No floating-point values are permitted.

   * No tags are allowed unless otherwise specified.

   * All items must follow the rules of RFC 7049 section 3.9 for
     canonical encoding, unless otherwise specified.


Implementations SHOULD accept and parse documents that are not
generated according to these rules, for future extensibility.
However, implementations SHOULD reject documents that are not
well-formed and valid.

### Design overview: Authentication

I'm going to specify a flexible authentication format that
captures threshold signatures, multisignatures, and merkle trees.
This will give us flexibility in our choice of authentication
mechanism over timeXXX






We're going to keep the SNIP format extensible, on the theory that
clients are the hardest to change over time.  XXXXX


We need to specify for three levels of strictness:

1. When generating ENDIVEs, we need to specify down to the byte
what the output is, since all the directory authorities need to
generate the same bytes.

2. We'd like 

xxxx

### What isn't in this document

This document doesn't tell you what the different routing indices
are.


## SNIPs

    ; A SNIP has three parts
    SNIP = [
        sig: snip-signature signature,
        index : bstr .cbor index-set,
        snip : bstr .cbor snip-core,
    ]


### SNIPCore: the info about a single router.

Got to store what you need to finish extending to a router

Also got to store what you need to connect to the same router again.

Some kinds of SNIPs may need additional data.

I expect to revise this as we figure out the rest of the system.

Correpsonds roughly to routerstatus plus microdesc.

Hoping to omit now-obsolete fields.

    ; blah
    snip-core = {
        id : ed25519-public,
        ntor : curve25519-public,
        ? ls : [ bstr ],
        ? sw : [ tstr, tstr ],
        ? pv : protovers,
        ? fam : [ ed25519-public ],
        ? cc : country,
        ; exit-policy ??xxxx
        ; flags ??xxxx
    }
    ; xxxx use integer IDs

    ed25519-public = bstr .size 32;
    curve25519-public = bstr .size 32;
    country = tstr .size 2;

    protover = { proto-id => proto-bitmask };
    proto-id = &(
        Link : 1,
        Relay : 2,
        ; ... xxxx
    )
    proto-bitmask = uint / bstr;

### SNIPIndex: What to tell a client about a router

Identify which index

Identify low and high range

    ; blah

    index-set = {
        ts : timestamp,
        lt : lifetime,
        * index-id => range,
        * str => any
    }

    timestamp = uint;
    lifetime = uint;

    index-id = int;
    range = [ lo: index-pos,
              hi: index-pos ]

    index-pos = uint / bstr;


### SNIPSignature: How to prove a SNIP is in the endive.

Timestamp, lifetime, and [sig/multisig], hashpath.

Let's come up with some may to make each relay ratchet on the timestamps so
we can make the lifetime long.

    ; SNIPSignature

    snip-signature = {
        ? 1 => SNIPSigningAlgorithm,
        ? 2 => SNIPDigestAlgorithm,
        ? 3 => SNIPKeyID / [ SNIPKeyID ],
        ? 4 => SNIPSig / [ SNIPSig ],
        ? 5 => MerklePath,
        int => any,
    }

    SNIPKeyID = bstr;
    SNIPSig = bstr;
    MerklePath = [ bstr ];

    SNIPSigningAlgorithm = &(
       ed25519-multi : 1,
       bls : 2,
    );

    SNIPDigestAlgorithm = &(
       sha2-256 : 0,
       sha3-256 : 1,
       kangaroo12-256 : 2,
    );

## ENDIVEs: sending a bunch of SNIPs efficiently.

Don't need to include hashpaths, just root.

Don't need to include index ranges, just build instructions for them.

ENDIVE becomes a bunch of Snip+SnipIndex+SnipSignaure

## Root documents

Do not need to be up-to-date to use network!!!

Let lifetime on these be long-ish.

Mostly same stuff as current header/footer of consensus.


## ENDIVE diffs

x use standard diff algorithm, chunking on cbor lexical items, synchonizing
  on bytestreams that represent ed keys.  Output has to be byte-oriented
  instead of line-oriented

    ; Define a generic diff type for binary files.
    Diff = {
        version : int,
        digest : [ alg: DigAlg, pre:bstr, post:bstr, ],
        commands : [* Command ],
        * int : any,
    }

    DigAlg = "SHA2-256" / "SHA2-512" / "SHA3-256" / "SHA3-512" / "Kangaroo12-256"

    OrigBytes = 0
    InsertBytes = 1

Command = [ OrigBytes, start: uint, end: uint ] / [ InsertBytes, bstr ]

## Managing indices over time.

## Storage analysis

## Bandwidth analysis

