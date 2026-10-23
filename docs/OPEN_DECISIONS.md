# Open decisions

| ID | Topic | Status | Decision |
|---|---|---|---|
| OD-077 | Casper Mini permanent draw lottery | Approved, local only — 2026-10-21 | Owner specifies independent Mini (mini / casper_mini_6_30), Classic label, six unique unordered numbers from 1–30, 10,000 CAS, daily 10:30/19:15 Europe/Moscow, 20m base jackpot, 40% (4,000 CAS per ticket), 100 tickets per purchase and 500 per player per draw. Exact fixed gross prizes for 2/3/4/5 matches: 10k/30k/140k/1m; six matches share Mini jackpot with existing 6/36 carryover, remainder and reset rules. Existing cutoff, random/quick purchases, prepaid five-draw purchases, settlement, refunds, notifications and statistics remain shared. Total 100-ticket purchase cap includes all five draws. Green/cream/gold reference-inspired picker, receipt and classic broadcast. Exclude Mini gameplay from achievements; actual wallet balance remains accurate. No changes to old history, economic epoch or production; no VPS publication authorized for this request. See docs/CASPER_MINI.md. |
| OD-076 | Achievement production publication and delayed activation | Published and scheduled — 2026-10-21 | Owner authorizes completing release preparation, full checks, backups, publication of 93 approved achievements and the profile/collection, then automatic activation around 02:00 Europe/Moscow on 21 October (23:00 UTC on 20 October). API/bot 1.58.1, Mini App 1.68.0 and schema 0065 published; full restored production migration, finance/history fingerprints, Linux smokes, public hashes/auth and monitoring pass. Schedule armed only after health gates, rechecked at 01:04 Moscow: disabled/unstarted, 93 definitions, zero awards/unlocks/local fixture users. Final NOWAIT barrier regression and full backend 908 tests pass; busy gameplay causes immediate deferral rather than a lock wait. Prepared runtime/schedule is unchanged across the patch. Durable server schedule requires no notebook. No local database, visual fixture awards or test users transferred. Preserve all balances, tickets, draw history and epoch; initialize achievement baseline once at actual activation. Keep cases planned/hidden and approved rewards unchanged. Details: docs/achievements/ACHIEVEMENTS_PRODUCTION_RELEASE_2026-10-21.md. |
| OD-075 | Legendary achievements, fixed final collection and cosmetics | Approved and implemented locally — 2026-10-20 | Owner approves ten jackpot awards excluding Dual, raises all CAS with 40m floor, 100–500 matching-game gifts and 20–100 ordinary future cases. Delegated allocation: 40m–350m CAS. Confirms final name «Каспер, подвинься»; fixed ten-code set, 1bn CAS, 300 gifts of each of those ten games, 200 ordinary future cases (upper permitted option), exclusive platinum/gold badge and «За гранью» theme. No legendary cases. CASE inventory/opening stays future; gold profile theme unlocks once with first legendary and applies only by choice. Three thousand final gifts use compact entitlements and one-ticket ledger transactions, current caps, purchase occupancy, future-draw waiting and protection against complete outcome coverage. No 300-unit reduction needed: minimum outcome space 1365. Add sparse collection ownership/selections and migration 0064; preserve previous categories, immutable history and launch epoch. Local catalogue 93; no VPS/GitHub publication. Reports and exact table in docs/achievements/ACHIEVEMENTS_LEGENDARY_LOCAL_REPORT.md and ACHIEVEMENTS_LEGENDARY_REWARDS.md. |
| OD-074 | Local folder organization and future GitHub publication | Cleanup approved and completed locally; publication not requested — 2026-10-20 | Owner authorizes local archiving of unused materials and grouping documentation. Keep active runtime/dependencies, secrets, backups and financial history intact. Archive retired media and one-off evidence locally; maintain legacy Web reference sources, exclude all archive content from VPS/Docker release. Achievement docs/catalogues now docs/achievements. Git history is not rewritten; no remote/commit/push or VPS deployment performed. GitHub visibility, repository destination and any public licence remain owner choices for a future publication; recommend private first. Preliminary secret/history audit and remaining clean-commit/full-suite/achievement-CI database requirements are recorded in docs/GITHUB_READINESS.md. |
| OD-073 | First epic achievements and approved rewards | Approved, implemented locally — 2026-10-20 | Owner approves all 17 entries and interpretations; raises CAS to 3m–8m, 20m for 100k paid tickets, and ten Grand tickets for five adjacent winning draws. Announced case distribution: four planned cases on 15 entries, one each on Big Collection and Human Orchestra. Final totals 98,500,000 CAS, 165 gifts, 62 planned cases. Local catalogue now 82 entries. Combined Dual result filter, bounded five-draw projection and revision-3 post-launch initialization; preserve existing categories, original epoch, immutable history and award snapshots. Cases remain planned only; no production publication. See docs/achievements/ACHIEVEMENTS_EPIC_PROPOSAL.md and docs/achievements/ACHIEVEMENTS_EPIC_LOCAL_REPORT.md. |
| OD-072 | First rare achievements and funded rewards | Approved and implemented locally — 2026-10-20 | Owner approves all 20 rare entries, rewards and interpretations, then raises CAS range to 400k–900k. Final allocation: 12,300,000 CAS, 80 gift tickets/cards, ten planned cases; docs/achievements/ACHIEVEMENTS_RARE_PROPOSAL.md. CODE is exactly four matching positions of five, with no new cipher mechanic. Bell means confirmed Casper Ball. PULSE permits either cipher outcome; repeat results count distinct paid tickets, including within one draw. Activity remains common 3 distinct, uncommon 7 consecutive/14 distinct, rare 21 consecutive/30 distinct. Extended sparse draw counts and bounded length-three winning series, daily FAST mask, full-card Bingo ≤40; one-time post-launch projection revision 2. Report: docs/achievements/ACHIEVEMENTS_RARE_LOCAL_REPORT.md. No production publication. |
| OD-071 | First uncommon achievements and funded reward packs | Approved and implemented locally — 2026-10-20 | Owner approves all 23 uncommon achievements, stated condition interpretations, 100k–300k CAS allocation, 3–5 ticket packs, Grand/Bingo/matching 6/36 gifts and planned cases; confirms Bell means Casper Ball. Final additions: September x3 for calendar flip, Grand x1 for Rich, PLL x2 for Little by little. Total 3,575,000 CAS, 50 tickets/cards, eight planned one-case rewards. Grand explicitly overrides prior daily-only gifts for this batch. Packs retain one idempotent funded part per ticket; Bingo uses standard pool inventory. Source epoch and common awards/rewards remain intact. Conditions/table: docs/achievements/ACHIEVEMENTS_UNCOMMON_PROPOSAL.md; implementation and necessary checks: docs/achievements/ACHIEVEMENTS_UNCOMMON_LOCAL_REPORT.md. No production publication. |
| OD-070 | Achievement badge artwork and rarity palette | Approved, local only — 2026-10-20 | Owner approves the first direction «Контур с характером» for the 22 common achievements and delegates rarity colours. Common uses silver-lilac, uncommon mint, rare blue, epic violet, legendary gold. Secret remains an independent visibility flag; locked secret artwork and threshold marks stay hidden. Update presentation consistently in profile/catalog/details/notices without rewriting immutable awards or changing rewards. No production publication. |
| OD-069 | Common achievement rewards and gift tickets | Approved, local only — 2026-10-20 | Owner approves the proposed 22-row reward table: 930,000 CAS total, eight specific automatic daily-draw tickets, four planned one-case rewards. CAS and ticket sponsorship come from Kasper Fund with immutable ledger accounting. Tickets receive a gift icon/label and random combinations for the nearest eligible open draw; no FAST, instant or weekly Grand gifts. Gift tickets and their results do not satisfy paid-only common conditions. Cases are catalog metadata only, with no inventory, opening or delivery until separately implemented. No production activation or historical payouts authorized. Resolves OD-066/068 amounts and funding for this batch only. |
| OD-068 | First common achievements and profile | Approved, local only — 2026-10-19 | Owner approves exactly 22 supplied common achievements, compact balance/profile summary, full category/filter/detail screen and in-app notices. Custom games are 3 September, 2:22 and Halloween (september/pll/grob). Only events since the achievement launch boundary count. Owner explicitly reiterates local-only implementation; CAS amounts, funding and production launch remain unapproved. Supersedes OD-066's earlier exclusion of a product catalog and final UI for this first batch only. |
| OD-048 | Casper Aurora instant lottery | Approved 2026-10-09 | Separate Aurora crystal game, same instant settlement and 1/3-ticket purchases as LIVE; hold each crystal with resumable progress or reveal the entire batch immediately. Price 3,000 CAS. Independent prizes: 0 at 60%, 2,000 at 20%, 3,000 at 10%, 6,000 at 7%, 25,000 at 2.8%, 200,000 at 0.19%, 1,000,000 at 0.01%. Any payout 40%, profit above ticket price 10%; expected payout 2,300 CAS / 76.6667%. Approved existing instant funding: burn ticket cost, prizes paid from Kasper Fund through ledger; separate versioned game history, no draw or auto-play. Aurora atmospheric northern-lights design approved; implementation and publication authorized with necessary checks. |
| OD-047 | Casper Grand flagship release | Approved 2026-10-09 | Grand Hall first concept, brighter lions and tactile number selection, animated dimensional draw without video, no enlarged catalogue positioning. Fixed prizes per ticket: 2+1=50k, 2+2=50k, 3+0=100k, 3+1=200k, 3+2=300k, 4+0=500k, 4+1=1m, 4+2=3m, 5+0=10m, 5+1=20m CAS; 5+2 shares jackpot. Supersedes Grand percentage categories in OD-015 for new snapshots. Keep 50k price, 5/35+2/5, Sunday 20:00 Moscow, 5bn base jackpot and existing Fund coverage. Owner explicitly authorizes immediate activation and full ledgered refunds of all 145 purchased future Grand tickets at original prices (4,865,000 CAS), preserving REFUNDED tickets and completed history. |
| OD-046 | Casper Halloween replaces ГРОБ | Approved — 2026-10-09 | Owner approves Casper Halloween (English name, original bat decoration around the O), first pumpkin art direction, 3 unique unordered numbers from 1–28, four rows of seven, ticket price 6,666 CAS, 28,000 CAS only for exactly two matches, no payout for one match, jackpot for three under existing sharing/funding rules; ordinary ×1/×5/×25 random purchases remain. Retain existing 06:06/23:06 Moscow schedule and jackpot base. Explicit full refunds for purchased tickets in future uncompleted ГРОБ draws during transition: preserve REFUNDED rows and create compensating ledger/audit records. Completed draws and settled tickets remain immutable; due old-format draws recover chronologically before activation. No history deletion. Publish after required checks and backup under operations lock. |
| OD-045 | Compact Mini App catalogue and festive collection | Approved 2026-10-09 | Owner selects the two-column visual grid and authorizes All / Instant / Draw / Festive filters. Add current ГРОБ to Festive now, overlapping with Draw and All; retain name, artwork and mechanics until a separate redesign. Festive games are intended to remain available year-round; no new games, seasonal availability rules or economic changes are approved here. Reuse existing game artwork with dimensional presentation; no mandatory featured Grand banner. |
| OD-044 | Platform content events B without visual layer | Approved 2026-10-06 | Exact B1.1–B1.4/B2.1/B3.1–B3.5/B4.1–B4.8 requested registry; automatic B1, B2.1, B3.5; all other B3/B4 draft only. Count winning tickets, include instant tickets in purchase/win totals but exclude instant draws/jackpots. B1.3 continues every 500k after 1m. Configurable thresholds and durable dedupe. Extend existing Publication drafts; no B visuals, texts, channel delivery or C/D. Owner later changes future shared automatic pacing to 30 minutes, no daily cap, manual bypass without shifting automatic clock. Keep A and B separate; one-draw A and per-scan B groups. A detector/dispatcher were not yet present in repository; this phase establishes shared nonvisual event foundation. See archive/reference/retired-publications/docs/PUBLICATION_EVENTS_B.md. |
| OD-043 | Remaining draw-game atmospheric art and instant exclusion | Approved 2026-10-06 | Add two newly generated full scenes each for Casper Grand (imperial architecture), 2:22 (night/mystery), Casper Ball (gala interiors/terrace), ГРОБ (gothic landscapes). Owner explicitly corrects replacement to addition: retain all previous draw-game templates. Fast and previously supplied art are preserved. Exclude LIVE and instant games from selectable publications, without changing the lottery itself or prior snapshots. Paired editable Stories/posts, no channel sends or automatic event rules in this release. Supersedes earlier LIVE publication inclusion in OD-035/039. |
| OD-042 | Casper Dual owner-only publication library | Approved 2026-10-06 | Replace all prior active Dual templates with the five supplied owner day/night scenes; paired Story/Post layouts, all five available for existing A labels. Remove old choices while preserving immutable saved artwork snapshots. Other lotteries unchanged; no new automatic policy or channel send. |
| OD-041 | Additional Fast owner artwork | Approved 2026-10-05 | Add six attachments in displayed order: first two CODE (shadow), next two FLASH, last two PULSE. Two new paired Story/Post scenes per game; retain previous collections. Exclusive game assignment and existing A event labels; no automatic publication policy or channel send change. |
| OD-040 | Casper Bingo template replacement | Approved 2026-10-05 | Replace all old Bingo choices with ten owner-supplied emerald/gold scenes. Use every scene, paired Stories/posts, including jackpot and jackpotless-series events. All ten fit and are reusable across existing A labels, so none are surplus. Remove old choices from active catalog while preserving saved snapshot artwork/history; other games unchanged. No new automatic publication rule or channel send authorized by this artwork change. |
| OD-039 | Block A automation/editorial policy | Partially approved; delivery details pending | Owner approves automatic A1 and A4, A2/A3 proposals with accept/reject, A5 proposals Monday/Wednesday/Friday at the 12:22 scan, manual A8; include Fast jackpots and support suitable Fast/LIVE summaries. Check events daily at 12:22, 18:35 and 22:22 Europe/Moscow; publish automatic events immediately after each scan without spacing/cap, merge one-draw events and publish different draws separately; inclusive per-draw ticket milestones 10k/50k/100k/500k/1m (no cumulative-sales A4.5), individual jackpot milestones; series news every 50 consecutive jackpotless completed draws, every 200 for Fast; factual metrics and current-format record scope. Never publish winner names/usernames. Combine same-draw events, allow multiple images, random suitable artwork excluding the last 3 images and last 2 texts within game/topic, oldest-used fallback when choices are scarce, plus manual override. Old events over 48h become proposals; no duplicate successful sends. Mini App Stories expire after 24h, unseen first, seen muted/last; Telegram channel posts remain. Native Telegram Stories excluded. Final hashtag statement adopts visible game/topic plus general footer tags under spoiler. Text bank is provisional and templates still being completed. A4.3 participant-record news requires both at least 500 unique participants per draw and at least 20% growth over the previous record. The definition of separate A4.4 activity remains open. Owner reconfirms delivery formats and same-draw grouping; these are approved, not open questions. See docs/publications/block-a/README.md; no automatic delivery enabled yet. |
| OD-038 | Atmospheric publication art and channel test | Approved 2026-10-05 | Add ten supplied autumn landscapes exclusively for 3 СЕНТЯБРЯ, preserving previous libraries. Owner prefers complete atmospheric scenes with depth and place as the visual direction, rather than repeating an isolated decorative object. Paired Stories/posts, Admin and Mini App remain current product scope. One explicitly marked test photo post to @casper_loto is authorized; permanent delivery and automatic A policies remain deferred. |
| OD-037 | Block A owner artwork and pending automatic policies | Visual addition approved 2026-10-05; automation open | Add nine owner-supplied compositions exclusively for 6/36 (`khan`), with paired story/post layouts and all old templates preserved. Current delivery scope is Admin + Mini App; post export remains available, channel delivery stays disabled. Nine artworks are reusable editorial choices for existing 32 A labels; metadata does not determine event eligibility. Before automation, owner must decide enabled A1/A2/A3/A4/A5/A8 scenarios, thresholds, statistical definitions and record comparison periods, A1/A5 overlap and winner privacy, moderation, daily/event processing timing, delay and quiet hours, publication limits/priority, missed-event recovery and historical backfill, artwork rotation and fallback, authoritative text/data sources, CTA targets during pauses, lifetime and archive policy. B/C/D remain outside the current scope. |
| OD-036 | Manual publications and channel destination | Manual scope approved 2026-10-05; automatic policies deferred | Owner authorizes Admin editor and Mini App Stories now, explicitly postponing every automatic publication rule until template selection is complete. Implement server drafts, explicit publish/archive, game-specific CTA and paired preview/export; no event detectors, scheduler jobs, automatic expiry or channel sends. Existing bot @Kasper_loto_bot has verified post/edit rights in owner-created @casper_loto (chat_id -1003771983357); destination is saved, delivery remains disabled. Automatic conditions, timing, eligibility, frequency, lifetime, duplicate events and channel deep links are future decisions. Templates can be added later; existing content/assets are snapshotted. |
| OD-035 | Lottery-specific publication library category A | Visual scope approved 2026-10-05; business policies deferred | Owner requests only A1/A2/A3/A4/A5/A8, inheriting each lottery's existing identity, 9:16 Stories and 4:3 Posts, varied compositions and permanent game-specific Story CTA. No A6/A7, new-game launch, standalone brand/service/seasonal work or publication engine. All 32 subcategories covered for draw games; incompatible draw/jackpot scenarios excluded for instant Casper LIVE. Real copy, milestone thresholds, event eligibility, timing, record comparison scope, duplicate-event handling, channel and final deep-link resolver remain undecided; design metadata does not activate business rules. |
| OD-034 | Mini App stories and Telegram channel publications | Partially resolved — design study 2026-10-04 | Owner selects compact rectangular news covers above the nearest-draw card and requests ten classic universal designs, each for story and channel post, without event-specific assignment. Product scope is Mini App plus Telegram channel; player Web excluded. design/publications/ contains paired text-free assets, editable previews and text-zone geometry. Final design acceptance, story lifetime, automatic publication delay, eligible lotteries/event frequency, late-event policy and channel destination remain open. Synthetic examples and field limits are proposals; no automatic or real channel publication is enabled. |
| OD-033 | Product brand spelling | Resolved 2026-10-04 | Owner requests consistent branding throughout the application using docs/brand.md. Display Casper Loto, Casper Grand, Casper Bingo, Casper Fast and Casper LIVE in Mini App, Web, Admin and bot messages. Presentation aliases cover legacy response labels; technical codes, stored names, immutable financial and draw history remain unchanged. |
| OD-032 | Kasper LIVE instant lottery | Resolved 2026-09-22 | Mini App only; no draws or auto-purchase. One ticket costs 2,000 CAS; a request buys exactly 1 or 3 tickets atomically. The server selects the prize first using fixed v1 odds, settles immediately, burns ticket cost, pays wins from the Kasper Fund through ledger, and stores immutable numbered history. The client only stages a short common reveal. Admin exposes only total tickets, wins, losses and sales-minus-payout result without player identity. |
| OD-031 | Fast Web presentation | Resolved 2026-09-21 | Owner authorizes independent premium Web art direction, unrestricted by the simple Mini App visual style. Three stable desktop scenes, stacked mobile sections with sticky game links, one-click random ticket or own numbers. Live MUST replace the corresponding main scene, never append a panel below or shift the page. Manual selection occupies the same fixed-height scene and survives live interruption. Browser access and desktop/mobile screenshots are required before release. No changes to lottery mechanics. |
| OD-029 | Premium Web and shared identity | Resolved 2026-09-21 | Owner authorizes independent premium Web on the existing VPS, Telegram login plus username/password without email, canonical existing users.id as unique ID. Mini App, lottery mechanics, draw settlement and database remain shared and unchanged. Initial Telegram login uses a five-minute single-use code from the existing bot; a password can be added to that same profile. |
| OD-030 | Existing-account merge and password recovery | Open | No automatic merge by names, no reassignment of historical tickets, no password reset by guessed identity. If two existing profiles already exist, their consolidation and recovery of a password-only account require a separate owner-approved policy. |
| OD-001 | Daily lineup | Resolved 2026-09-02 | PLL 02:22/13:45, PSS 12:00/20:30 and KHAN 09:00/18:00 are independent entities. |
| OD-002 | Daily numbering | Resolved 2026-08-31 | Each entity starts at the current production Daily counters and advances independently. |
| OD-003 | Daily price | Resolved 2026-08-31 | Each starts with the current production Daily ticket price; Admin may configure later. |
| OD-004 | Daily payout | Resolved 2026-09-04 | ПЛЛ/ПСС: 0/1 matches pay 0, 2 pays 50%, 3 pays 300%, 4 splits jackpot. «6 из 36»: the same 2/3-match payouts, 4/5 pay 0, and 6 splits jackpot. Unified funding from OD-015 applies. |
| OD-005 | Daily jackpot | Resolved 2026-08-31 | PSS/KHAN start at 24m CAS; PLL preserves shared Daily funds. |
| OD-006 | Interfaces | Resolved 2026-08-31 | Telegram bot + Mini App for players, separate Web Admin; ordinary player Web removed. |
| OD-007 | Welcome grant | Resolved 2026-08-31 | Temporary automatic target grant is 100bn CAS once per Telegram identity through ledger. |
| OD-008 | Cart TTL | Open | Persistence stays disabled until the owner chooses a duration; session cart works. |
| OD-009 | Multi-draw purchase | Resolved 2026-09-01 | The player explicitly chooses 1 or 5 draws. All tickets and the full integer-CAS price are created and charged atomically up front; there is no renewal or later hidden debit. Paid contributions enter the lottery-wide funds at purchase time. |
| OD-010 | Player notifications | Resolved 2026-09-01 | Telegram is opt-in and sends only results for draws where the player owned a ticket plus one inactivity reminder after 24 hours without a purchase. Mini App stores wins and draw invitations in its own inbox. |
| OD-011 | Owner auto-play | Resolved 2026-09-01 | Telegram player 1201541335 receives five cryptographically random tickets once for every open draw. Purchases use the regular ledgered service and are controlled through audited Admin settings. |
| OD-012 | CAS purpose and audience | Resolved 2026-09-01 | CAS is permanently virtual and cannot be purchased, sold, withdrawn or exchanged for money or property. K-Loto is a private entertainment project for the owner and up to 50 friends, without public or commercial operation. |
| OD-013 | «3 СЕНТЯБРЯ» funding | Resolved 2026-09-01 | Tickets cost 333 CAS. One match pays 333, two pay 3,333, and 3/3 shares the 33,333,333 CAS main prize. Since 1.7.0 the unified funding rule in OD-015 applies. |
| OD-014 | «ГРОБ» rules | Resolved 2026-09-01 | Daily 3/16 at 06:06 and 23:06 Moscow, price 6,666 CAS, cutoff 2 minutes. One match pays 666, two pay 6,666, and 3/3 shares the 6,666,666 CAS base jackpot. Since 1.7.0 the unified funding rule in OD-015 applies. |
| OD-015 | Единая финансовая схема | Resolved 2026-09-04 | 100% цены нового билета поступает в джекпот его лотереи. Обычные выигрыши и восстановление базового джекпота оплачивает единый Фонд Каспера. Старые distribution/reserve сохранены только как финансовая история. Для Kasper Grand обычные категории рассчитываются как 20%/10%/8%/4%/2% накопительной части джекпота для 5+1/5+0/4+2/4+1/3+2 соответственно; полный 5+2 получает весь джекпот. |
| OD-016 | Fast | Resolved 2026-09-05 | FLASH, CODE и PULSE идут строго по очереди каждые 3 минуты; каждая возвращается через 9 минут, cutoff 8 секунд. FLASH — 3/15 с выплатами 88/888 CAS за 1/2 совпадения. CODE — последовательность из 4 цифр 0–9 с повторами; выигрывает только точный код и делит jackpot. PULSE — 2/10 + 1/5 с выплатами 88/888 CAS. У каждой Fast-лотереи сохраняются собственные цена, jackpot и нумерация. 100% цены поступает в jackpot. Закрытие продаж и переход карточки в эфир происходят одновременно за 8 секунд до старта; результат показывается 6 секунд. Ближайшая карточка остаётся наверху до конца эфира, после чего плавно уступает место следующей. Владельцу сохраняются auto-play и личный Telegram-результат каждого Fast-тиража. |
| OD-017 | Kasper Grand | Resolved 2026-09-04 | Сущность `weekly` переходит с 5/20 на два независимых поля 5/35 + 2/5 без сброса нумерации. Старые завершённые тиражи остаются историей, активные старые билеты получают полный ledger-возврат, следующий тираж использует новый формат. |
| OD-018 | Классика 6 из 36 | Resolved 2026-09-04 | Сущность `khan` сохраняет расписание 09:00/18:00 и нумерацию, но будущие тиражи переходят на 6/36. Билеты старого формата получили полный ledger-возврат. Цена нового билета — 48 000 CAS. Выплаты: 2/6 = 12 000, 3/6 = 48 000, 4/6 = 480 000, 5/6 = 4 800 000 CAS, 6/6 делит jackpot. Базовый jackpot — 30 000 000 CAS. |

