
# Relay operations: Receiving and expanding ENDIVEs

Previously, we introduced a format for ENDIVEs to be transmitted
from authorities to relays.  To save on bandwidth, the relays
download diffs rather than entire ENDIVEs.  The ENDIVE format makes
several choices in order to make these diffs small: the Merkle tree
is omitted, and routing indices are not included directly.

To address these issues, this document describe the steps that a
relay needs to performs, upon receiving an ENDIVE document, to derive
all the SNIPs for that ENDIVE.

Here are the steps to be followed.  I'll describe them in order,
though in practice they could be pipelined somewhat.  I'll expand
further on each step later on.

  1. Compute routing indices positions,

  2. Compute truncated SNIPRouterData variations.

  3. Build signed SNIP data.

  4. Compute Merkle tree.

  5. Build authenticated SNIPs.

Below we'll specify specific algorithms for these steps.  Note that
relays do not need to follow the steps of these algorithms exactly,
but they MUST produce the same outputs as if they had followed them.

## Computing index positions.

For every IndexId in every Index Group, the relay will compute the
full routing index.  A routing index is a mapping from
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
(memcmp) order.  We define "predecessor" as the inverse of
"successor".

The algorithms here describe a set of invariants that are
"verified".  Relays SHOULD check each of these invariants;
authorities MUST NOT generate any ENDIVEs that violate them.  If a
relay encounters an ENDIVE that cannot be verified, then the ENDIVE
cannot be expended.

> XXXX should there be some way to define an index as a subset of another
> index, with elements weighted in different ways?

### Raw indices

When the IndexType is Indextype_Raw, then its members are listed
directly in the IndexSpec.

    Algorithm: Expanding a "Raw" indexspec.

    Let result_idx = {} (an empty mapping).

    Let previous_pos = indexspec.first_index

    For each element [i, pos2] of indexspec.index_ranges:

        Verify that i is a valid index into the list of ENDIVERouterData.

        Set pos1 = the successor of previous_pos.

        Verify that pos1 and pos2 have the same type, and that pos1
        <= pos2.

        Append the mapping (pos1, pos2) => i to result_idx

        Set previous_pos to pos2.

    Verify that previous_pos = the maximum value for the index type.

    Return result_idx.

### Raw numeric indices

If the IndexType is Indextype_RawNumreic, it is describe by a set of
spans on a 64-bit index range.

    Algorithm: Expanding a RawNumeric index.

    Let prev_pos = 0

    For each element [i, span] of indexspec.index_ranges:

        Verify that i is a valid index into the list of ENDIVERouterData.

        Let pos2 = prev_pos + span.

        Append the mapping (pos1, pos2) => i to result_idx

        Let prev_pos = pos2 + 1

    Verify that previous_pos = UINT32_MAX

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

    Let result_idx = {} (an empty mapping).

    Define POS(b) = FLOOR( (b << 32) / total_weight).

    For 0 <= i < LEN(indexspec.indexweights):

       Let w = indexspec.indexweights[i].

       Let lo = POS(total_so_far).

       Let total_so_far = total_so_far + w.

       Let hi = POS(total_so_far) - 1.

       Append (lo, hi) => i to result_idx.

    Return result_idx.

### Derived weighted indices

> XXXX We could possibly simplify weighted indices by specifying that one
> is derived from another by multiplying the weights by a vector of just a
> few possible multipliers.  eg, "0, Wge, Wme, Wbe" as possible multiples.

### Copying indices

> XXXX We could possibly want a way to say "these two indices are the same",
> here and in SNIPs.

### RSAId indices

If the IndexSpec type is Indextype_RSAId then the index is a set of
binary strings describing the routers' legacy RSA identities, for
use in the HSv2 hash ring.

