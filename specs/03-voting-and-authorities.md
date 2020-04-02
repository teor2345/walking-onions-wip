
# Directory authority operations

For Walking Onions to work, authorities must begin to generate
ENDIVEs as a new kind of "consensus document".  Since this format is
incompatible with the previous consensus document formats, and is
CBOR-based, a text-based voting protocol is no longer appropriate
for generating it.

We cannot immediately abandon the text-based consensus and
microdescriptor formats, however, but instead will need to keep
generating them for legacy relays and clients.  Ideally, the legacy
consensus should be a byproduct of the same voting process as is
used to produce ENDIVEs, to limit the amount of divergence in
contents.

Further, it would be good for the purposes of this proposal if we
can "inherit" as much as possible of our existing voting mechanism
rather than needing to re-specify it from scratch.

This section of the proposal will try to solve these goals by
defining a new binary-based voting format which can nonetheless be
used as an input to an the previous text-based consensus mechanism.

## Overview

Except as described below, we retain from Tor's existing voting
mechanism all notions of how votes are transferred and processed.
Other changes are likely desirable, but they are out of scope for
this proposal.

The principal changes in the voting that are relevant for legacy
consensus computation are:

  * The uploading process for votes now supports negotiation, so
    that the receiving authority can tell the uploading authority
    what kind of formats, diffs, and compression it supports.

  * We specify a CBOR-based binary format for votes, with a simple
    deterministic transformation to the legacy text format.  This
    transformation is meant for transitional use only; once all
    authorities support the binary format, the transitional format
    and its support structures can be abandoned.

  * To reduce complexity, the new vote format also includes
    _verbatim_ microdescriptors, whereas previously microdescriptors
    would have been referenced by hash.  (The use of diffs and
    compression should make the bandwidth impact of this addition
    negligible.)

For computing ENDIVEs, the principle changes in voting are:

  * The consensus outputs for most votable objects are specified in a
    way that does not require the authorities to understand their
    semantics when computing a consensus.  This should make it
    easier to change fields without requiring consensus methods.

## Negotiating vote uploads

Authorities supporting Walking Onions are required to support a new
resource "/tor/auth-vote-opts.txt".  This resource is a text document
containing a list of HTTP-style headers. Recognized headers are
described below; unrecognized headers MUST be ignored.

The *Accept-Encoding* follows the same as the header of the same
name; it indicates a list of Content-Encodings that the authority
will accept for uploads.  The gzip and identity encodings are
mandatory. (Default: "gzip, identity"

The *Accept-Vote-Diffs-From* header is a list of digests of previous
votes held by this authority; any new uploaded votes that are given
as diffs from one of these old votes SHOULD be accepted.  The format
is a space-separated list of "digestname:Hexdigest".  (Default: "".)

The *Accept-Vote-Formats* header is a space-separated list of the
vote formats that this router accepts. The recognized vote formats
are "legacy-3" (Tor's current vote format) and "endive-1" (the vote
format described here). Unrecognized vote formats MUST be ignored.
(Default: "legacy-3".)

If requesting "/tor/auth-vote-opts.txt" gives an error, or if one or
more headers missing, the default values should be used.  These
documents (or their absence) MAY be cached for up to 2 voting
periods.)

Authorities supporting Walking Onions SHOULD also support the
"Connection: keep-alive" and "Keep-Alive" HTTP headers, to avoid
needless reconnections in response to these requests.
Implementators SHOULD be aware of potential denial-of-service
attacks based on open HTTP connections, and mitigate them as
appropriate.

> Note: I thought about using OPTIONS here, but OPTIONS isn't quite
> right for this, since Accept-Vote-Diffs-From does not fit with its
> semantics.

## A generalized algorithm for voting

Unlike with previous versions of our voting specification, here I'm
going to try to describe pieces the voting algorithm in terms of
simpler voting operations.  Each voting operation will be named and
possibly parameterized, and data will frequently self-describe what
voting operation is to be used on it.