| OD-019 | Kasper Bingo | Resolved 2026-09-05 | Отдельная ежедневная лотерея в 22:00 МСК, cutoff 2 минуты. Пул 2000 готовых уникальных комбинаций, неизменные строки 3×4 из 1–60; лимит 50 билетов на человека за тираж, цена 50 000 CAS. Выпадают 58 чисел без повторений. Первый билет с любой строкой делит 100 000 CAS, с любыми двумя — 500 000 CAS. Первый полный билет до 28-го хода включительно делит джекпот; после этого отдельного приза за полный билет нет. Один билет может выиграть несколько туров. Совпавшие по ходу победители делят соответствующий приз по билетам; целый остаток CAS — по возрастанию серийных номеров. Непроданные билеты не участвуют. Пустой тираж проводится; приз без победителя остаётся в фонде, джекпот переносится. Базовый джекпот 10 млрд CAS финансируется из Фонда Каспера, 100% продаж поступает в джекпот. Эфир раскрывает по числу каждые 2 секунды; выплаты после его окончания. Без штрихкода. |
| OD-022 | Kasper Bingo 1.25 | Resolved 2026-09-14 | Заменяет категорийную часть OD-019 для будущих расчётов: 100 000 CAS делят все проданные билеты со строкой до 18-го хода, 500 000 CAS — все проданные билеты с двумя строками до 34-го; джекпот остаётся за полным билетом до 28-го. Обычный приз без победителя остаётся в Фонде Каспера. Официальная нумерация непрерывна между тиражами и продвигается только при покупке; пул использует отдельные технические позиции. Приняты быстрые покупки 1/5/10/все доступные, точный поиск по пяти числам, ограниченный набор из 10 билетов с 2/9/16/28 и компактный эфир с категориями снизу. |
| OD-023 | Player auto-play | Resolved 2026-09-14 | Supersedes the owner-only scope in OD-011 and OD-016. An audited enabled auto-play setting applies to any active non-admin player selected in Admin Panel. Each open draw receives the configured 1–5 random tickets once through the normal ledgered purchase service; balance, draw and purchase limits remain enforced. |
| OD-024 | Purchase feedback and Bingo operations | Resolved 2026-09-15 | Supersedes the five-number search portion of OD-022. Purchase success is non-blocking and dismisses automatically; Telegram permission is requested only from the account settings. Bingo ticket search uses one to three favorite numbers, while the fixed Kasper set retains four. Admin represents Bingo by moves, omitted balls and prize categories rather than ordinary number-frequency charts, and may configure 1–5 auto-play tickets per draw. |
| OD-025 | Quiet notifications | Resolved 2026-09-15 | Supersedes the delivery scope in OD-010 and OD-016. Telegram sends players only their own jackpot win and the existing once-per-24-hours inactivity reminder; purchases, ordinary results and auto-play results are not delivered. The Mini App inbox excludes routine Fast results, which remain available in ticket history. |
| OD-026 | Kasper Fast refresh | Resolved 2026-09-15 | Supersedes the format and navigation portions of OD-016 and OD-020. The player section is named Kasper Fast, marked red and uses a separate red-black screen; promotional Fast references outside it are removed while its accumulated ticket history remains. New FLASH draws use 3/16. New PULSE draws use 2/10+2/5: one total match pays 88 CAS, two or three pay 888 CAS, and 2+2 splits the jackpot. Existing scheduled draws and purchased tickets retain their old snapshotted formats without refunds or mutation. |
| OD-027 | Главная Mini App | Resolved 2026-09-15 | Supersedes the “короткая” главная из OD-020. Экран «Сегодня» оформлен как афиша: крупный ближайший обычный тираж, до трёх следующих событий и персональный блок «Вы в игре». Неблокирующая строка показывает общие билеты проекта, выигрышные билеты, выплаты текущего месяца и сумму текущих джекпотов. Kasper Fast остаётся только в собственном разделе. |
| OD-028 | Непрерывная покупка | Resolved 2026-09-15 | Прямая покупка не возвращает игрока на главную: открытая лотерея сохраняется, купленная комбинация очищается, а нижние действия покупки закреплены на экране. Kasper Fast открывается сразу с карточек игр; последний джекпот и история расположены после них. |

