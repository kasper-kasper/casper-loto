# Halloween replacement concepts — 2026-10-09

Status: final contract approved. Name Casper Halloween with an original decorative bat near the O; first pumpkin art direction; 3/28 in four rows of seven; price 6,666 CAS; exactly two matches pay 28,000 CAS, three share the jackpot under existing rules, one pays zero. Preserve existing 06:06/23:06 Moscow schedule, jackpot base and ×1/×5/×25 controls. Full audited refunds for purchased tickets in future uncompleted ГРОБ draws are explicitly authorized. No deletion of ticket or completed-draw history. Earlier alternatives below are retained only as concept history.

## Current repository rules

`GROB_RULES` uses 3 unique unordered numbers from 1–16, jackpot for 3 matches, fixed payouts 666 CAS for 1 match and 6,666 CAS for 2 matches. The declared schedule is 06:06 / 23:06 Europe/Moscow. These are repository rules, not a live-production audit of current administrative settings.

Uniform drawing gives C(16,3)=560 combinations. Proposed 3/31 gives C(31,3)=4,495 combinations, making a jackpot 8.03 times less likely per ticket. Proposed 4/31 gives C(31,4)=31,465, or 56.19 times less likely. These are per-ticket odds; jackpot frequency also depends on sales volume, duplicated selections and draw frequency. No forecast of time between jackpots is approved.

## Art directions

1. Тыквенная ночь: sculpted pumpkin lanterns, bronze and aubergine velvet, warm orange light. Friendly seasonal identity suited to a permanent festive collection.
2. Особняк полуночи: miniature Victorian mansion, amethyst mist, glowing windows and magical keys. Premium mystery without death imagery.
3. Лавка заклинаний: emerald potion, bronze cauldron, glass bottles and magical seals. A tactile playful workshop with potential for future thematic reveal animation.

The three images share the same proposed 3/31 interface for a fair visual comparison. Names, materials and scenes are alternatives. Money and draw timing are placeholders; the images do not define payouts, price or schedule. No coffins, graves or skulls.

## Proposed starting point, pending owner choice

Latest owner decision: implement 3/28, with 28 numbers in four rows of seven, and normal price / ×1 / ×5 / ×25 purchase controls. C(28,3)=3,276. Exactly two matches occur for 75 of 3,276 outcomes (2.2894%, approximately one in 43.68). Proposed prize: 28,000 CAS. Against the repository's original ticket price of 6,666 CAS, this is approximately 4.2 times the price and an expected two-match payout of 641.03 CAS per ticket (9.616% of that price). These are proposal calculations, not a live audit or approval of price/payout changes. One-match payouts, ticket price and schedule remain to be settled before release. The earlier 3/31 and 4/31 alternatives below are retained as concept history, not implementation instructions.

Consider 3/31 first rather than jumping to 4/31. Retaining payouts for any 1/2/3 matches would reduce the probability of some payout from 274/560 (48.93%) to 1,219/4,495 (27.12%). This is conditional on that payout structure being approved and does not predict payout size or profitability. Before approving price or prize tiers, calculate expected reserve use, jackpot contribution and payouts under observed sales-volume scenarios.

Final choice supersedes the earlier proposed alternatives: Casper Halloween, pumpkin art, 3/28, 6,666 CAS price, only the two-match 28,000 CAS category plus jackpot. Draw/reveal effects visualize immutable server outcomes, not select them.

Transition must introduce a versioned ruleset for future sales and draws. The owner now explicitly authorizes a full compensating refund for purchased tickets in future uncompleted ГРОБ draws before the new format starts. Preserve those tickets as REFUNDED and record every balance/fund movement in the immutable ledger plus an audit record. Completed draws and settled history remain immutable. Implementation needs migration, domain regression tests, full suite, locked backup/release and production health verification. Refund and format activation must be coordinated safely under locks; no standalone destructive cleanup.

## Implementation and artwork provenance

No schema change is needed; `python -m scripts.activate_halloween` explicitly orchestrates recovery and the audited financial transition in a stopped-service maintenance window rather than introducing a silent financial migration at startup. Use the configured existing Admin Panel identity with `is_admin`; no access rights change. The disposable PostgreSQL smoke verifies late-error rollback, concurrent idempotency, completed/settled history fingerprints, balanced refund pairs and purchase containing number 28.

Built-in imagegen generated `archive/reference/design-studies/halloween-concepts-2026-10-09/production-pumpkins.png` using the selected concept as a style reference. Production encoding with unchanged composition: `frontend/miniapp/src/assets/lotteries/halloween-pumpkins-v1.webp`. No fallback API or Batman logo. Genuine React controls render all prices, payouts and numbers.

Final generation prompt:

> Use the supplied image ONLY as an art direction reference for a new production artwork. Create a single landscape 3:2 illustration for the Casper Halloween lottery mobile game, premium polished cinematic 3D sculpted artwork. Recreate ONLY the wonderful scene portion: glowing carved orange pumpkin lanterns, friendly black cat with golden eyes, ornate polished bronze transparent lottery globe with purple and orange balls, deep aubergine velvet curtains, candlelight, autumn leaves, distant magical moonlit castle. Scene fills the entire image edge to edge. Large foreground pumpkin on left and golden lottery globe right, readable at 390px mobile size. Same warmth, luxury, rich texture and dimensionality as reference. NO app interface, NO numbers, NO lettering, NO words, NO brand logo, NO borders, NO price or buttons. No coffin, skulls, grave, crosses, horror, Batman logo. Beautiful independent artwork asset only.