Voting operations may operate over different CBOR types, and are
themselves specified as CBOR objects.

A voting operation takes place over a given "voteable field".  Each
authority that specifies a value for a voteable field MUST specify
which voting operation to use for that field.  Specifying a voteable
field without a voting operation MUST be taken as specifying the
voting operation "None" -- that is, voting against a consensus.

On the other hand, an authority MAY specify a voting operations for
a field without casting any vote for it.  This means that the
authority has an opinion on how to reach a consensus about the
field, without having any preferred value for the field itself.

### Constants used with voting operations

Many voting operations may be parameterized by an unsigned integer.
In some cases the integers are constant, but in

When we encode these constants, we encode them as short strings
rather than as integers.


The following constants are defined:

`N_AUTH` -- the total number of authorities, including those whose votes
are absent.

`N_PRESENT` -- the total number of authorities whose votes are present for
this vote.

`N_FIELD` -- the total number of authorites whose votes for a given field are
present.

Necessarily, `N_FIELD` <= `N_PRESENT` <= `N_AUTH` -- you can't vote
on a field unless you've cast a vote, and you can't cast a vote
unless you're an authority.

`QUORUM_AUTH` -- The lowest integer that is greater than half of
`N_AUTH`.  Equivalent to CEIL( (N_AUTH+1)/2 ).

`QUORUM_PRESENT` -- The lowest integer that is greater than half of
`N_PRESENT`.  Equivalent to CEIL( (N_PRESENT+1)/2 ).

`QUORUM_FIELD` -- The lowest integer that is greater than half of
`N_FIELD`.  Equivalent to CEIL( (N_PRESENT+1)/2 ).

We define `SUPERQUORUM_`..., variants of these fields as well, based
on the lowest integer that is greater than 2/3 majority of the
underlying field.  `SUPERQUORUM_x` is thus equivalent to
CEIL( (N_x * 2 + 1) / 3 )

We need to encode these arguments; we do so as short strings.

    IntOpArgument = uint / "auth" / "present" / "field" /
         "qauth" / "qpresent" / "qfield" /
         "sqauth" / "sqpresent / "sqfield"

> I had thought of using negative integers here to encode these
> special constants, but that seems too error-prone.

> Alternatively, we could formulate QUORUM_x as CEIL( x / 2 + epsilon )
> and SUPERQUORUM_x as CEIL( x * 2/3 + epsilon), for epsilon being a
> tiny positive number.  Is that better?

### Producing consensus on a field

Each voting operation will either produce a CBOR output, or produce
no consensus.  Unless otherwise stated, all CBOR outputs are to be
given in canonical form.  To compute the consensus for a field, the
authorities follow this algorithm:

    Algorithm: CONSENSUS(OPERATION-VOTES, VOTES)

    (Computes a consensus on a field, given that the authorities
    casting votes have specified the voting operations in
    OPERATION-VOTES, and the authorities casting votes for this
    field)

    Requires: LEN(VOTES) <= LEN(OPERATION-VOTES).
    Requires: LEN(OPERATION-VOTES) <= N_PRESENT

    Identity the most frequent member OP of OPERATION-VOTES.  (Two
    members are the same iff they have exactly the same operation
    and parameters.)  If there is no unique most frequent member,
    return "no consensus" for this field.

    Let OP_COUNT = the number of times that OP appears in
    OPERATION-VOTES.

    If OP < QUORUM_AUTH, return "No consensus" for this field.

    Otherwise, invoke the operation specified by OP over the
    provided VOTES.

In other words, there is only a consensus for a field if more than
half of the total authorities agree how to vote on that field.

Below we specify a number of operations, and the parameters that
they take.  We begin with operations that apply to "simple" values
(integers and binary strings), then show how to compose them to
larger values.