| OD-020 | Навигация и Fast | Resolved 2026-09-05 | Четыре кнопки: Сегодня, Лотереи, Fast, Моё. Билеты остаются в Моём. Главная короткая; каталог обычных лотерей в две колонки, акцент на джекпотах без формата Bingo на лицевой карточке. Эфиры внутри игр. Fast отделён от обычной истории билетов, тиражей, джекпотов и админской аналитики; доступен режим всех игр. Денежные правила и автопокупка не меняются. |

| OD-021 | Косметические выпуски и бренд 2:22 | Resolved 2026-09-05 | ПЛЛ получает отображаемый бренд 2:22. Разные визуальные темы обычных лотерей, Fast без изменений. По указанию владельца для чистой косметики — без новых тестов, полного прогона и финансовой резервной копии; проверка сборки и публикация gateway. Финансовые/механические изменения по-прежнему требуют соответствующих проверок и backup. |
## Publication activation override — 2026-10-06

The owner explicitly authorizes real channel posts and a one-time historical replay from 25 September 00:00 Europe/Moscow through the captured current UTC cutoff. This replay includes calculated A/B drafts, sends each event separately without an editorial interval, and overrides the normal old-event approval rule. Ongoing automatic posts retain a 30-minute interval without a daily cap; manual approvals bypass and do not reset it. Stories retain only the ten latest relevant events within 24 hours. A/B categories, copy and artwork stay separate. Telegram-required rate limits are respected.

