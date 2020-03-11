
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

Each SNIP has three pieces: the part of the SNIP that describes the
router; the part of that describes the SNIPs place within an ENDIVE, and
the part that authenticates the whole SNIP.

Why two _separate_ authenticated pieces?  Because (the router
description) one is taken verbatim from the ENDIVE, and the other
(the place within the ENDIVE) is computed from the ENDIVE by the
relays. Separating them like this helps ensure that the part
generated by the relay and the part generated by the authorities
can't interfere with each other.

    ; A SNIP, as it is sent from the relay to the client.  Note that
    ; this is represented as a three-element array.
    SNIP = [
        ; First comes the signature.  This is computed over
        ; the concatenation of the two binary strings below.
        auth: SNIPSignature,

        ; Next comes the location of the SNIP within the ENDIVE.
        index : encoded-cbor .cbor SNIPLocation,

        ; Finally comes the information about the router.
        router : encoded-cbor .cbor SNIPRouterData,
    ]

    ; encoded-cbor is defined in the CDDL postlude as a bstr that is
    ; tagged as holding verbatim CBOR:
    ;
    ;    encoded-cbor = #6.24(bstr)
    ;
    ; Using a tag like this helps tools that validate the string as
    ; valid CBOR; using a bstr helps indicate that the signed data
    ; should not be interpreted until after the signature is checked.


### SNIPRouterData: information about a single router.

Here we talk about the type that tells a client about a single
router.  For cases where we are just storing information about a
router (for example, when using it as a guard) we can remember
this part, and discard the other pieces.

The only required parts here are those that identify the router
and tell the client how to build a circuit through it.  The others
are all optional.  In practice, I expect they will be encoded in most
cases, but clients MUST behave properly if they are absent.

More than one SNIPRouterData may exist at a time for a single
router.  For example, there might be a longer version to represent
a router to be used as a guard, and another to represent the same
router when used as a hidden service directory.  (This is not
possible in the voting mechanism that I'm working on, but relays
and clients MUST NOT treat this as an error.)

This representation is based on the routerstats and
microdescriptor entries of today, but tries to omit a number of
obsolete fields, including RSA identity fingerprint, TAP key,
published time, etc.

XXXX I expect that we'll be making more changes to this type than
to any other type as we review and revise this design. It may turn
out to omit things that we need.

    ; A SNIPRouterData is a map from integer keys to values for
    ; those key.
    SNIPRouterData = {
        ; identity key.
        0 => Ed25519PublicKey,

        ; ntor onion key.
        1 => Curve25519PublicKey,

        ; list of link specifiers other than the identity key.
        ; If a client wants to extend to the same router later on,
        ; they SHOULD include all of these link specifiers verbatim,
        ; whether they recognize them or not.
        ? 2 => [ bstr ],

        ; The software that this relay says it is running.
        ? 3 => SoftwareDescription,

        ; protovers.
        ? 4 => ProtoVersions,

        ; Family.  See below for notes on dual encoding.
        ? 5 => [ * FamilyId ],

        ; Country Code
        ? 6 => Country,

        ; I don't know what I want to do here yet. XXXXX
        ? 7 => ExitPolicy,

        ; XXXX Properly speaking, there should be a CDDL 'cut'
        ; here, to indicate that the rules below sould only match
        ; if one if the previous rules hasn't matched.
        ; Unfortunately, my CDDL tool doesn't seem to support cuts.

        ; For future tor extensions.
        * int => any,

        ; For unofficial and experimental extensions.
        * tstr => any,
    };

    ; Ed25519 keys are 32 bytes, and that isn't changing.
    Ed25519PublicKey = bstr .size 32;

    ; Curve25519 keys are 32 bytes, and that isn't changing.
    Curve25519PublicKey = bstr .size 32;

    ; For future-proofing, we are allowing multiple ways to encode
    ; families.  One is as a list of other relays that are in your
    ; family.  One is as a list of authority-generated family
    ; identifiers. And one is as a master key for a family (as in
    ; Tor proposal 242).
    ;
    ; A client should consider two routers to be in the same
    ; family if they have at last one FamilyId in common.
    ; Authorities will canonicalize these lists.
    FamilyId = bstr;

    ; A country.  These should ordinarily be 2-character strings,
    ; but I don't want to enforce that.
    Country = tstr;

    ; SoftwareDescription replaces our old "version".
    SoftwareDescription = [
      software : tstr,
      version : tstr,
      ? extra : tstr
    ]

    ; Protocol versions: after a bit of experimentation, I think
    ; the most reasonable representation to use is a map from protocol
    ; ID to a bitmask of the supported versions.
    ProtoVersions = { ProtoId => ProtoBitmask };

    ; integer protocols are reserved for future version of Tor. tstr ids
    ; reserved for experimental and non-tor extensions.
    ProtoId = ProtoIdEnum / int / tstr;

    ProtoIdEnum = &(
      Link      : 0,
      LinkAuth  : 1,
      Relay     : 2,
      DirCache  : 3,
      HSDir     : 4,
      HSIntro   : 5,
      HSRend    : 6,
      Desc      : 7,
      MicroDesc : 8,
      Cons      : 9,
      Padding   : 10,
      FlowCtrl  : 11,
    )
    ProtoBitmask = uint / biguint;


    ; XXXX I've got to come back when I know what to do about exit
    ; policies.
    ExitPolicy = undefined;


