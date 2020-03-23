
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

## A CBOR-based metaformat for votes.

A vote is a signed document containing a number of sections; each
section corresponds roughly to a section of another document, a
description of how the vote is to be conducted, or both.

When a items in a vote corresponds to an element in a legacy vote,
that item is said to be a "legacy item".  Legacy items are in a
limited format, and contain a small set of tags indicating how they
are to be formatted.

    VoteDocument = [
        sig : [ + SingleSig ],
        lifetime : LifespanInfo,
        body : bstr .cbor VoteContent
    ]

    VoteContent = {
        voter : VoterSection,
        meta : MetaSection .within VoteableSection,
        root : RootSection .within VoteableSection,
        relays : RelaySection,
        indices : IndexSection,
        * tstr => any
    }

    VoterSection = {
        name : tstr,
        ? ul : [ *LinkSpec ]
        ? dl : [ *LinkSpec ],
        ? contact : tstr,
        cert : VoterCert,
        ? legacy-cert : tstr,
    }

    MetaSection = {
       * tstr => Voteable
    };

    RootSection = {
       * tstr => Voteable
    }

    RelaySection = {
       * bstr => RelayInfo .within VotingRule,
    }

    RelayInfo = [
       meta : RelayMetaInfo,
       snip : RelaySNIPInfo,
       ? legacy : RelayLegacyInfo,
    ]

    // ==========

    VoteableSection = {
        * tstr => Voteable
    }

    Voteable = [
       rule : VotingRule,
       content : any
    ]

    VotingRule = &(
       None          : 0,
       Special       : 1,
       Median        : 2,
       LowMode       : 3,
       HighMode      : 4,
       Intersect     : 5,
    )
    


XXX have to : make root document

XXXsay how to : vote.

XXX say how to : sign.

Kinds of voting rule: low-mode, high-mode, median.

xx "A foo is present if at least half of authorities vote on foo and
specify the same voting rule for it.  The value of the foo is
determined by that voting rule."

xx In endive need to vote on what the snips contents are, what the
adjunct data are, how each index works.  because of eliding, only
need to have rules for one data element per relay.  but if a new
data item is added in, what happens? does that get included or
excluded? let's say majority in both cases decide.

xx let's say that consensus method 100 is the first one for walking
onions


## Deriving older vote formats.


## Computing an ENDIVE.


## Managing indices over time.

XXXX

index groups could be fixed; that might be best at first. we could
reserve new methods for allocating new ones.



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