Open criteria remain: unusual result A2.4, what counts as a large ordinary win A3.3/A3.5, activity A4.4/A5.4, anniversary grid A5.7 and unspecified record A5.8. Those types do not invent triggers. A8/B4 need confirmed owner-authored changes. Jackpot milestone ratios use the previously approved configurable 1.5/2/3 approach; ticket/player/streak grids remain as previously approved.

## Publication stop supersedes activation — 2026-10-06

The owner stopped automatic channel delivery because the historical replay included routine Fast results for every draw. Production transport is disabled. The earlier historical activation authorization no longer authorizes further delivery. Leave pending events blocked and published messages intact. Routine Fast results must not be treated as significant news merely because a draw completed; clarify their eligibility before any resumed replay. Resume requires explicit owner authorization.

## Corrected historical replay authorization — 2026-10-06

Supersedes the emergency stop for the corrected replay only: owner authorizes restarting all eligible A/B events since 25 September, including calculated drafts and repeats of previously sent eligible events. Exclude routine per-draw Fast A2.1/A2.2/A2.3 and A3.1/A3.2 at both event generation and outbox delivery. Fast jackpot wins, format/platform records, agreed milestone/streak thresholds and period summaries remain eligible. Missing business criteria remain unresolved and must not be invented. Preserve previous delivery IDs in the event audit when explicitly replaying; normal collection remains idempotent. Historical replay has no editorial interval; subsequent automatic posts retain 30 minutes, with manual sends exempt. Owner requests no additional backups or broad checks for this correction, and removal of unneeded copies after completion.

## Publication criteria correction — 2026-10-06

Owner retires unique-participant records everywhere: A4.3/A5.2 are removed from the selectable catalog, feeds, approval and delivery. A5.5 means a genuinely new format-scoped record of distinct paid winning users in ONE draw, strictly more than 20; repeat weekly snapshots of an unchanged maximum are not events. Routine draw completion/combination/carryover/winner counts for any lottery do not qualify for the historical or ongoing channel queue. Template metadata is not an approved trigger. Channel event eligibility uses an explicit configured allowlist: approved A1 jackpot events, A4.1/A4.2 threshold/ticket records, the specified A5.5 winner record, and the agreed B types with real source facts. Other design-only A types remain inactive pending defined conditions. “3 сентября” is an existing active lottery NAME and remains included; do not mistake it for an event date or retire that game.


## Publication editorial rules — 2026-10-06

Owner explicitly selects a minimum increase of 100,000,000 CAS from the last announced jackpot record for A1.3, A1.4 and B2.1. Small intervening increases update factual maxima without advancing the editorial checkpoint. Existing queued notices must pass the same gap. Remove automatic event/date/time/MSK footers; contextual jackpot dates remain permitted. Non-jackpot copy and artwork omit dates. Remove original Fast templates for flash/shadow/pulse; only fast-owner-v1 is selectable. Preserve published receipts and financial history.


## OD-049 — Casper Vault — Resolved 2026-10-09

Owner explicitly approved ticket price 5,000 CAS and changed the proposed odds to: 3,000 at 35%; 5,000 at 25%; 10,000 at 10%; 50,000 at 5%; 300,000 at 2%; new 1,000,000 at 1%; 5,000,000 unchanged at 0.01%. Remaining no-prize probability is 21.99%. Expected payout 22,300 CAS / RTP 446% was stated to the owner; implement the approved values without choosing alternative monetary requirements. Golden vault artwork, finger-operated wheel, one/three tickets and reveal-all reuse the approved instant purchase system. No refunds or modifications of previous games.
## OD-050 — Distribution draws — Resolved 2026-10-09

Owner approved all active scheduled lotteries including Fast, explicitly excluding Casper Dual entirely and instant games. Admin chooses the official Moscow date/time and confirms any time before sales close, including after tickets were bought. Purchased tickets and ordinary payouts remain unchanged. A jackpot winner follows normal settlement. Otherwise the whole current draw jackpot is allocated per ticket in the highest nonempty lower prize category, descending to all paid tickets if none wins. Bingo uses tour 2, then tour 1, then all tickets. Integer remainders follow public ticket number/UUID. Restore the snapshot base jackpot from Kasper Fund using ledger entries. No tickets means carry forward without distribution/reset.

Immediately after confirmation publish a human text-only Telegram announcement with date/time/current jackpot and hashtags, without the regular publication interval. No stories/images. Show a distribution marker only on the designated current draw. Preserve completed draws and all purchased tickets; record assignment audit and unique durable announcement receipt. Ambiguous Telegram failures are visible and never blindly resent. Future calendar selection prepares the official intermediate draw sequence under the existing lottery lock, without changing schedules.

## OD-051 — Distribution follow-up and proposal lifetime — Resolved 2026-10-11

Owner requires paid distribution to end the jackpot drought cycle, just as a genuine jackpot win does. An empty draw that carries the jackpot does not reset the cycle. Count chronologically by official scheduled draw time; do not fabricate jackpot-win events or alter completed draws. Archive pending claims about superseded cycles.

Every new completed distribution draw creates a separate durable automatic text result in its settlement transaction: jackpot paid, winning tickets (not unique players), exact payout groups, total payouts and closing jackpot. Preserve existing schedule announcements. Results bypass general editorial approval/gaps and remain queued during definite delivery delays; ambiguous failures retain the existing nonduplicate uncertainty policy. Recover missing results only for fresh completed draws from the last 24 hours when upgrading, avoiding unsolicited old retrospective posts.

Unanswered editorial suggestions expire at 24 hours from creation or source event, whichever is earlier; editing cannot prolong them. Remove before pagination and archive with audit/tombstones, preserving published history and authorized delivery. Refresh the open suggestion list automatically, without overwriting editor work; refuse publication/edit of expired proposals on the server.


## OD-052 — Browser client retired in production — Resolved 2026-10-14

The owner explicitly requested stage 1 of the financial audit remediation and authorized removing the separate browser version from the server. Keep `archive/reference/legacy-web/frontend/web` in the local Git repository for reference and local development; exclude it from release archives and gateway builds, remove its production checkout and disable `/api/v1/web` (including registration and login). `/web` returns 410. Telegram Mini App, Admin, existing users, purchased tickets, draws and ledger history remain available and unchanged. Retained rollback images follow the existing retention policy.


## OD-053 — Mini App profile statistics — Resolved 2026-10-14

Owner requests ready profile totals and favorite numbers from the latest 1,000 tickets, with no explanatory profile text for now. Preserve the current favorite-lottery selection (eligible lifetime regular-ticket count); favorite-number window is the latest 1,000 eligible regular tickets in that lottery. Refunded tickets and instant symbols are excluded. All tickets and ledger history remain intact. History loads in 20-record pages; derived statistics may be rebuilt from authoritative history. Admin simplification remains separate work.

## OD-054 — Player leaderboard — Partially approved 2026-10-17

Owner requests product ideas for a possible bottom-navigation leaderboard and top 100. Owner approves partially masked usernames with a visible prefix and stars, and prefers no next-update countdown. Mask identities server-side rather than exposing full identities to the client; prefix masking is not anonymity. Owner favors three categories including total currency won and jackpot count; the third category and complete ranking rules remain open. Current recommendation for discussion: “Рейтинг” with “Выиграно” (total actual prize payouts, not balance or net profit), “Джекпоты”, and “Победы” (winning-ticket count), initially lifetime statistics and shared persisted top-100 snapshots rebuilt every six hours. Six/twelve-hour and daily cadences are alternatives under discussion, not an approved schedule. No full implementation or release is authorized yet. Owner decisions remain open on final categories/defaults, qualifying payouts (including return-of-stake and distribution payouts), game scopes, jackpot counting unit, historical coverage, ties, public participation and exact masking/fallback rules. A paid distribution must not be relabeled as a genuine jackpot win.

