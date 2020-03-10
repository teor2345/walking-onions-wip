
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

### Goals for our formats

We want SNIPs to be small, since they need to be sent on the wire
one at a time, and won't get much benefit from compression.  (To
avoid a side-channel, we want CREATED cells to all be the same
size, which means we need to pad up to the largest size possible
for a SNIP.)

We want to place as few demands on clients as possible, and we want to
preserve forward compatibility.

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
captures threshold signatures, multisignatures, and Merkle trees.
This will give us flexibility in our choice of authentication
mechanism over time.

The flexibility of this format is a
  * If we use Merkle trees, we can make ENDIVE diffs much much smaller,
    and save a bunch of authority CPU -- at the expense of requiring
    slightly larger SNIPs.

  * If Merkle tree root signatures are in SNIPs, SNIPs get a
    bit larger, but they can be used by clients that do not have the
    latest signed Merkle tree root.

  * If we use threshold signatures, we need to depend on
    not-yet-quite-standardized algorithms.  If we use multisignatures,
    then either SNIPs get bigger, or we need to put the signed Merkle
    tree roots into a consensus document.

Of course, flexibility in signature formats is risky, since the more
code paths there are, the more opportunities there are for nasty bugs.
With this in mind, I'm structuring our authentication so that there
should (to the extent possible) be only a single validation path for
different uses.

With this in mind, our format is structured so that "not using a
Merkle tree" is considered, from the client's point of view, the same as
"using a Merkle of depth 1".

The authentication on a single snip is structured, in the abstract, as:
   - ITEM: The item to be authenticated.
   - PATH: A list of N bits, representing a path through a Merkle tree from
     its root, where 0 indicates a left branch and 1 indicates a right
     branch.  (Note that in a left-leaning tree, the 0th leaf will have
     path 000..0, the 1st leaf will have path 000..1, and so on.)
   - BRANCH: A list of N digests, representing the branches in a Merkle tree
     that we are _not_ taking.
   - SIG: A generalized signature (either a threshold signature or a
     multisignature) of a top-level digest.
   - NONCE: an optional nonce for use with the hash functions.

We assume two hash functions here: `H_leaf()` to be used with leaf
items, and `H_node()` to be used with intermediate nodes.  These functions
are parameterized with a path through the tree, and with a nonce.

To validate the authentication on a SNIP, the client proceeds as follows:

    Algorithm: Validating SNIP authentication

    Let H = H_leaf(PATH, NONCE, ITEM).
    While N > 0:
       Remove the last bit of PATH; call it P.
       Remove the last digest of BRANCH; call it B.

       If P is zero:
           Let H = H_node(PATH, NONCE, H, B)
       else:
           Let H = H_node(PATH, NONCE, B, H)

       Let N = N - 1

    Check wither SIG is a correct (multi)signature over H with the
    correct key(s).

Parameterization on this structure is up to the authorities.  If N is
zero, then we are not using a Merkle tree.  The generalize signature
SIG can either be given as part of the SNIP, or as part of a consensus
document.  I expect that in practice, we will converge on a single set of
parameters here quickly (I'm favoring BLS signatures and a Merkle
tree), but using this format will give clients the flexibility to handle
other variations in the future.

### Design overview: how the formats work together

Authorities, as part of their current voting process, will produce an
ENDIVE.

Relays will download this ENDIVE (either directly or as a diff),
validate it, and extract SNIPs from it.  Extracting these SNIPs may be
trivial (if they are signed individually), or more complex (if they are
signed via a merkle tree, and the merkle tree needs to be
reconstructed).  This complexity is acceptable only to the extent that
it reduces diff size.

Once the SNIPs are reconstructed, relays will hold them, and serve them
to clients.

### What isn't in this document

This document doesn't tell you what the different routing indices are or
mean.  For now, we can imagine there being one index for guards, one for
middles, and one for exits, and one for each hidden service directory
ring.

This document doesn't give an algorithm for computing ENDIVEs from
votes.

## SNIPs

Each SNIP has three pieces: 

    ; A SNIP has three parts
    SNIP = [
        auth: snip-signature,
        index : bstr .cbor index-set,
        snip : bstr .cbor snip-core,
    ]


### SNIPCore: information about a single router.

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

Here is a binary format to be used with ENDIVEs and any other similar
binary formats.  Authorities and directory caches need to be able to
generate it; clients and non-cache relays only need to be able to parse
and apply it.

    ; Binary diff specification.
    BinaryDiff = {
        ; optionally, a diff can say what different digests
        ; of the document should be before and after it is applied.
        ? digest : { DigestAlgorithm =>
                         [ pre : Digest,
                           post : Digest ]},

        ; optionally, a diff can give some information to identify
        ; which document it applies to, and what document you get
        ; from applying it.  These might be a tuple of a document type
        ; and a publication type.
        ? ident : [ pre : any, post : any ]

        ; list of commands to apply in order to the original document in
        ; order to get the transformed document
        cmds : [ *DiffCommand ]

        ; for future extension.
        * tstr : any
    ]

    ; There are currently only two diff commands.  One is to copy
    ; some bytes from the original.
    DiffCommand = [
        OrigBytesCmdId,
        ; Range of bytes to copy from the original document.
        ; Ranges include their starting byte, but do not include their
        ; ending byte.
        start : uint,
        end : uint,
    ]

    ; The other diff comment is to insert some bytes from the diff.
    DiffCommand /= [
        InsertBytesCmdId,
        bytes : bstr,
    ]

    OrigBytesCmdId = 0
    InsertBytesCmdId = 1

Applying a binary diff is simple:

    Algorithm: applying a binary diff.

    (Given an input bytestring INP and a diff D, produces an output OUT.)

    Initialize OUT to an empty bytestring.

    For each command C in D.commands, in order:

        If C begins with OrigBytesCmdId:
            Append INP[C.start .. C.end] to OUT.

        else: # C begins with InsertBytesCmdId:
            Append C.bytes to OUT.

Generating a binary diff can be trickier, and is not specified here.
There are several generic algorithms out there for making binary diffs
between arbitrary byte sequences. Since these are complex, I recommend a
chunk-based CBOR-aware algorithm, using each CBOR item in a similar way
to that in which our current line-oriented code uses lines.

However, the diff format above should work equally well no matter what
diff algorithm is used.


## Managing indices over time.

## Storage analysis

## Bandwidth analysis

## Common CDDL items

    ; Enumeration to define integer equivalents for all the digest algorithms
    ; that Tor uses anywhere.  Note that some of these are not used in
    ; this spec, but are included so that we can use this production
    ; whenever we need to refer to a hash function.
    DigestAlgorithm = &(
        SHA1     : 1,     ; deprecated.
        SHA2-256 : 2,
        SHA2-512 : 3,
        SHA3-256 : 4,
        SHA3-512 : 5,
        Kangaroo12-256 : 6,
        Kangaroo12-512 : 7,
    )

    ; A digest is represented as a binary blob.
    Digest = bstr;