Note that while some voting operations take other operations as
parameters, we are _not_ supporting full recursion here: there is a
strict hierarchy of operations, and more complex operations can only
have simpler operations in their parameters.


### Generic voting operations

#### None

This voting operation takes no parameters, and always produces "no
consensus".  It is encoded as:

    NoneOp = { op : "None" }

When encounting an unrecognized or nonconforming voting operation,
_or one which is not recognized by the consensus-method in use_, the
authorities proceed as if the operation had been "None".

### Voting operations for simple values

We define a "simple value" according to these cddl rules:

    SimpleVal = BasicVal / SimpleTupleVal
    BasicVal = boolean / int / bstr / tstr
    SimpleTuple = [ *BasicVal ]

We also need the ability to encode the types for these values:

    SimpleType = BasicType / SimpleTupleType
    BasicType = "bool" /  "uint" / "sint" / "bstr" ] / "tstr"
    SimpleTupleType = [ b"tuple", *BasicType ]

In other words, a SimpleVal is either an non-compound base value, or is
a tuple of such values.

We encode these operations as:

    SimpleOp = IntMedianOp / ModeOp / FirstWithOp / LastWithOp /
        BitThresholdOp / NoneOp

#### IntMedian

_Parameters_: MIN_VOTES (an integer)

Encoding:

    IntMedianOp = { op : "IntMedian", min : IntOpArgument }

Discard all non-integer votes.  If there are fewer than MIN_VOTES
votes remaining, return "no consensus".

Put the votes in ascending sorted order.  If the number of votes N
is odd, take the center vote (the one at position (N+1)/2).  If N is
even, take the lower of the two center votes (the one at position
N/2).

For example, the IntMedian of the votes ["String", 2, 111, 6] is 6.
The IntMedian of the votes ["String", 77, 9, 22, "String", 3] is 9.

#### Mode

_Parameters_: `MIN_COUNT` (an integer), `BREAK_TIES_LOW` (a boolean),
`TYPE` (a SimpleType)

    ModeOp = { op : "Mode",
               min : IntOpArgument,
               tie_low : boolean,
               type : SimpleType
    }

Discard all votes that are not of the specified type.  Of the
remaining votes, look for the value that has received the most
votes.  If no value has received at least `MIN_COUNTS` votes, then
return "no consensus".

If there is a single value that has received the most votes, return
it. Break ties in favor of lower values if `BREAK_TIES_LOW` is true,
and in favor of higher values of `BREAK_TIES_LOW` is false.
(Perform comparisons in canonical cbor order.)

#### FirstWith

_Parameters_: `MIN_COUNT` (an integer), `TYPE` (a SimpleType)

    ModeOp = { op : "FirstWith",
               min : IntOpArgument,
               type : SimpleType
    }

Discard all votes that are not of the specified TYPE.  Sort in
canonical cbor order.  Return the first element that received at
least MIN_COUNT votes.

#### LastWith

    ModeOp = { op : "LastWith",
               min : IntOpArgument,
               type : SimpleType
    }

As FirstWith, but return the last element that received at least
MIN_COUNT votes.

#### BitThreshold

Parameters: `LowerBound` (an integer >= 1)

    ModeOp = { op : "BitThreshold",
               lb : IntOpArgument,
    }

These are usually not needed, but are quite useful for
building some ProtoVer operations.

Discard all votes that are not of type uint or bstr; construe bstr
inputs as having type "biguint".

The output is a uint or biguint in which the b'th bit is set iff the
b'th bit is set in at least `LowerBound` of the votes.

### Voting operations for lists

These operations work on lists of SimpleVal:

    ListVal = [ * SimpleVal ]

    ListType = [ b"list",
                 [ *SimpleType ] / nil ]

They are encoded as:

    ListOp = SetJoinOp

#### SetJoin

Parameters: `LowBound` (an integer >= 1).
Optional parameters: `TYPE` (a SimpleType.)