Implementation evidence: existing `player_profile_stats` is maintained by database triggers and already contains lifetime wins, total payouts and best single-ticket payout across regular and instant tickets; it does not supply monthly/per-game leaderboard counts or a jackpot counter. A basic lifetime board can use indexed reads of these projections without scanning ticket history. Jackpot counting needs an explicitly defined derived counter and a one-time historical initialization. Monthly/per-game scopes would also need derived statistics. Snapshot cadence affects ranking refresh work, not the existing transactional profile-stat updates. The alternative equal-sample competition remains only a proposal; raw win percentages and payout multiples alone do not establish equal opportunity. Owner's continued interest in total payouts is compatible with a straightforward achievement leaderboard despite purchase-volume effects.

## OD-055 — Collections, seasonal cases and public showcase — October scope approved; rules open 2026-10-17

Owner likes collections of figurines, cases purchasable with virtual CAS and a gold badge for a genuine “6 из 36” jackpot. Owner says current accounts are exclusively their test bots and considers a balance write-down acceptable for an economy transition. No balance change, ticket deletion or historical draw modification is performed by this planning task; future CAS corrections require ledger/audit records.

Owner confirms an October 2026 roadmap covering leaderboard, badges/achievements, collections/showcase, seasonal cases, tasks/bonuses and an updated economy/start grant, and requests a shareable human-language image plus a separate technical order. The first seasonal theme is “Осенний кейс”, with a refresh roughly every three months and mixed weighted rewards: figurines, lottery tickets and virtual CAS. The earlier guaranteed-new-figurine/no-repeat recommendation is withdrawn. “50 rewards, 12 collectible” is explicitly an example, not an approved count or drop probability.

Current navigation and phased scope are in `docs/COLLECTIONS_ROADMAP_DRAFT.md`, technical dependencies in `docs/OCTOBER_2026_IMPLEMENTATION_ORDER.md`, and a clickable illustrative flow in `design/planning/casper-collection-map.html`. Collection/cases live inside “Моё”; the leaderboard opens a masked public player showcase. Public sharing/participation rules remain open. Starter gift case, exact showcase slots and completion rewards remain proposals. Final content/artwork, case price/weights, repeat handling, ticket game/draw/funding, season boundaries/old-case access, jackpot qualification/history coverage and test-balance transition remain undecided. All prototype names, counts, amounts and item symbols are examples. This request produces planning/publication assets only; actual feature implementation, balance operations and channel posting are not performed in this task.

## OD-056 — Economy baseline and lottery rebalance — Proposal only 2026-10-17

Owner requests the current prices, jackpots, prize categories and per-player purchase limits for every active game, with recommendations before implementing the economy. `docs/ECONOMY_REVIEW_2026-10-17.md` separates a read-only production snapshot at 19:59:49 UTC from an unapproved candidate model. No runtime settings, balances, tickets or draws are changed.

Verified concerns: welcome grant 100 billion CAS; Vault expected payout 22,300 at price 5,000 (446%, previously approved OD-049); current per-draw caps permit complete distinct-combination coverage in 2:22 and Halloween; no global daily purchase cap; production purchase limiter actually uses ten requests per five seconds despite the per-minute setting name. Progressive games route 100% of stakes to jackpot while other prizes/base restoration use Kasper Fund; distribution draws must be included in reserve modelling. Ball's current 0+1 payout excludes 1+1/2+1/3+1.

Unapproved discussion model includes 100,000 starter CAS and 20,000 daily-entry CAS, a proposed price/base table, revised ordinary tiers for Khan/Ball/Grand/Dual, Vault price 30,000 preserving its payout distribution, lower per-draw caps and a preliminary global 100 paid tickets/day cap. These are recommendations, not requirements or authorization to implement. Still open: CAS issuance/reserve budget and funding, stake allocation, final prices/bases/tiers/caps, rate-window intent, gift-ticket treatment, distribution frequency, season simulation criteria and safe transition of existing balances/pools/future tickets. No existing accumulated jackpot is authorized for write-down. Record any later owner decisions explicitly; preserve completed history and use ledgered compensation when separately approved.

## OD-057 — Vault price and LIVE probabilities approved — 2026-10-18

Owner approves Vault ticket price 30,000 CAS instead of 5,000, with the existing prize distribution/max prize retained. New purchases use the higher price; stored purchases/history and idempotent replay preserve their original amounts. This supersedes only the Vault price part of OD-049/OD-056. Owner requests only necessary checks and explicitly defers DEVLOG/CHANGELOG updates until the economy changes are complete.

Owner clarifies LIVE: 0 CAS 60%, 1,000 CAS 15%, 2,000 CAS 18%, 5,000 CAS 5%, 20,000 CAS 1.8%, 100,000 CAS 0.19%, 1,000,000 CAS 0.01%. Price remains 2,000; maximum remains 1,000,000. The corrected distribution totals 100%, expected payout is 1,410 CAS (70.5%). New LIVE tickets use odds version v2; v1 remains resolvable and included in the same game's history/statistics. No historical ticket/result/ledger rewrite. Other economy proposals in OD-056 remain unapproved.


## OD-058 — Planned pause and Fast economy, batch 1 — 2026-10-18

Owner authorizes closing the Mini App indefinitely until a new explicit reopening instruction. Admin stays available. Purchases, auto-play, new draws and scheduled announcements pause; obligations due at the recorded closing cutoff finish with old snapshots. Future purchased tickets receive full compensating ledger/audit refunds and remain stored; future scheduled draws become terminal CANCELLED. No draw/ticket numbers or counters may be reset or reused. Completed history is immutable. On explicit reopening, persist a recovery checkpoint and skip planned downtime slots; real missed draws after that checkpoint still recover chronologically.

Owner approves a new economy epoch with default Admin statistics scoped to the new epoch and a read-only “Архив старой экономики” view for old draws/tickets/metrics. Current account balances remain real account values. Existing bot balances have not been authorized for a particular replacement amount; wait for the owner's next batch. Rules/prices/bases for other games also await subsequent batches. Reset the three Fast jackpots to their newly approved bases through transfers with Kasper Fund. Other jackpot adjustments will accompany their approved batches. Do not update DEVLOG/CHANGELOG yet.

FLASH, CODE and PULSE: price 2,000 CAS, 800 CAS (40%) to progressive jackpot, 1,200 CAS (60%) burned, max 500 tickets per player/draw; existing 100 per transaction retained. Exactly one highest-category prize per ticket; progressive jackpot shares among winning tickets as before. FLASH base 10,000,000, fixed matches 2→2,000 / 3→8,000 / 4→100,000. CODE base 15,000,000, fixed exact positions 1→2,000 / 2→4,000 / 3→10,000 / 4→500,000. PULSE base 40,000,000; A+B 1+1 or 0+2→4,000, 1+2→8,000, 2+0 or 2+1→14,000, 2+2 without cipher→500,000 (owner correction supersedes the initial 1,000,000 proposal), 2+2 with cipher→jackpot. Lower tiers ignore cipher match. Formats unchanged, including PULSE's 199-value server cipher and jackpot probability 1/197,010. Original rules remain registered for historical draws.

Economic limitation, reported to owner: ordinary-prize expectation per ticket is approximately FLASH 1,612.49 / CODE 1,253.70 / PULSE 1,690.39 CAS. All exceed the burned 1,200 CAS, by 412.49 / 53.70 / 490.39 respectively, before base-jackpot replenishment. Ordinary prizes and base resets continue using Kasper Fund. This approved payout table does not create a self-funding reserve. No alternative payouts or fund issuance are authorized.


## OD-059 — Accumulate economy batches locally; clear daily CAS reporting — 2026-10-18

Owner explicitly changes this maintenance workflow: implement incoming economy parts locally with focused checks only. Defer clean production builds, the complete release suite, release backups, production migration/application and deployment until the explicit final instruction (e.g. “это финал, включай”). Keep production closed throughout. This is a local-only exception to ordinary immediate-deployment rules, not a request to disable scheduled backups or independent monitoring. Refunds already closed old future obligations for ALL lotteries in OD-058; do not repeat them per batch. Reopening still requires an explicit owner instruction. DEVLOG/CHANGELOG remain deferred until the finale.

Owner clarifies that a closed/self-funding economy is NOT a project requirement. The approved Fast payouts need not be reduced merely to eliminate net issuance. Report observed flows transparently so the owner can compare days and decide later; no unapproved payout/fund changes.

Owner requests a prominent daily CAS overview in Admin and historical comparison. Existing “Сегодня” reports draw-ticket sales/payouts, not complete wallet flows, and excludes instant-game flows from that draw aggregate. Add a read-only all-project ledger report to the homepage: credited/debited player wallets, their net change, separate prizes/jackpots, ticket refunds, admin corrections and other credits/debits (including bonuses). Also report actual system issuance/burning by the NET sum across all accounts of each complete operation, so transfers between players, jackpots, funds and reserves do not count as newly created or destroyed CAS. Moscow calendar days, 7/30-day comparison and an arbitrary past report day; the selected economy epoch filters complete operations, and partial/excluded days are labelled. No new money movements, refunds or schema changes are authorized by this reporting task. Full PostgreSQL/performance and release checks are deferred until the finale.


