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

Renderer correctness must not use game identity. The generic video core selects
the BG palette/backdrop path from the active WonderSwan hardware state. OBJ tile
readiness is recorded at the emulated frame boundary and tiles are published at
host VBlank; this is not proof of atomic OAM/tile/palette ownership. Product identity
may still be used by a diagnostic build to select trace targets, but not to decide
which hardware behavior is emulated.

Diagnostic selection chooses what to observe (trace scene, logical test name,
exact input SHA-256). Behavior selection chooses how the emulated hardware works.
Only the former may select a particular dump by hash. Do not add a ROM-hash
whitelist to enable the renderer or exclude a translation patch.
Private manifests should contain logical IDs and SHA-256, not local filenames,
paths, ROM bytes or saves; see [DevelopmentGuide.md](DevelopmentGuide.md).
