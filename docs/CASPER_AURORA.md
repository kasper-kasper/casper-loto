# Casper Aurora

Owner-approved 2026-10-09 (OD-048). Mini App instant game, one or three tickets per atomic purchase. Each ticket costs 3,000 CAS. No scheduled draw or auto-play. Result and ledger settlement happen on the server at purchase; holding a crystal or revealing all tickets only presents the stored result.

| Prize CAS | Probability |
|---:|---:|
| 0 | 60% |
| 2,000 | 20% |
| 3,000 | 10% |
| 6,000 | 7% |
| 25,000 | 2.8% |
| 200,000 | 0.19% |
| 1,000,000 | 0.01% |

Independent uniform rolls 1–10,000; expected payout 2,300 CAS. Ticket cost is burned, prizes are paid from the existing Kasper Fund with paired immutable ledger entries. `casper-aurora-v1` distinguishes stored tickets from LIVE v1 without changing the table schema or completed history. Separate idempotency namespace, owner and quantity replay checks. Separate history and Admin summary.

The 1.6-second hold supports pause/resume, pointer capture, viewport lock, keyboard holding and reduced motion. A shared reveal button opens the remaining tickets without purchasing again. Uncertain network purchases retry the original key and quantity.

## Artwork

Built-in imagegen generated the production scene, encoded as WebP without changing its composition. Repository asset: `frontend/miniapp/src/assets/lotteries/aurora-crystal-v1.webp`. Text is rendered in a separate dark block above the image following the owner's readability correction.

Generation prompt:

> Production raster art for Casper Aurora instant lottery mobile game, stylized premium 3D cinematic rendering. Landscape 3:2 composition, one magnificent large faceted translucent icy crystal standing on a circular frozen obsidian ice pedestal in foreground, cyan turquoise violet light shining from crystal interior, arctic fantasy landscape with distant icy mountain peaks and vivid northern lights ribbons across deep violet night sky, reflections on frozen lake, fine frosted crystal facets, luxurious atmospheric depth, luminous attractive and legible at small thumbnail size, center crystal fully visible with generous breathing room, richer teal and purple with warm subtle magical sparkle highlights. No letters, no numbers, no logo, no UI, no price, no border, no people. This is actual game hero and catalogue artwork, polished dimensional materials, not a mockup.