These identities are truncated to a fixed length.  Though the SNIP
format allows variable-length binary prefixes, we do not use this
feature.

    Algorithm: Expanding an "RSAId" indexspec.

    Let R = [ ] (an empty list).

    Take the value n_bytes from the IndexSpec.

    For 0 <= b_idx < MIN( LEN(indexspec.members) * 8,
                          LEN(list of ENDIVERouterData) ):

       Let b = the b_idx'th bit of indexspec.members.

       If b is 1:
           Let m = the b_idx'th member of the ENDIVERouterData list.

           Verify that m has its RSAIdentityFingerprint set.

           Let pos = m.RSAIdentityFingerprint, truncated to n_bytes.

           Add (m, pos, b_idx) to the list R.

    Return INDEX_FROM_RING_KEYS(R).


    Sub-Algorithm: INDEX_FROM_RANGE_KEYS(R)

        # XXXX double-check that we are actually looking at the
        # right relay.  teor says that our algorithm is supposed to
        # use the hsdir at the the _next_ index on the ring, not the
        # _previous_ one. They are probably correct.

    First, sort R according to its 'pos' field.

    For each member (m, pos, idx) of the list R:

        Let key_low = pos

        If this is the last member of the list R:
            Let key_next = pos for the next member of R.

            Let key_high = the precessor of key_next.
        else:
            # XXXX this should wrap around, not stop at 0xfffff.
            # We should be clear about wrapping in snips.
            Let key_high = 0xFFFFFFFF...., truncated to n_bytes.

        If key_high >= key_low:
            Add (key_low, key_high) => idx to result_idx.

    Return result_idx.


### Ed25519 indices

If the IndexSpec type is Indextype_RSAId then the index is a set of
binary strings describing the routers' positions in a hash ring,
derived from their Ed25519 identity keys.

This algorithm is a generalization of the one used for hsv3 rings,
to be used to compute the hsv3 ring and other possible future
derivitives.

    Algorithm: Expanding an "Ed25519Id" indexspec.

    Let R = [ ] (an empty list).

    Take the values prefix, suffix, and n_bytes from the IndexSpec.

    Let H() be the digest algorithm specified by d_alg from the
    IndexSpec.

    For 0 <= b_idx < MIN( LEN(indexspec.members) * 8,
                          LEN(list of ENDIVERouterData) ):

       Let b = the b_idx'th bit of indexspec.members.

       If b is 1:
           Let m = the b_idx'th member of the ENDIVERouterData list.

           Let key = m's ed25519 identity key, as a 32-byte value.

           Compute pos = H(prefix || key || suffix)

           Truncate pos to n_bytes.

           Add (m, b_idx, pos) to the list R.

    Return INDEX_FROM_RING_KEYS(R).

### Building a SNIPLocation

After all the indices in an IndexGroups, they are combined into a series of
SNIPLocation objects. Each SNIPLocation should MUST contain all the IndexId
=> IndexRange entries that point to a given ENDIVERouterData, for the
IndexIds listed in an IndexGroup.

    Algorithm: Build a list of SNIPLocation from a set of routing indices.

    Initialize R as [ { } ] * LEN(relays)   (A list of empty maps)

    For each IndexId "ID" in the IndexGroup:

       Let router_idx be the index map calculated for ID.
       (This is what we computed previously.)

       For each entry ( (LO, HI) => idx) in router_idx:

          Let R[idx][ID] = (LO, HI).

SNIPLocation objects are thus organized in the order in which they will
appear in the Merkle tree: that is, sorted by the index of their
corresponding ENDIVERouterData.

Because SNIPLocation objects are signed, they must be encoded as "canonical"
cbor, according to section 3.9 of RFC 7049.

If R[idx] is {} (the empty map) for any given idx, then no SNIP will be
generated for the SNIPRouterData at that index for this index group.

## Computing truncated SNIPRouterData.

An index group can include an `omit_from_snips` field to indicate that
certain fields from a SNIPRouterData should not be included in the
SNIPs for that index group.

