# Casper Loto — «Проверь свою удачу»

Standalone Instagram Reel commissioned by the owner on 2026-10-17.
24 seconds · 1080 × 1920 · 9:16 · 30 fps · H.264/AAC · BT.709.

## Creative

| Time | Scene | Message |
| --- | --- | --- |
| 0–3 s | Gold lottery balls, kinetic question | А что, если тебе повезёт? |
| 3–6 s | Ivory colour break, oversized zero | Лото за 0 ₽. Бесплатно. Без вложений. |
| 6–10 s | Number selection in the actual Mini App | Выбери свои числа |
| 10–14 s | Actual game catalogue in an animated phone | Найди свою игру |
| 14–18 s | Sequential ball reveals | А вдруг совпадёт? |
| 18–24 s | Brand, call to action, clear free-play message | Проверь свою удачу. Открой в Telegram. |

All meaningful copy stays within the vertical Reel's central safe area;
the right side and lower portion have room for social UI. Screens were captured
from the current Mini App's existing local design preview at 430 × 880.
Numbers and balances are demo data and are identified as such in the video.
No real accounts, transactions or production data were used.

The creative follows the owner's free-play brief and `docs/NEXT_STEPS.md`:
CAS are virtual game units, without purchase or cash-out for money.
It makes no claim about cash prizes or guaranteed wins.
The CTA names Telegram without inventing a bot username or a profile link.

## Assets and rights

- `public/logo.png`, `symbol.png`: unchanged approved source artwork from
  `frontend/shared/assets/brand/`.
- `public/orbits.webp`: existing repository artwork,
  `assets/publications/khan-owner-v1/six-orbits.webp`.
- `public/catalog.png`, `picker*.png`: captures of the project's local demo.
- `public/Manrope.ttf`: Manrope variable font from Google Fonts;
  SIL Open Font License preserved in `Manrope-OFL.txt`.
- `public/casper-original.wav`: original, deterministic synthesized score and
  effects created by `make-audio.cjs`; 120 BPM, 48 kHz stereo. No sampled songs
  or third-party sound recordings. The reel is designed to work with sound off.

## Edit and reproduce

Node 22.13+ is supported. Run commands in this directory:

```powershell
npm ci
npm run dev -- --no-open --port 4188
npm run lint
npm run build
npm run audio
npm run render
```

For an already installed Chrome, append
`--browser-executable="C:\Program Files\Google\Chrome\Application\chrome.exe"`
to the render command. Every major scene has its own composition in Studio.
The master composition is `Casper-Reel`.

Outputs are in ignored `out/`; source, assets and the lockfile are versioned.
The production application, backend and server configuration are unaffected.
This is a standalone marketing deliverable, not an application release.

## Verification

- ESLint, TypeScript and Remotion production bundle pass.
- Six scene frames were rendered and inspected together for layout, contrast,
  logo integrity, demo labels and text containment.
- Final output metadata, complete decode and audio checks are recorded in
  `out/verification.json` after export.
- The delivery MP4 uses limited-range YUV 4:2:0, BT.709 colour metadata and
  fast-start playback. Audio measures −15.48 LUFS integrated / −1.98 dBTP;
  no additional loudness processing is needed.
- `caption-ru.txt` contains a suggested post caption. Publishing to Instagram
  is a separate owner action; this task only creates the video and supporting files.
