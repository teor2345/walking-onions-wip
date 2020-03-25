
# Introduction

Proposal 249 describes a system for create cells to become wider, in order to
accommodate hybrid crypto.  And in order to send those cell bodies across
circuits, it described a way to split CREATE cells into multiple EXTEND
cells.

But there are other cell types that can need to be wider. For example,
INTRODUCE and RENDEZVOUS cells also contain key material used for a
handshake: if they need to grow larger, then .

This proposal describes an encoding for arbitrary "wide" relay cells,
that can be used to send a wide variant of anything.

To be clear, I do not propose that wide cells should actually be _allowed_
for all relay cell types, but they can be extended as needed to support
whatever types need to be "wide".

# Proposal

We add a new relay cell type: RELAY_FRAGMENT.  This cell type contains part
of another relay cell.  A RELAY_FRAGEMENT cell can either introduce a new
fragmented cell, or can continue one that is already in progress.

The format of a RELAY_FRAGMENT body is one the following:

    struct fragment_begin {
       // What relay_command is in use for the underlying cell?
       u8 relay_command;
       // What will the total length of the cell be once it is reassembled?
       u16 total_len;
       // Bytes for the cell body
       u8 body[];
    }

    struct fragment_continued {
       // More bytes for the cell body.
       u8 body[];
    }

To send a fragmented cell, first a party sends a RELAY_FRAGMENT cell
containing a "fragment_begin" payload.  This payload describes the total
length of the cell, the relay command

Fragmented cells other than the last one in sequence MUST be sent full of
as much data as possible.  Parties SHOULD close a circuit if they receive a
non-full fragmented cell that is not the last fragment in a sequence.

Fragmented cells MUST NOT be interleaved with other relay cells on a circuit,
other than cells used for flow control. (Currently, this is only SENDME
cells.)  If any party receives any cell on a circuit, other than a flow
control cell or a RELAY_FRAGEMENT cell, before the fragmented cell is
complete, than it SHOULD close the circuit.

Parties MUST NOT send extra data in fragmented cells beyond the amount given
in the first 'total_len' field.

Not every relay command may be sent in a fragmented cell.  In this proposal,
we allow the following cell types to be fragmented: EXTEND2, EXTENDED2,
INTRODUCE1, INTRODUCE2, RENDEZVOUS.  Any party receiving a command that they
believe should not be fragmented should close the circuit.

Not all lengths up to 65535 are valid lengths for a fragmented cell.  Any
length under 499 bytes SHOULD cause the circuit to close, since that could
fit into a non-fragmented RELAY cell.  Parties SHOULD enforce maximum lengths
for cell types that they understand.

# Onion service concerns.

We allocate a new extension for use in the ESTABLISH_INTRO by onion services,
to indicate that they can receive a wide INTRODUCE2 cell.  This extension
contains:

        struct wide_intro2_ok {
          u16 max_len;
        }

# Compatibility

This proposal will require the allocation of a new 'Relay' protocol version,
to indicate understanding of the RELAY_FRAGMENTED command.

# Open questions

What should be done with Stream IDs here?  All of the types listed above take
a "0" Stream ID.

Should ESTABLISH_RENDEZVOUS cells have extensions to indicate that they
understand wide RENDEZVOUS cells?