Since a SNIPRouterData needs to be signed, this process has to be be
deterministic.  Thus, the truncated SNIPRouterData should be computed by
removing the keys and values for EXACTLY the keys listed and no more.  The
remaining keys MUST be left in the same order that they appeared in the
original SNIPRouterData, and they MUST NOT be re-encoded.

(Two keys are "the same" if and only if they are integers encoding the same
value, or text strings with the same UT-8 content.)

There is no need to compute a SNIPRouterData when no SNIP is going to be
generated for a given router.

## Building the Merkle tree.

After computing a list of (SNIPLocation, SNIPRouterData) for every entry
in an index group, the relay needs to expand a Merkle tree to
authenticate every SNIP.

There are two steps here: First the relay generates the leaves, and then
it generates the intermediate hashes.

To generate the list of leaves for an index group, the relay first
removes all entries from the (SNIPLocation, SNIPRouterData) list that
have an empty index map.  The relay then puts `n_padding_entries` "nil"
entries at the end of the list.

To generate the list of leaves for the whole Merkle tree, the relay
concatenates these index group lists in the order in which they appear
in the ENDIVE, and pads the resulting list with "nil" entries until the
length of the list is a power of two: 2^`tree-depth` for some integer
`tree-depth`.  Let LEAF(IDX) denote the entry at position IDX in this
list, where IDX is a D-bit bitstring.  LEAF(IDX) is either a byte string
or nil.

The relay then recursively computes the hashes in the Merkle tree as
follows.  (Recall from that `H_node()` and `H_leaf()` are hashes taking
a bit-string PATH, a LIFESPAN and NONCE from the signature information,
and a variable-length string ITEM.)

    Recursive defintion: HM(PATH)

    Given PATH a bitstring of length no more than tree-depth.

    Define S:
        S(nil) = an all-0 string of the same length as the hash output.
        S(x) = x, for all other x.

    If LEN(PATH) = tree-depth:   (Leaf case.)
       If LEAF(PATH) = nil:
         HM(PATH) = nil.
       Else:
         HM(PATH) = H_node(PATH, LIFESPAN, NONCE, LEAF(PATH)).

    Else:
       Let LEFT = HM(PATH || 0)
       Let LIGHT = HM(PATH || 1)
       If LEFT = nil and RIGHT = nil:
           HM(PATH) = nil
       else:
           HM(PATH) = H_node(PATH, LIFESPAN, NONCE, S(LEFT) || S(RIGHT))

Note that entries aren't computed for "nil" leaves, or any node all of
whose children are "nil".  The "nil" entries only exist to place all
leaves at a constant depth, and to enable spacing out different sections
of the tree.

If `siganture-depth` from the ENDIVE is N, the relay does not need to
compute any merkle tree entries for PATHs of length greater than N bits.

## Assembling the SNIPs

Finally, the relay has computed a list of encoded (SNIPLocation,
RouterData) values, and a Merkle tree to authenticate them.  At this
point, the relay builds them into SNIPs, using the `sig_params` and
`signatures` from the ENDIVE.

    Algorithm: Building a SNIPSignature for a SNIP.

    Given a non-nil (SNIPLocation, RouterData) at leaf position PATH.

    Let SIG_IDX = PATH, truncated to signature-depth bits.
    Consider SIG_IDX as an integer.

    Let Sig = signatures[SIG_IDX] -- either the SingleSig or the MultiSig
    for this snip.

    Let HashPath = []   (an emtpy list).
    For bitlen = signature-depth+1 ... tree-depth-1:
        Let X = PATH, truncated to bitlen bits.
        Invert the final bit of PATH.
        Append HM(PATH) to HashPath.

    The SnipSignature's signature values is Sig, and its merkle_path is
    HashPath.

## Implementation considerations

A relay only needs to hold one set of SNIPs at a time: once one
ENDIVE's SNIPs have been extracted, then the SNIPs from the previous
ENDIVE can be discarded.

To save memory, a relay MAY store SNIPs to disk, and mmap them as
needed.
