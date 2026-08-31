# Game compatibility identity policy

Game-specific compatibility behavior should be selected from stable official
header identity whenever possible: publisher, hardware/color type, product ID,
and the actual revision bits. For WonderSwan `gameRev`, bit 7 controls internal
EEPROM write protection and is not part of the product revision.

A whole-ROM hash or header checksum identifies an exact byte-level ROM image.
It may be used to validate a known dump or official revision, but it must not be
the required enable condition for hardware compatibility behavior. Translation
patches, bug-fix patches, IPS/BPS patches and other non-hardware modifications
change content checksums without changing the hardware behavior the game needs.

Do not grow checksum whitelists for modified variants. If two official revisions
really require different behavior, distinguish them with the official revision
field and document the hardware evidence.

The One Piece compatibility path follows this policy through the shared
`isOnePieceGrandBattle()` helper. The BG palette/backdrop and custom OBJ code stay
separate, but both are enabled from the same helper result.
