
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

## Primitives for voting

Unlike with previous versions of our voting specification, here I'm
going to try to describe pieces the voting algorithm in terms of simpler
voting operations.  Each voting operation will be named, and data will
frequently self-describe what voting operation is to be used on it.

A voting operation takes place over a "voteable field".  Each voteable
field will have a distinct identity within a given context.  For each
voteable field, each authority may vote at most once.  The vote for a
field may be an integer, a boolean, a binary string, a text string.  The
vote for a field may also be a list of integers, booleans, binary
strings, text strings, or nil.

Voting operations may be implicit, in which case they are specified
here, or explicit, in which case they are specified in the vote.

Each voting operation will either produce an output or a lack of
consensus.

Unless otherwise specified, there is no consensus for a voting operation
unless more than half of the authorities have voted on the field.  There
is also no consensus if the voting operation for the field is explicit,
and fewer than half of the authorities have agreed on the same voting
operation.

Individual voting operations are listed below.  In the descriptions
below, "more than half" is to be interpreted strictly: "more than half
of two" for example, means "at least 1", not "one or more".

Voting operations may be parameterized by an integer.

The following constants are defined:

`N_AUTH` -- the total number of authorities, including those whose votes
are absent.

`N_PRESENT` -- the total number of authorities whose votes are present for
this vote.

`N_FIELD` -- the total number of authorites who votes for a given field are
present.

`QUORUM_AUTH` -- The lowest integer that is greater than half of
`N_AUTH`.  Equivalent to CEIL( (N_AUTH+1)/2 ).

`QUORUM_PRESENT` -- The lowest integer that is greater than half of
`N_PRESENT`.  Equivalent to CEIL( (N_PRESENT+1)/2 ).

`QUORUM_FIELD` -- The lowest integer that is greater than half of
`N_FIELD`.  Equivalent to CEIL( (N_PRESENT+1)/2 ).


### IntMedian [N]

Discard all non-Integer votes.  To take the 'median' of a set of N
integer votes, first put them in ascending sorted order.  If N is odd,
take the center vote (the one at position (N+1)/2).  If N is even, take
the lower of the two center votes (the one at position N/2).

For example, the IntMedian of the votes ["String", 2, 111, 6] is 6.
The IntMedian of the votes ["String", 77, 9, 22, "String", 3] is 9.

If the parameter N is provided, then there must be at least N votes or there
is no consensus.

### FirstMode [N]

Discard all votes that are not booleans, integers, byte strings, or text
strings. Find the most frequent value in the votes.  If there is a tie,
break ties in favor of lower values.  (Sort by cbor canonical order.)

If the parameter N is provided, then the mode must be listed in at least N
votes or there is no consensus.

### LastMode [N]

As FirstMode, but break ties in favor of higher values.

### FirstWith [N]

Discard all votes that are not booleans, integers, byte strings, or text
strings. Sort in canonical cbor order.  Return the first element
that is listed in at least N votes.

### LastWith [N]

Discard all votes that are not booleans, integers, byte strings, or text
strings. Sort in canonical cbor order.  Return the final element
that is listed in at least N votes.

### IntMean [N]

Discard all non-Integer votes.  To take the integer 'mean' of a set of N
integer votes, compute FLOOR(SUM(votes)/N).

For example, the IntMean of [7, 99, 11, 6, 9] is 26.

If the parameter N is provided, then there must be at least N votes or there
is no consensus.

### SetJoin [N]

Discard all votes that are not lists.  From each list, remove values
that are not booleans, integers, byte strings, or text strings.

To take the "SetJoin[N]" of the resulting lists, construct a list
containing exactly those elements that are listed in N or more of the of
the input lists, once each.  Sort this list in canonical cbor order.

Note that if N=1, then this operation is equivalent to a set union.

### Special

If a voting operation is described as "Special", then any field
using it is generated in some field-specific way.  This is only
usable for fields whose voting operations are specified in this
document.

### None

The voting operation "None" never produces a consensus.


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

    ; XXXX I need to decide what to do with VoteableSection. In my
    ;   original design, all voteable objects were self-describing,
    ;   but we need to decide whether that makes sense.

    VoteContent = {
        ; Information about the voter itself
        voter : VoterSection,
        ; Meta-information that the authorities vote on, which does
        ; not actually appear in the ENDIVE or consensus directory.
        meta : MetaSection .within VoteableSection,
        ; Fields that appear in the client root document.
        client-root : RootSection .within VoteableSection,
        ; Fields that appear in the server root document.
        server-root : RootSection .within VoteableSection,
        ; Information that the authority wants to share about this
        ; vote, which is not for voting.
        notes : NoteSection,
        ; Information about each relay.
        relays : RelaySection,
        ; Information about indices.
        indices : IndexSection,
        * tstr => any
    }

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

    ; XXXX
    IndexSection = nil

    ; XXXX nonconformant with VoteableSection XXX
    MetaSection = {
       ; List of supportd consensus methods.
       consensus-methods : [ + uint ],
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
       ?shared-rand-commit : SRCommit,
       ; Parameters used for voting only.
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

    NoteSection = {
       flag-thresholds : { tstr => any },
       bw-file-headers : {tstr => any },
       * tstr => any
    }
    RelaySection = {
       * bstr => RelayInfo .within VotingRule,
    }

    RelayInfo = [
       meta : RelayMetaInfo,
       snip : RelaySNIPInfo,
       ? legacy : RelayLegacyInfo,
    ]

    ; XXXXXX
    RelayMetaInfo = nil
    RelaySNIPInfo = nil

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
       ? weight : {
          bw : uint,
          ? measured : bool,
          ? unmeasured : bool
       },
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

    VoteableSection = {
        * tstr => Voteable
    }

    Voteable = [
       rule : VotingRule / [ VotingRule, uint ],
       content : any
    ]

    VotingRule = &(
       None          : 0,
       Special       : 1,
       IntMedian     : 2,
       LowMode       : 3,
       HighMode      : 4,
       FirstWith     : 5,
       LastWith      : 6,
       IntMean       : 7,
       SetJoin       : 8,
    )




Kinds of voting rule: low-mode, high-mode, median.

xx In endive need to vote on what the snips contents are, what the
adjunct data are, how each index works.  because of eliding, only
need to have rules for one data element per relay.  but if a new
data item is added in, what happens? does that get included or
excluded? let's say majority in both cases decide.

xx let's say that consensus method 100 is the first one for walking
onions


## Deriving older vote formats.

The data included in a VoteDocument can be used to reconstruct the
same data that would be present in a legacy vote, and therefore can
be used to compute legacy consensus documents for as long as they may
be needed.  Here we describe how to compute these contents.

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