Encoding:
    SetJoinOp = {
       op : "SetJoin",
       lb : IntOpArgument,
       ? type : SimpleType
    }

Discard all votes that are not lists.  From each vote,
discard all members that are not of type 'TYPE'.

For the consensus, construct a new list containing exactly those
elements that appears in at least `LowerBound` votes.

(Note that the input votes may contain duplicate elements.  These
must be treated as if there were no duplicates: the vote
[1, 1, 1, 1] is the same as the vote [1]. Implementations may want
to preprocess votes by discarding all but one instance of each
member.)

### Voting operations for maps

Map voting operations work over maps from key types to other non-map
types.

    MapVal = { * SimpleVal => ItemVal }
    ItemVal = ListVal / SimpleVal

    MapType = [ b"map", [ *SimpleType ] / nil, [ *ItemType ] / nil ]
    ItemType = ListType / SimpleType

They are encoded as:

    MapOp = MapJoinOp / MergeDerivedOp

#### MapJoin

Parameters:
   `KeyLowBound` (an integer >= 1)
   `KeyType` (a SimpleType type)
   `ItemOperation` (A non-MapJoin voting operation)

Encoding:

    MapJoinOp = {
       op : "MapJoin"
       key : SimpleType,
       keylb : IntOpArgument,
       item-op : ListOp / SimpleOp
    }

First, discard all votes that are not maps.  Then consider the set
of keys from each vote as if they were a list, and apply
`SetJoin[KeyLowBound,KeyType]` to those lists.  The resulting list
is a set of keys to consider including in the output map.

For each key in the output list, run the sub-voting operation
`ItemOperation` on the values it received in the votes.  Discard all
keys for which the outcome was "no consensus".

The final vote result is a map from the remaining keys to the values
produced by the voting operation.

#### StructJoin

    ; Encoding
    StructItemOp = ListOp / SimpleOp / MapJoinOp / DerivedItemOp

    VoteableStructKey = int / tstr

    StructJoinOp = {
        op : "StructJoin",
        key_rules : {
            * VoteableStructKey => StructItemOp,
        }
        ? unknown_rule : StructItemOp
    }

> xxxx write this up better, but the idea is that for each key, you
> apply the given StructItemOp.

#### DerivedFromField

    ;Encoding
    DerivedItemOp = {
        op : "DerivedFrom",
        fields : [ +SourceField ]
    }

    SourceField = [ FieldSource, VoteableStructKey ]
    FieldSource = "M" ; Meta
               / "CR" ; ClientRoot
               / "SR" ; ServerRoot
               / "RM" ; Relay-meta
               / "RL" ; Relay-legacy
               / "RS" ; Relay-SNIP

> xxxx write this up better, but the idea is that this field is
> derived from some other field, and so we should take the vote on
> _that_ field, and then look at the votes on this field which
> should be the same for everybody who voted on that field 'right'.
>
> Most stuff for relays is derived from published / relay-digest.

## A CBOR-based metaformat for votes.

A vote is a signed document containing a number of sections; each
section corresponds roughly to a section of another document, a
description of how the vote is to be conducted, or both.

