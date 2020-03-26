
# Extending circuits with Walking Onions

When a client wants to extend a circuit, there are several
possibilities.  It might need to extend to an unknown relay with
specific properties.  It might need to extend to a particular relay
from which it has received a SNIP before.  In both cases, there are
changes to be made in the circuit extension process.

Further, there are changes we need to make for the handshake between
the extending relay and the target relay.  The target relay is no
longer told by the client which of its onion keys it should use.. so
the extending relay needs to tell the target relay which keys are in
the SNIP that the client is using.

## Modifying the EXTEND/CREATE handshake

First, we will require that proposal 249 (or some similar proposal
for wide CREATE and EXTEND cells) is in place, so that we can have
EXTEND cells larger than can fit in a single cell.  (See
other-proposals/xxx-wide-everything.txt for an example proposal to
supersede 249.)

We add new fields to the CREATE2 cell so that relays can send each
other more information without interfering with the client's part of
the handshake.

The CREATE2, CREATED2, and EXTENDED2 cells changes as follows:

      struct create2_body {
         // old fields
         u16 htype; // client handshake type
         u16 hlen; // client handshake length
         u8 hdata[hlen]; // client handshake data.

         // new fields
         u8 n_extensions;
         struct extension extension[n_extensions];
      }

      struct created2_body {
         // old fields
         u16 hlen;
         u8 hdata[hlen];

         // new fields
         u8 n_extensions;
         struct extension extension[n_extensions];
      }

      struct truncated_body {
         // old fields
         u8 errcode;
         // new fields
         u8 n_extensions;
         struct extension extension[n_extensions];
      }

      // EXTENDED2 cells can now use the same new fields as in the
      // created2 cell.

      struct extension {
         u16 type;
         u16 len;
         u8 body[len];
      }



Two extensions are defined by this proposal:

  [01] -- Partial_SNIPRouterData -- one or more fields from a SNIPRouterData
          that will be given to the client along with the relay's
          response to the CREATE2 cell.  (These fields are
          determined by the "forward_with_extend" field in the ENDIVE.)

  [02] -- Full_SNIP -- an entire SNIP that was used to extend the
          circuit.

  [03] -- Extra_SNIP -- an entire SNIP that was not used to extend
          the circuit, but which the client requested anyway.  This
          can be sent back from the extending relay when the client
          specifies multiple indices.

  [04] -- SNIP_Request -- a single byte, sent away from the client.
          If the byte is 0, the originator does not want a SNIP.  If
          the byte is 1, the originator does want a SNIP.  Other
          values are unspecified and SHOULD be ignored.

          By default, EXTENDED2 cells are sent with a SNIP iff the
          EXTENDED2 cell used a snip_index link specifier, and
          CREATED2 cells are not sent with a SNIP.


### New link specifiers

We add a new link specifier type [XX hex id here] for a router
index, using the following coding for its contents:

    /* Using trunnel syntax here. */
    struct snip_index {
        u16 index_id; // which index is it?
        u8 index[]; // extends to the end of the link specifier.
    }

The "index" field can be longer or shorter than the actual width of the
router index.  If it is too long, it is truncated.  If it is too short, it is
extended with zero-valued byte.

Any number of these link specifiers may appear in an EXTEND cell.
If there is more then one, then they should appear in order of
client preference; the extending relay may extend to any of the
listed routers.

This link specifier SHOULD NOT be used with IPv4, IPv6, RSA ID, or
Ed25519 ID link specifiers.  Relays receiving such a link along with
a snip_index link specifier SHOULD reject the entire EXTEND request.

> XXX I'm avoiding use of cbor for these types. Is that correct? I
>  think so, on the theory that there is no reason here, and we already use
>  trunnel-like objcts for this purpose.

## Modified ntor handshake

We adapt the ntor handsake from tor-spec.txt for this use, with the
following main changes.

  * The NODEID and KEYID fields are omitted from the input.
    Instead, these fields _may_ appear in a PartialSNIPData extension.

  * The NODEID and KEYID fields appear in the reply.

  * The NODEID field is extended to 32 bytes, and now holds the
    relay's ed25519 identity.

So the client's message is now:

   CLIENT_PK [32 bytes]

And the relay's reply is now:

   NODEID    [32 bytes]
   KEYID     [32 bytes]
   SERVER_PK [32 bytes]
   AUTH      [32 bytes]

otherwise, all fields are computed as described in tor-spec.

When this handshake is in use, keys are derived using SHAKE-128.


## New relay behavior on EXTEND and CREATE failure.

If an EXTEND2 cell based on an index fails, the relay should not
close the circuit, but should instead send back a TRUNCATED cell
containing the SNIP in an extension.

If a CREATE2 cell fails and a SNIP was requested, then instead of
sending a DESTROY cell, the relay SHOULD respond with a CREATED2
cell containing 0 bytes of handshake data, and the SNIP in an
extension.

>XXXX what do relays do here now?

## NIL handshake type

We introduce a new handshake type, "NIL".  The NIL handshake always
fails.  A client's part of the NIL handshake is an empty bytestring;
there is no server response that indicates success.

The NIL handshake can used by the client when it wants to fetch a
SNIP, without creating a circuit.

Upon receiving a request to extend with the NIL circuit type, a
relay SHOULD NOT actually open any connection or send any data to
the target relay.  Instead, it should respond with a TRUNCATED cell
with the SNIP(s) that the client requested in one or more Extra_SNIP
extensions.

## Relay behavior: responding to CREATE
XXX

## Relay behavior: responding to EXTEND
XXX


## Example Client operations: Extending by property and index.

XXXX

## Example Client operations: Extending to a relay with known SNIP

XXXX

## Example Client operations: Fetching a SNIP for a target index

XXXX


