
# Relay operations: Receiving and expanding ENDIVEs

Previously, we introduced a format for ENDIVEs to be transmitted
from authorities to relays.  To save on bandwidth, the relays
download diffs rather than entire ENDIVEs.  The ENDIVE format makes
several choices in order to make these diffs small: the Merkle tree
is omitted, and routing indices are not included directly.

To address these issues, this describe the steps that a relay
needs to follow, upon receiving an ENDIVE document, to derive all
the SNIPs for that ENDIVE. 

Here are the steps to be followed.  I'll describe them in order,
though in practice they could be pipelined somewhat.  I'll expand
further on each step later on.

  1. Compute routing indices positions,

  2. Compute truncated SNIPRouterData variations.

  3. Build signed SNIP data.

  4. Compute Merkle tree.

  5. Build authenticated SNIPs.

## Computing index positions.

For every IndexId in every Index Group, the relay will compute the
full routing index.  A routing index is an ordered mapping from
index position ranges (represented as 2-tuples) to relays, where the
relays are represented as ENDIVERouterData members of the ENDIVE.  The
routing index must cover all possible values of the index.

An IndexSpec field describes how the index is to be constructed.
There are four kinds of IndexSpec: Raw, Weighted, RSAId, and
Ed25519Id.  We'll describe how to build the indices for each.

Every index may either have an integer key, or a binary-string
key. We define the "successor" of an integer index as
the succeeding integer.  We define the "successor" of a binary
string as the next binary string of the same length in lexical
(memcmp) order.

The algorithms here describe a set of invariants that are
"verified".  Relays SHOULD check each of these invariants;
authorities MUST NOT generate any ENDIVEs that violate them.  If a
relay encounters an ENDIVE that cannot be verified, then the ENDIVE
cannot be expended.

### Raw indices

When the IndexType is Idextype_Raw, then its members are listed
directly in the IndexSpec.

    Algorithm: Expanding a "Raw" indexspec.

    Let result_idx = {} (an empty ordered mapping).

    Let previous_pos = Nil.

    For each element [i, pos1, pos2] of indexspec.index_ranges:

        Verify that i is a valid index into the list of ENDIVERouterData.

        If previous_pos is Nil:
            Verify that pos1 is the minimum value for the index type.
        else:
            Verify that pos1 is the successor of previous_pos.

        Verify that pos1 and pos2 have the same type, and that pos1
        <= pos2.

        Append the mapping (pos1, pos2) => i to result_idx

        Set previous_pos to pos2.

    Verify that previous_pos = the maximum value for the index type.

    Return result_idx.

### Weighted indices

If the IndexSpec type is Indextype_Weighted, then the index is
described by assigning a probability weight to a number of relays.
From these, we compute a series of 64-bit index positions.

This algorithm uses 64-bit math, and 64-by-32-bit integer division.

It requires that the sum of weights is no more than UINT32_MAX.

    Algorithm: Expanding a "Weighted" indexspec.

    Let total_weight = SUM(indexspec.index_weights)

    Verify total_weight <= UINT32_MAX.

    Let total_so_far = 0.

    Let result_idx = {} (an empty ordered mapping).

    Define POS(b) = FLOOR( (b << 32) / total_weight).

    For 0 <= i < LEN(indexspec.indexweights):

       Let w = indexspec.indexweights[i].

       Let lo = POS(total_so_far).

       Let total_so_far = total_so_far + w.

       Let hi = POS(total_so_far) - 1.

       Append (lo, hi) => i to result_idx.

    Return result_idx.


### RSAId indices

If the IndexSpec type is Indextype_RSAId then the index is a set of
binary strings describing the routers' legacy RSA identities, for
use in the HSv2 hash ring.

These identities are truncated to a fixed length.  Though the SNIP
format allows variable-length binary prefixes, we do not use this
feature.

    Algorithm: Expanding an "RSAId" indexspec.

    Let R = [ ], an empty list.

    For 0 <= b_idx < MIN( LEN(indexspec.members) * 8,
                          LEN(list of ENDIVERouterData) ):

       Let b = the b_idx'th bit of indexspec.members.

       If b is 1:
           Let m = the b_idx'th member of the ENDIVERouterData list.

           Verify that m has its RSAIdentityFingerprint set.

           Add m to the list R.

    Sort R by RSAIdentityFingerprint in ascending order.

    For each member m of the list R:

        XXXX

### Ed25519 indices

XXXX


### Computing a SNIPLocation


## Computing truncated SNIPRouterData.

An index group can include an `omit_from_snips` field to indicate that
certain fields from a SNIPRouterData should not be included in the
SNIPs for that index group.

XXXX

## Building the Merkle tree.


## Implementation considerations

A relay only needs to hold one set of SNIPs at a time: once one
ENDIVE's SNIPs have been extracted, then the SNIPs from the previous
ENDIVE can be discarded.

To save memory, a relay MAY store SNIPs to disk, and mmap them as
needed.