When a items in a vote corresponds to an element in a legacy vote,
that item is said to be a "legacy item".  Legacy items are in a
limited format, and contain a small set of tags indicating how they
are to be formatted.

    ; VoteDocument is a top-level signed vote.
    VoteDocument = [
        sig : [ + SingleSig ],
        lifetime : Lifespan,
        body : bstr .cbor VoteContent
    ]

    VoteContent = {
       ; List of supportd consensus methods.
       consensus-methods : [ + uint ],

        ; How should the votes within the individual sections be
        ; computed?
        voting-rules : VotingRules,

        ; Information that the authority wants to share about this
        ; vote, which is not for voting.
        notes : NoteSection,

        ; Meta-information that the authorities vote on, which does
        ; not actually appear in the ENDIVE or consensus directory.
        meta : MetaSection .within VoteableSection,

        ; Fields that appear in the client root document.
        client-root : RootSection .within VoteableSection,
        ; Fields that appear in the server root document.
        server-root : RootSection .with VoteableSection,
        ; Information about each relay.
        relays : RelaySection,
        ; Information about indices.
        indices : IndexSection, 

        * tstr => any
    }

    ; Self-description of a voter.
    VoterSection = {
        ; human-memorable name
        name : tstr,

        ; List of link specifiers to use when uploading to this
        ; authority. (See proposal for dirport link specifier)
        ? ul : [ *LinkSpecifier ],

        ; List of link specifiers to use when downloading from this authority.
        ? dl : [ *LinkSpecifier ],

        ; contact information for this authority.
        ? contact : tstr,

        ; certificates tying this authority's long-term identity
        ; key(s) to the signing keys it's using to vote.
        certs : [ + VoterCert ] ,

        ; legacy certificate in format given by dir-spec.txt.
        ? legacy-cert : tstr,

        ; for extensions
        * tstr => any,
    }

    IndexSection = {
        IndexId => [ * IndexRule ],
    }

    IndexRule = int / tstr

    VoteableValue =  MapVal / ListVal / SimpleVal
    VoteableSection = {
       VoteableStructKey => VoteableValue,
    }

    ; the meta-section is voted on, but does not appear in the ENDIVE.
    MetaSection = {
       ; Seconds to allocate for voting and distributing signatures
       voting-delay: [ vote_seconds: uint, dist_seconds: uint ],
       ; Proposed time till next vote.
       voting-interval : uint,
       ; proposed lifetime for the SNIPs and endives
       snip_lifetime: Lifespan,
       ; proposed lifetime for client root document
       c_root_lifetime : Lifespan,
       ; proposed lifetime for server root document
       s_root_lifetime : Lifespan,
       ; Current and previous shared-random values
       ? cur-shared-rand : [ reveals : uint, rand : bstr ],
       ? prev-shared-rand : [ reveals : uint, rand : bstr ],
       ; extensions.
       * tstr => Voteable
    };

    SRCommit = [
       ver : uint,
       alg : tstr,
       ident : bstr,
       commit : bstr,
       ? reveal : bstr
    ]

    RootSection = {
       ? versions : [ * tstr ],
       ? require-protos : ProtoVersions,
       ? recommend-protos : ProtoVersions,
       ? params : NetParams,
       * tstr => Voteable
    }

    ; A NoteSection is used to convey information about the voter and
    ; its vote that is not actually voted on.
    NoteSection = {
       ; Information about the voter itself
       voter : VoterSection,
       ; Information that the voter used when assigning flags.
       ? flag-thresholds : { tstr => any },
       ; Headers from the bandwidth file that the
       ? bw-file-headers : {tstr => any },
       ? shared-rand-commit : SRCommit,
       * tstr => any
    }

    RelaySection = {
       * bstr => RelayInfo,
    }

    RelayInfo = [
       meta : RelayMetaInfo .within VoteableSection,
       snip : RelaySNIPInfo .within VoteableSection,
       ? legacy : RelayLegacyInfo  .within VoteableSection,,
    }

    ; XXXXXX
    RelayMetaInfo = nil
    RelaySNIPInfo = SNIPRouterData ; XXXX does this fit?

    ; XXXXX xxx i'm probably missing something here.
    RelayLegacyInfo = {
       nickname : tstr,
       flags : [ + tstr ],
       desc_digest : bstr,
       ? md_digests : [ + MDDigest ],
       ? md_literal : LiteralMD,
       published : tstr,
       protovers : ProtoVersions,
       ? ipv4-orport : [ bstr, uint ],
       ? ipv6-orport : [ bstr, uint ],
       ? dirport : uint,
       ? policy-summary : [ + tstr ],
       ? version : tstr,
       ? measured_weight : uint,
       ? unmeasured_weight : uint,
       * tstr => any,
    }

    LiteralMD = [ * MDLine ]
    MDLine = [ * MDLineElement ]
    MDLineElement = tstr / bstr   ;  xxxx tag bstr as hex or base64

    MDDigest = [
       low : uint,
       high : uint,
       digest : bstr .size 32
    ]

    ; ==========

    VotingRules = {
        meta : SectionRules,
        root : SectionRules,
        relay : RelayRules,
        indices : SectionRules,
     }

     SectionRules = {
        * VoteableKey => VotingOp
     }

     VotingOp = MapOp / ListOp / SimpleOp / UnknownOp

     UnknownOp = {
         op : tstr,
         * tstr => any
     }

     RelayRules = {
         meta : SectionRules,
         snip : SectionRules,
         legacy : SectionRules,
     }