## OD-060 — Approved 2:22, Halloween and September economy — 2026-10-18

Owner approves unchanged draw mechanics and schedules, with a maximum of 100 tickets per player per draw for all three games. A transaction cannot exceed that cap; retain any smaller existing per-purchase limit. Exactly 50% of each ticket goes to the progressive jackpot and the remaining CAS burns. Ordinary prizes and base restoration retain existing Kasper Fund funding; jackpot sharing between winning tickets remains unchanged.

2:22 (`pll`): 4 of 15; ticket 22,222 CAS; base jackpot 2,222,222 CAS; 2 matches pay 22,222, 3 matches 44,444, 4 matches the progressive jackpot. Halloween (`grob`): 3 of 28; ticket 6,666; base 6,666,666; 2 matches 66,666, 3 matches the progressive jackpot. 3 СЕНТЯБРЯ (`september`): 3 of 33; ticket 3,333; base 3,333,333; 1 match 3,333, 2 matches 9,999, 3 matches the progressive jackpot. Preserve historical rules under their original persisted codes; only new draws use the new rules.

Project-wide monetary precision decision: preserve exact approved thematic prices, jackpots and prizes, with integer arithmetic and no floating point for money. Never round these values to tens/hundreds/thousands for technical convenience. For a 50% ticket-to-jackpot allocation, round UP in favor of the jackpot PER TICKET; burn the remainder. Thus 22,222 splits 11,111/11,111; 6,666 splits 3,333/3,333; 3,333 splits 1,667/1,666. Bulk and multi-draw purchases sum individual ticket contributions. This does not change legacy prize-ratio rounding or the approved Fast 40% split.

Prepared locally under OD-059. At the explicit final release, apply the separate idempotent paused batch `scripts/apply_economy_batches.py`: set the approved price/rules/limits and reset these three jackpots to their bases using balanced compensating ledger entries with Kasper Fund and admin audit. Require the initial pause/refunds to have completed and no unresolved draws/tickets. Never rerun refunds, create another economy epoch, alter completed draws/tickets/counters, reset bot balances or reopen the app as part of this batch. Full release checks, production application and DEVLOG/CHANGELOG updates remain deferred until the owner's final instruction.


## OD-061 — Owner Admin workspace and fresh analytics — 2026-10-18

Owner explicitly continues local work and asks for a simpler, visually clear Admin centered on statistics, economy, tickets, winnings and jackpots. Primary navigation is Overview, Economy, Tickets and winnings, Jackpots, Statistics. Less frequent management (players, game settings, Fast/instant details, draws, schedules, distribution, publications) is grouped under a collapsed Management section. Diagnostics, notification queues, ledger/audit, development journals and format history live in System and load only when the relevant tab is opened or manually refreshed. No background polling is introduced; independent production monitoring remains enabled.

The new `/admin/overview` projection returns business metrics without reading scheduler diagnostics, notification status or recent ledger transactions. Overview combines ordinary draw games and Fast, with instant-game counts separately accessible and all-game CAS flows in Economy. Clearly label these scopes. Show the selected economy stage, Moscow-day figures, exact CAS flows, and a zero-state message before the first new purchases. Full jackpot history is fetched on expansion. Preserve existing detailed ticket/player lookup and financial safeguards.

All Admin analytics start from the already established economy epoch; do not create another epoch or delete historical data. Keep old economy available in its read-only archive. Test actual aggregate queries with old/current rows, including instant tickets, jackpots, ledger, aliases and outer joins. Archived number statistics resolve the latest recorded old format rather than requiring the new payout version; remove the client-side hardcoded historical date floor. Failed or late requests must not carry archived totals/draw details into the current stage. Current account balances and jackpot funds remain real balances, not resettable analytics counters; current jackpot balances are hidden in archived jackpot statistics.

Prepared and visually reviewed locally on desktop/mobile with explicitly marked test fixtures. Focused Admin/backend checks only; complete release checks, production build/deployment and DEVLOG/CHANGELOG remain deferred under OD-059.


## OD-062 — Approved 6/36, Casper Ball and Casper Grand economy — 2026-10-18

Owner approves new economics while keeping existing combination/draw mechanics and schedules. All three games route 40% of every ticket to progressive jackpot, burn the remaining 60%, and allow at most 600 tickets per player per draw across purchases. Do not introduce additional daily limits. Preserve any smaller existing per-purchase cap; otherwise cap a purchase at 600 to satisfy the per-draw constraint. Each ticket receives only its single highest applicable prize. Ordinary prizes and base restoration continue using Kasper Fund; progressive jackpot sharing between winning tickets is unchanged.

6 из 36 (`khan`): 6 of 36; ticket 25,000 CAS; base jackpot 100,000,000 CAS. Exact matches 2→30,000; 3→140,000; 4→1,000,000; 5→7,000,000; 6→progressive jackpot. Per ticket: 10,000 to jackpot, 15,000 burned.

Casper Ball (`pss`): 5 of 36 plus 1 of 8; ticket 25,000 CAS; base jackpot 250,000,000 CAS. Main+special matches 0+1→25,000; 1+1→100,000; 2+0→50,000; 2+1→100,000; 3+0→200,000; 3+1→400,000; 4+0→1,000,000; 4+1→5,000,000; 5+0→25,000,000; 5+1→progressive jackpot. Per ticket: 10,000 to jackpot, 15,000 burned. No prize for 0+0 or 1+0.

Casper Grand (`weekly`): 5 of 35 plus 2 of 5; ticket 50,000 CAS; base jackpot 5,000,000,000 CAS. Main+special matches 2+0→75,000; 2+1→150,000; 2+2→300,000; 3+0→650,000; 3+1→850,000; 3+2→1,200,000; 4+0→1,500,000; 4+1→3,000,000; 4+2→8,000,000; 5+0→30,000,000; 5+1→60,000,000; 5+2→progressive jackpot. Per ticket: 20,000 to jackpot, 30,000 burned. No prize below two main matches.

Prepared locally under OD-059 as independent idempotent step `2026-10-classic-ball-grand-economy-v2`, preserving original rules for all historical snapshots. Final `scripts/apply_economy_batches.py` applies the earlier themed batch and this batch through the shared paused transition service, with compensating Kasper Fund/jackpot ledger transfers and audit for new bases/settings. Never repeat ticket refunds, reset counters/history, create another economy epoch or reopen the app during this batch. Disposable PostgreSQL recovery/distribution checks recognize both old and new versions and derive expected ordinary payouts from the selected rules; execute them at the final release, not against production now. Full checks, backup/deploy and DEVLOG/CHANGELOG remain deferred.


## OD-063 — Private daily owner economy summary — 2026-10-18

21 October follow-up: owner explicitly requests clearer daily copy, separate
FAST/instant/ordinary-draw purchase counts, new Telegram registrations and useful
economy indicators. Report gross paid purchases (including auto-play), list
gifts/refunded purchases separately, deduplicate buyers across game types and
count Dual once. Separate funded achievement payouts from other credits; show
current player/jackpot totals and readable observed fund expense. Preserve
operation-net issuance/burning, Moscow-day boundaries, existing delivery guards
and factual warnings; do not invent financial alarm thresholds or change game
economics. Already delivered reports are not resent.

Owner requests implementing a simple daily personal report through the existing lottery bot, locally for the eventual combined economy release. Explicit authorization covers the future automated private delivery to the configured owner, not a channel or players. Owner is flexible about the time; choose a complete previous Moscow day, eligible from 00:05, with a cheap five-minute reconciliation and startup recovery of the latest day only. No retrospective backlog spam. Keep preparation/delivery paused during the current maintenance window. No production messages are sent by this implementation task.

Include purchased regular/Fast/instant ticket counts, CAS purchases, prizes (including jackpot payouts but no jackpot count), refunds, bonuses/other credits, manual adjustments, player wallet net, actual global issuance/burning, current Kasper Fund balance and its daily net. Reuse the Admin complete-operation ledger report and current economy epoch. Purchases minus prizes minus refunds is cash movement, not profit; jackpot contributions remain liabilities for future payouts. Positive issuance is permitted by OD-059 and is not itself an alarm. Do not invent a self-funding requirement or automatically alter any business settings.

Explain the observed fund runway as current balance divided by average NET depletion over up to seven complete days of the current epoch, excluding a partial transition day. With no net depletion or no full days, report that no duration estimate is available; do not claim infinite solvency. Warn factually about unresolved report-day draws, an empty fund, or less than one day of observed depletion remaining. The estimate is explicitly not a guarantee of future payouts. No new reserve/emission budget or growth target is approved; those remain owner decisions.

Reuse the existing immutable outbox event payload and unique epoch/day/owner key, SQL conflict protection, and conservative uncertain-delivery policy. Validate owner identity and latest report day/epoch before sending; no player notification preference can redirect the private report. No schema change or financial mutation. New configuration `OWNER_DAILY_SUMMARY_ENABLED` defaults true with the existing `OWNER_TELEGRAM_ID`; missing/inactive/unregistered owner skips preparation. The local `.env` currently lacks that ID. Verify the production recipient/bot association at final activation; never infer the owner's ID from the bot's username. Details and formulas are in `docs/OWNER_ECONOMY_SUMMARY.md`. Full release checks, deployment and DEVLOG/CHANGELOG remain deferred.


## OD-064 — Approved Dual and Bingo economy — 2026-10-18