### SNIPLocation: Locating a SNIP within an ENDIVE.

The SNIPLocation type can encode where a SNIP is located with
respect to one or more routing indices.  Note that it does not
need to be exhaustive: If a given IndexId is not listed for a
given relay in one SNIP, clients should not infer that no other
SNIPLocation for that relay exists.


    ; SNIPLocation: we're using a map here because it's natural
    ; to look up indices in maps.
    SNIPLocation = {
        ; A SNIP's location is given as a ranges in different
        ; indices.
        * IndexId => IndexRange,
        ; For experimental and extension use.
        * tstr => any,
    }

    ; We'll define the different index ranges as we go on with
    ; these specifications.
    IndexId = int;

    ; An index range extends from a minimum to a maximum value.  These
    ; ranges are _inclusive_ on both sides.  It is not allowed for 'hi'
    ; to be less than 'lo'.  A "nil" value indicates an empty
    ; range, which would not ordinarily be included.
    IndexRange = [ lo: IndexPos,
                   hi: IndexPos ] / nil;

    ; For most indices, the ranges are 4-byte integers.  But for
    ; hsdir rings, they are binary strings.
    IndexPos= uint / bstr;

### SNIPSignature: How to prove a SNIP is in the ENDIVE.

Here we describe the types for implementing SNIP signatures, to be
validated as described in "Design overview: Authentication" above.

    ; Most elements in a SNIPSignature are positional and fixed
    SNIPSignature = [
        ; The actual signature or signatures.
        SNIPSig / [ * SNIPSig ],

        ; algorithm to use for the path througbh the merkle tree.
        d_alg : DigestAlgorithm,
        ; Path through merkle tree, possibly empty.
        merkle_path : MerklePath ,

        ; Lifespan, in seconds since the epoch and in duration
        ; after that time.
        start-time: uint,
        lifetime: uint,

        ; optional nonce for hash algorithm.
        ? nonce : bstr,

        ; extensions for later use. These are not signed.
        extensions : { any => any },
    ];

    ; One signature on a SNIP.  If the signature is a threshold
    ; signature, or a reference to a signature in another
    ; document, there will probably be just one of these.  But if
    ; we're sticking a full multisignature in the document, this
    ; is the one to use.
    SNIPSig = [
       s_alg: SigningAlgorithm,
       signature : bstr,
       ; A prefix of the key or the key's digest, depending on the
       ; algorithm.
       ?keyid : bstr
    ];

    ; A Merkle path is represented as a sequence of bits to
    ; indicate whether we're going left or right, and a list of
    ; hashes for the parts of the tree that we aren't including.
    ;
    ; (It's safe to use a uint for the bits, since it will never
    ; overflow 64 bits.)
    MerklePath = [ uint, * bstr ];


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
        ; This is version 1.
        v : 1,
        ; optionally, a diff can say what different digests
        ; of the document should be before and after it is applied.
        ? digest : { DigestAlgorithm =>
                         [ pre : Digest,
                           post : Digest ]},

        ; optionally, a diff can give some information to identify
        ; which document it applies to, and what document you get
        ; from applying it.  These might be a tuple of a document type
        ; and a publication type.
        ? ident : [ pre : any, post : any ],

        ; list of commands to apply in order to the original document in
        ; order to get the transformed document
        cmds : [ *DiffCommand ],

        ; for future extension.
        * tstr : any,
    };

    ; There are currently only two diff commands.
    ; One is to copy some bytes from the original.
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
to that in which our current line-oriented code uses lines.  (See
example-code/cbor_diff.py for an example of doing this with Python's
difflib.)

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

    ; Enumeration for different signing algorithms.
    SigningAlgorithm = &(
       RSA-OAEP-SHA1   : 1,     ; deprecated.
       RSA-OAEP-SHA256 : 2,     ; deprecated.
       Ed25519         : 3,
       BLS             : 3,     ; Not yet standardized.

       ; XXX specify how references to other documents would be described.
    );