## Computing a consensus.

To compute a consensus, the relays first verify that all the votes are
timely and correctly signed by real authorities.  If they have two
votes from an authority, they SHOULD issue a warning, and they
should take the one that is published more recently.

> XXXX Teor suggests that maybe we shouldn't warn about two votes
> from an authority for the same period, and we could instead have a
> more resilient process here.  Most interesting...

Next, the authorites determine the consensus method as they do today,
using the field "consensus-method".  This can also be expressed as
the voting operation
`LastWith[SUPERQUORUM_PRESENT, uint]`.

If there is no consensus for the consensus-method, then voting stops
without having produced a consensus.

Note that unlike the current voting algorithm, the consensus method
does not determine the way to vote on every individual field: that
aspect of voting is controlled by the voting-rules.  Instead, the
consensus-method changes other aspects of this voting, such as:

    * Adding, removing, or changing the semantics of voting
      operations.
    * Changing the set of documents to which voting operations apply.
    * Otherwise changing the rules that are set out in this
      document.

Once a consensus-method is decided, the next step is to compute the
consensus for other sections in this order: `meta`, `client-root`,
`server-root`, and `indices`.  The consensus for each is calculated
according to the operations given in the corresponding section of
VotingRules.

Next the authorities compute a consensus on the `relays` section,
which is done slightly differently, according to the rules of
RelayRules element of VotingRules.

Finally, the authorities transform the resulting sections into an
ENDIVE and a legacy consensus.

## Deriving older vote formats.

The data included in a VoteDocument can be used to reconstruct the
same data that would be present in a legacy vote, and therefore can
be used to compute legacy consensus documents for as long as they may
be needed.  Here we describe how to compute these contents.
XXXX
xxx

## Computing an ENDIVE.

xxx main idea here: decide what to include by voting on
sniprouterdata as we do on microdescriptors.  seems to provide easy
migration.

xxx alternative: vote on individual fields?

xxx give flags similar to how we do now

xxx define indices in terms of weights and flags

xxx weighting tweaks for different roles: ouch.  can anything be
done to make the complicated pile of formulas easier?  or do
authorities need to keep computing that ** post-vote** and feeding
it into the index calculations?  The post-vote part is what makes it
ugly here. If we could just have the vote do a median or something
we'd be in much better shape.

xxx could investigate if medians would work earlier based on formulas
and historical data?

## Managing indices over time.

XXXX

index groups could be fixed; that might be best at first. we could
reserve new methods for allocating new ones.

xxxx each index group gets a set of tags: must have all tags to be in the
group.  Additionally has set of weight/tag-set pairs: if you have
all tags in that set, you get multiplied by the weight.  allow
multiple possible source probabilities.

xxx oh hey that might work!

## Bandwidth analysis

## Analyzing voting rules

(of our past rule changes, which would have required alterations
here?)


## Other work

vote diffs?

compress before upload



    Line: key, series of tstr or bstr fields, then an optional (tag, bstr) pair?

    tstr goes in UTF-8. bstr goes in base64. separated by spaces. then
    begin/end foo...

    can't use dict since order matters.