Owner approves the next local economy batch under OD-059. Dual (`dual`): ticket 40,000 CAS; maximum fixed payout 10,000,000 CAS. Combined NIGHT+DAWN matches 1+1 → 300,000; 1+2 or 2+1 → 1,000,000; 2+2 → 10,000,000, per winning ticket without splitting. Preserve two-stage mechanics and a single payment after both stages, including tickets starting at either stage. Limit 50 tickets per player for every draw, counting both first-stage and second-stage participation. No progressive accumulation: existing stakes flow to Kasper Fund and all prizes are fund-backed. Preserve the existing fixed-maximum account representation and balanced ledger/history compatibility; its value becomes 10,000,000, never increases from ticket sales. Player interfaces call it the maximum prize. Keep the historical Dual payout version for archived draws/tickets.

Bingo (`bingo`): card 50,000 CAS; base progressive jackpot 1,000,000,000 CAS; cap 75 cards/player/draw and allow a 75-card purchase. Each card contributes 20,000 CAS (40%) to jackpot and burns 30,000 (60%). Ordinary prizes are fixed and stack independently: first row by move 18 inclusive → 50,000; two rows by move 34 inclusive → 100,000; all 12 numbers by move 58 inclusive → 20,000. All 12 by move 28 inclusive additionally share the progressive jackpot through the existing integer, public-number-ordered mechanism. Ordinary prizes and jackpot base restoration use Kasper Fund. There are still 58 moves. Preserve generation, row order, pool size 2,000 and the existing special Kasper sets completely.

After successful Bingo settlement, delete only unused pool rows for that completed draw (`ticket_id IS NULL`) in the same transaction. Keep every purchased Ticket and its linked pool row, including historical/refunded cards. A failed settlement rolls cleanup back; retry does not pay twice. This adds no deletion of purchased business history, draw/ticket renumbering or broad historical purge. Future inventories are unaffected. The existing distribution-draw roll-down priority remains two-row category, then one-row category, then all purchased cards; do not silently alter that separately approved policy by adding the new low-value full-card prize to its priority.

New rules are independently versioned (`casper_dual_2_12_2_12_economy_v2`, `bingo_12_60_economy_v2`). Preserve Bingo's historical jackpot result slot at index 2 and append the new ordinary full-card payout at index 3; row closing moves remain three values. Feed, tickets and Admin summaries recognize both shapes and display all 75 cards. Prepare migration 0058 to allow the approved Dual price/rules pair and validate its fixed account against the final transaction state on changes to either configuration or account. It changes no money or completed history itself. Final paused economy steps `2026-10-dual-economy-v2` and `2026-10-bingo-economy-v2` apply prices, limits and ledgered/audited account resets once, without repeating refunds, creating another epoch or reopening.

Focused rule/application/UI checks and offline migration SQL validation are local. PostgreSQL financial recovery smoke fixtures are prepared for the new terms, fixed Bingo stacking and sold/unused card retention; execute live disposable-database migration/recovery checks at the finale. Full release checks, production builds, backups/deployment/restarts and DEVLOG/CHANGELOG remain deferred. Production stays paused until the owner's explicit final instruction.


## OD-065 — Final combined release and explicit reopening — 2026-10-18

Owner explicitly ends OD-059 local-only accumulation, requests all required tests, CHANGELOG/DEVLOG updates, production deployment and opening the server, Mini App and Admin. Authorizes the already approved remaining economy batches and resetting their jackpots via ledger/audit, followed by an explicit scheduler recovery checkpoint. Preserve epoch 2, all historical tickets/draws and numbering. Do not repeat initial refunds or invent a bot starting balance. Prepare plain-language player announcement text for the owner; no channel delivery is requested. Normal release rules resume after this window.

## OD-066 — Achievement foundation, local only — Approved scope 2026-10-18

Owner approves both a concrete technical specification and local implementation, delegates technical choices and prioritizes compact storage and keeping achievement work out of gameplay/Mini App latency. The original brief plus the supplied approved-rules supplement govern this work. No production publication or activation, final achievement catalog, real reward amounts, new gift-ticket mechanism, cases, cosmetics or final UI are authorized. This local-only instruction is independent of and does not reopen the completed OD-065 economy transition.

Approved semantics: distinct draw participation rather than ticket count; refunded paid tickets correct purchase/participation/spend progress without revoking earned achievements or rewards; paid-only purchase metrics, normal result eligibility for future gift tickets; gross payouts and separate net profit; stacked Bingo per-card total and separate prize counts; standard rule-snapshot price for payout multipliers; Moscow Mini App opening days; automatic rewards and controlled CAS/balance/meta cascades. All activity starts at the single achievement launch boundary, with existing balances as the balance baseline. No prelaunch history backfill or old reward issuance.

Technical implementation and local commands are documented in docs/achievements/ACHIEVEMENTS_SPEC.md and docs/achievements/ACHIEVEMENTS_LOCAL_REPORT.md. First version uses one-time awards, a transactional PostgreSQL queue, sparse projections and bounded result pages. The CAS adapter is exercised only on disposable synthetic accounts. The actual funding source for future CAS rewards (issuance versus an explicitly funded account), final catalog/rewards, notification copy/design and production launch remain open business decisions for that later stage. Do not silently select a source of real reward money. Future gift-ticket participation details belong to the separately unimplemented entitlement mechanism.


## OD-067 — Удаление редакционного блока (2026-10-19, утверждено)

Владелец поручил выгрузить локально и безвозвратно удалить с VPS историю
публикаций в канал, картинки и связанные сторис/ленту миниаппа; отдельно
подтвердил удаление сторис/ленты. Дальнейший сбор и доставка отключаются.
Данные розыгрышей, билетов, ledger и игрового аудита сохраняются. Редакционные
контрольные точки, предложения и тексты объявлений не являются финансовой
историей. Старые резервные копии и образы с этими данными переносятся локально;
на VPS создаётся новая резервная копия очищенной базы. Посты в самом Telegram
этой операцией не удаляются. Достижения остаются отдельной локальной работой.

## OD-068 — Первая партия достижений и профиль (2026-10-19, только локально)

Владелец утвердил 22 названия и условия из нового ТЗ, интерфейс достижений,
компактный баланс и блок в профиле. Кастомными считаются «3 сентября», «2:22»
и Halloween: `september`, `pll`, `grob`. На уточнение об объёме публикации
владелец прямо ответил «Оставить локально».

Предыдущая история не используется. Награды конфигурируются, но суммы не
утверждены, поэтому реальные CAS не выдаются; первое получение награды
проверяется только после действительной успешной выплаты за другое достижение.
Источник финансирования из OD-066, суммы и дата запуска production остаются
открытыми до решения владельца. Не менять экономические параметры лотерей.

Результат и локальная база: `docs/achievements/ACHIEVEMENTS_COMMON_LOCAL_REPORT.md`.

## OD-069 — Новогоднее лото 2027 (2026-10-21, утверждено, только локально)

Владелец поручил новую праздничную лотерею: 3 различных символа из 12, 10 000 CAS, суммарно 101 билет/игрок/тираж. Полные выплаты 0 / 5 000 / 30 000 CAS за 0/1/2 совпадения; общий миллион на все билеты с 3 совпадениями, без суммирования категорий и без накопительного джекпота. Порядок символов не важен, повторные комбинации обрабатывает существующий движок.

На уточнение расписания владелец ответил: «в 21:15. Закрытие продаж за 2 минуты до. Серия идет до особого моего указания». Применено ежедневное расписание Europe/Moscow без конечной даты. Экономический маршрут делегирован: «сделай как технически удобно. деньги можно вообще сжигать. как технически проще ?». Выбран существующий путь сжигания стоимости билетов и выплаты из Kasper Fund. Без полных совпадений миллион не переносится; деление целочисленное, остаток по 1 CAS получают выигравшие билеты с меньшими номерами по существующему правилу проекта.

По дополнительному указанию техническая реализация максимально общая с остальными лото: предметы — отображение ID 1–12; покупки, лимиты, ledger, возвраты, планировщик, восстановление и проведение — существующие сервисы. Только визуальная композиция и необязательный параметр фиксированного разделяемого приза новые. Специальные достижения и автоматическое подключение игры к старым настройкам автопокупок не добавлялись.

Владелец явно ограничил работу локальной средой и необходимыми тестами. Полный проектный набор и production публикация в этом задании не выполняются. Точные параметры, графика и проверка: `docs/NEW_YEAR_2027.md`.


## OD-070 — Публикация Mini и Новогоднего лото (2026-10-22, утверждено)

Владелец поручил повторно проверить обе лотереи только необходимыми тестами, обновить документацию и выложить на production. Это отменяет локальное ограничение для этих двух готовых продуктов. Экономика, расписания и визуальные решения остаются утверждёнными ранее; существующая история не сбрасывается. Другие локальные изменения автоматически не включаются в выпуск.
## OD-071 — Английская версия Mini App и приоритет языка (2026-10-22, утверждено)

Владелец поручил сделать английскую версию миниаппа. Приоритет: язык, самостоятельно выбранный игроком в Casper Loto; язык Telegram, если выбора ещё нет; язык браузера/устройства, если Telegram не передал язык. Добавляются русский/английский переключатель профиля, перевод интерфейса, правил и системных сообщений. Расписание остаётся московским, игровые и финансовые правила не меняются. Техническое хранение выбора на устройстве отдельно для аккаунта и проверки описаны в `docs/MINIAPP_LANGUAGES.md`. Действуют обычные правила публикации frontend-only.

## OD-078 — Публичное описание и слоганы (2026-10-23)

Владелец поручил подготовить сначала русский вариант README для GitHub,
использовать утверждённый логотип и пять предоставленных настоящих снимков
с iPhone, добавить личную историю, ссылки на игру, Telegram-канал и @rabochyru.
Основной слоган утверждён: «Удача ничего не стоит»; «Просто попробуй» —
приглашение к игре. Если нужна одна фраза, используется основной слоган.
Логотип остаётся неизменным, слоганы размещаются отдельным текстом.

