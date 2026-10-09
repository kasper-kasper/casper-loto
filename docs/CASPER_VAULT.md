# Casper Vault

Approved by the owner on 2026-10-09 (OD-049). One or three tickets per atomic purchase, 5,000 CAS each. Results and payout are settled on the server; opening the vault only presents the stored result.

| Prize CAS | Probability |
|---:|---:|
| 0 | 21.99% |
| 3,000 | 35% |
| 5,000 | 25% |
| 10,000 | 10% |
| 50,000 | 5% |
| 300,000 | 2% |
| 1,000,000 | 1% |
| 5,000,000 | 0.01% |

Independent uniform rolls 1–10,000. Any payout: 78.01%; payout above ticket price: 18.01%. Expected payout: 22,300 CAS, RTP 446%. This is the explicitly approved distribution, without an automatic economic adjustment. Ticket price is burned; prizes debit the existing Kasper Fund with paired immutable ledger entries. Insufficient Fund coverage rejects the entire purchase before creating tickets or moving money.

`casper-vault-v1` identifies stored tickets without a schema change. `instant-vault` separates idempotency keys from LIVE and Aurora. Replays validate owner and quantity. Separate history, account filter and administrative summary. Existing tickets and rules remain intact.

The player rotates the wheel through 540 degrees, opening five locks. Progress survives pauses. Pointer capture and viewport locking prevent the screen moving during interaction. Keyboard arrows and held Space/Enter provide alternatives. The immediate reveal button opens one or all remaining tickets. Reduced motion is supported. Unknown purchase failures retry the original key and quantity.

## Artwork

Built-in imagegen generated the production scene, encoded as WebP without composition edits. Asset: `frontend/miniapp/src/assets/lotteries/vault-treasury-v1.webp`. All text appears in its own dark area above the artwork.

Generation prompt:

> Production artwork for Casper Vault instant mobile lottery, cinematic premium realistic 3D render, landscape 3:2. A massive elegant gold and dark navy bank vault door in a luxurious underground treasury, large polished golden handwheel at center of thick circular vault door, sculpted locking bolts, machined brass and brushed metal, warm golden light spilling through subtle door gap, atmospheric volumetric lighting, architectural depth with restrained black marble and gold details, extremely polished tactile materials and realistic reflections. Entire central vault door and wheel clearly visible, symmetric impressive composition, golden glow contrasts dark blue background. No letters, no numbers, no text, no UI, no logo, no people, no currencies. Hero and catalogue asset for a premium game, not a UI mockup.