Владелец прямо закрепил принцип: покупок за реальные деньги не будет
ни сейчас, ни в будущем. CAS, билеты и преимущества не продаются за деньги;
вывода и денежного обмена нет. Это описание философии, не изменение экономики.

Английский README и английская версия слогана — следующий этап, пока не готовы.
В README явно отмечены уже работающие русский/английский интерфейсы Mini App.
Даты и конкретные правила будущих заданий, рейтингов и новых коллекционных
механик не утверждаются этим редакционным заданием.

Упоминание планируемой MIT в приложенном AI-черновике не является отдельным
решением владельца о выдаче лицензии. Выбор лицензии и проверка прав на материалы
остаются открытыми; LICENSE не создаётся. Адрес GitHub-репозитория пока не задан:
ссылки на несуществующие Issues/Discussions не добавляются. Подготовка русского
варианта на просмотр не является публикацией исходников или выпуском на VPS.

## OD-079 — Личный README и новые направления развития (2026-10-23)

Владелец поручил вести README от первого лица: проект делает он один.
Скриншоты описываются как его собственные снимки, время тиражей — UTC+3 (МСК),
подпись — Andrey Kasper. Упоминание основного языка общения удаляется.
Объяснение розыгрышей должно явно называть серверный генератор случайности.

Утверждены направления для Roadmap: профиль нового поколения с витриной,
статистикой за всё время, редкими наградами, историей рекордов и оформлением;
сезоны ориентировочно по три месяца с темой, коллекциями, заданиями и наградами;
совместные цели и сообщества; центр прозрачности со статистикой тиражей,
историей результатов, объяснением вероятностей и симулятором; конструктор
предложений лотерей с публичным голосованием внутри Mini App; открытый API
для безопасных сторонних инструментов.

Отдельным ответом владелец подтвердил: сезоны без платного пропуска
и без давления ежедневными входами. Независимая проверка источника случайности
не обещается: действующего механизма нет. Конкретные игровые правила,
награды, состав сезонов, подсчёт общих целей, голосование, видимость профилей
и методы API этим обсуждением не утверждаются и не реализуются.

Владелец попросил предложить распределение по времени, которое он затем
скорректирует. Окна ноября 2026 — декабря 2027 в docs/ROADMAP.md — редакционный
черновик для обсуждения, не утверждённый срок выпуска. Предложение начать API
с публичного чтения также остаётся проектным направлением, не выдачей доступа.

Владелец не против использования наработок другими, но просит объяснить
лицензию отдельно. MIT или другая конкретная лицензия пока не назначается.
Разрешена проверка готовности GitHub и уборка постороннего материала;
output/ исключается из Git/Docker, исходные файлы сохраняются. Переписывание
истории Git, удаление архивов, отправка на GitHub и выпуск продукта этим
редакционным заданием не выполняются.

## OD-080 — Английская страница и закрытый GitHub (2026-10-23)

Владелец уточнил целевые сроки: профиль нового поколения — ноябрь 2026;
центр прозрачности — октябрь–ноябрь 2026; первый сезон — запуск в январе 2027;
совместные цели/сообщества — февраль–март 2027. Публичное голосование отделено
от конструктора: голосование — январь 2027, конструктор — лето 2027.
Открытый API — май 2027. Это план развития, а не изменение расписания тиражей
или утверждение ещё не согласованных правил будущих механик.

Владелец поручил сделать английский основным языком GitHub-страницы, сохранить
русский по ссылке и загрузить проект в закрытый репозиторий. README, Roadmap
и оглавление документации подготовлены в обеих версиях; основной слоган
переведён как «Luck costs nothing», приглашение — «Give it a try».
Создан Private-репозиторий kasper-kasper/casper-loto; владелец самостоятельно
вошёл в GitHub и подтвердил Git Credential Manager. Разрешена первая отправка
проверенных исходников и истории в этот репозиторий. Предыдущее ограничение
OD-079 на отправку для редакционного просмотра этим поручением отменено.

Открытый доступ и конкретная лицензия пока не разрешены. VPS и игровые
правила этим заданием не меняются. Секреты, посторонние документы и локальные
данные не отправляются. Реальные iPhone-снимки и утверждённый логотип сохраняются.

## OD-081 — MIT и читаемая история проекта (2026-10-23)

Владелец прямо согласовал MIT после объяснения, что она допускает коммерческое
использование и производные проекты с закрытым кодом при сохранении уведомлений.
Добавляется стандартный LICENSE, автор Andrey Kasper, 2026 год; собственный код
и связанная документация публикуются на этих условиях. Сторонние материалы
сохраняют свои условия, а использование имени и логотипа не должно создавать
ложное впечатление официальной версии или одобрения автора. Прежние записи
OD-078–080 о невыбранной лицензии являются историей и заменены этим решением.

Владелец поручил объединить связанные мелкие изменения в читаемые записи
Changelog и Devlog. Публичные журналы получают английскую основную версию
и русский вариант. Исходные журналы сохраняются побайтово с хэшами и полным
указателем заголовков, включая нестандартные и пустые. Объединённые сводки
не подменяют номера старых выпусков и не подтверждают публикацию локальных
экспериментов. Даты реализации и проверки публикации указываются отдельно.

## OD-082 — Нумерацию пока сохранить (2026-10-23)

После обсуждения общепринятых подходов владелец прямо поручил пока не менять
нумерацию и вернуться к решению позже. Текущие версии API 1.59.0,
Mini App 1.70.0 и Admin 1.61.2, манифесты пакетов, lockfiles, теги
и версия работающего продукта сохраняются. Общая версия проекта не назначается,
предложение начать будущую общую последовательность с 1.71.0 не утверждено.
Changelog описывает версии продукта и не имеет отдельного счётчика;
публичный Devlog содержит даты и названия заметок, без номера выпуска дневника.

Открытие репозитория всем остаётся отдельным будущим решением владельца.
Разрешены редакционная подготовка и обновление закрытого GitHub;
игровой код, экономика и VPS этим заданием не меняются.

## OD-083 — Единая публичная версия Casper Loto 1.70.0 (2026-10-23)

Владелец прямо утвердил изложенные им правила версионирования как обязательное
правило проекта и поручил выполнить редакционные изменения. Решение заменяет
ожидание OD-082: текущая единая публичная версия — Casper Loto 1.70.0.
Источник публичного номера — корневой VERSION; CHANGELOG использует номер
публичного выпуска. Самостоятельные внутренние версии API 1.59.0,
Mini App 1.70.0 и Admin 1.61.2 сохраняются и отражены в docs/releases/1.70.0.md.

История 0.1.0 от 14 августа и переход к 1.0.0 от 1 сентября 2026 сохраняются.
Исторические номера, исходные записи, DEV-номера, снимки, SHA-256-манифесты
и Git-теги не переписываются. DEVLOG ведётся по датам и темам, собственного
счётчика версий у него и CHANGELOG нет. Неопубликованные игрокам изменения
накапливаются в Unreleased. Документация, тестирование, локальная разработка
и подготовка GitHub сами по себе не повышают публичную версию.

Правила SemVer полностью закреплены в docs/VERSIONING.md и русской версии:
MAJOR — несовместимость ранее поддерживаемых публичных контрактов с обнулением
MINOR/PATCH; MINOR — совместимые новые функции с обнулением PATCH;
PATCH — совместимые исправления без новых функций. От текущей базы следующие
альтернативы — 1.71.0 для новых функций или 1.70.1 для исправлений. Количество
функций, срок разработки или визуальный масштаб сами по себе не требуют MAJOR.
Перед выпуском агент классифицирует изменения и получает прямое согласование
публичного номера владельцем; самостоятельно менять этот номер запрещено.

Проверены исходники и архивы трёх последних публикаций; для последнего
снимка ba6d8df версии компонентов подтверждены SHA-256-манифестом.
Владелец разрешил подготовить и отправить согласованные правки в закрытый GitHub,
после чего сообщить ему о готовности открыть репозиторий. GitHub Release и новый
тег для этой задачи не требуются и не создаются. Изменение видимости выполняет
владелец после завершения подготовки. Рабочая игра, экономика и VPS не меняются.

## OD-084 — Две копии базы и компактное хранение только на VPS (2026-10-23)

Для текущего этапа, когда играет только владелец, он прямо выбрал последний
упрощённый вариант и подтвердил уточнение: только VPS, компьютер и облако
пока не нужны. На VPS сохраняются две последние проверяемые копии базы,
рабочие/используемые образы и две предыдущие сборки для отката каждого сервиса,
а распознанные архивы — по два каждого вида суммарно в двух известных папках.
image_keep_versions=3 сохраняется: рабочая версия плюс две предыдущие.
database_backup_keep и archive_keep_per_category меняются на 2.

Разрешены проверка и применение штатной очистки лишних распознанных копий
под блокировками operations/backup после проверки оставляемых резервных копий.
Финансовая история, билеты, тиражи, рабочие Docker volumes, неизвестные файлы
и используемые образы не являются целью очистки. Политика диагностических
логов (90 дней и три последние копии) и резерв кеша 512 МБ сохраняются.

Ночная резервная копия и периодическое обслуживание продолжаются автоматически.
Обязательного скачивания при совместной работе и команды ручного скачивания
в рамках этого решения не добавляется. Перенос планировщика и CDN не реализуются.
Изменение эксплуатационного хранения не меняет поведение игры для игроков,
поэтому публичная версия остаётся Casper Loto 1.70.0; Git-теги не создаются.
