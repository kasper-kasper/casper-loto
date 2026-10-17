// Original, deterministic 120 BPM score. No third-party samples or recordings.
const fs = require('node:fs');
const path = require('node:path');
const rate = 48000;
const seconds = 24;
const left = new Float32Array(rate * seconds);
const right = new Float32Array(rate * seconds);
let seed = 713;
const noise = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 2147483648 - 1; };
const hz = (midi) => 440 * Math.pow(2, (midi - 69) / 12);
const add = (start, duration, fn, pan = 0) => {
  const offset = Math.round(start * rate);
  for (let i = 0; i < Math.floor(duration * rate) && offset + i < left.length; i++) {
    if (offset + i < 0) continue;
    const v = fn(i / rate, i);
    left[offset + i] += v * Math.sqrt((1 - pan) / 2);
    right[offset + i] += v * Math.sqrt((1 + pan) / 2);
  }
};
// Four-on-the-floor kick with a short pitch fall and warm sub.
for (let b = 0; b < 48; b++) {
  const t = b / 2;
  const gain = b < 6 ? .60 : .94;
  add(t, .38, s => gain * (.70 * Math.sin(2 * Math.PI * (49 * s + 7 * (1 - Math.exp(-s * 28)))) * Math.exp(-s * 11) + noise() * .10 * Math.exp(-s * 150)));
  if (b % 2 === 1) {
    add(t, .16, s => .23 * noise() * Math.exp(-s * 27) * (1 + .25 * Math.cos(2 * Math.PI * 1550 * s)));
    add(t + .012, .12, s => .13 * noise() * Math.exp(-s * 35));
  }
  add(t + .25, .11, s => noise() * .13 * Math.exp(-s * 47), b % 2 ? -.32 : .32);
  if (b > 11) add(t + .375, .04, s => noise() * .045 * Math.exp(-s * 110), -.45);
}
const chords = [[45, 52, 57, 60, 64], [41, 48, 53, 57, 60], [48, 55, 60, 64, 67], [43, 50, 55, 59, 62]];
for (let bar = 0; bar < 12; bar++) {
  const chord = chords[bar % 4];
  for (let beat = 0; beat < 4; beat++) {
    const start = bar * 2 + beat * .5;
    add(start + .03, .40, s => {
      const f = hz(chord[0]);
      const env = Math.min(1, s * 130) * Math.exp(-s * 8);
      return .24 * env * (Math.sin(2 * Math.PI * f * s) + .22 * Math.sin(4 * Math.PI * f * s));
    });
    chord.slice(2).forEach((note, j) => {
      add(start + .125, .60, s => {
        const f = hz(note + 12);
        const env = Math.min(1, s * 170) * Math.exp(-s * 9);
        return .075 * env * (Math.sin(2 * Math.PI * f * s) + .24 * Math.sin(4 * Math.PI * f * s));
      }, (j - 1) * .45);
    });
  }
  // Airy bell motif with a stereo echo.
  const motif = [chord[2] + 24, chord[4] + 12, chord[3] + 12, chord[4] + 24];
  motif.forEach((note, j) => {
    const start = bar * 2 + j * .5 + .25;
    const tone = s => .12 * Math.min(1, s * 220) * Math.exp(-s * 5) * (Math.sin(2 * Math.PI * hz(note) * s) + .25 * Math.sin(2 * Math.PI * hz(note) * 2.003 * s));
    add(start, .85, tone, -.2);
    add(start + .25, .85, s => tone(s) * .22, .6);
  });
}
// Rising swells and soft impacts mark the scene cuts.
for (const at of [3, 6, 10, 14, 18]) {
  add(at - .36, .36, s => {
    const p = s / .36;
    return .13 * Math.pow(p, 2) * (noise() * .6 + Math.sin(2 * Math.PI * (210 * s + 1200 * s * s)) * .4);
  }, -.15);
  add(at, .45, s => .22 * Math.sin(2 * Math.PI * (65 * s + .9 * (1 - Math.exp(-s * 25)))) * Math.exp(-s * 13));
}
for (let i = 0; i < 6; i++) {
  add(6.70 + i * .37, .13, s => .12 * Math.sin(2 * Math.PI * (1050 + i * 110) * s) * Math.exp(-s * 30), (i % 2 ? 1 : -1) * .3);
}
let peak = 0;
for (let i = 0; i < left.length; i++) {
  const t = i / rate;
  const fade = Math.min(1, t / .01, (seconds - t) / .32);
  left[i] = Math.tanh(left[i] * 1.15) * fade;
  right[i] = Math.tanh(right[i] * 1.15) * fade;
  peak = Math.max(peak, Math.abs(left[i]), Math.abs(right[i]));
}
const bytes = Buffer.alloc(44 + left.length * 4);
bytes.write('RIFF'); bytes.writeUInt32LE(bytes.length - 8, 4); bytes.write('WAVEfmt ', 8);
bytes.writeUInt32LE(16, 16); bytes.writeUInt16LE(1, 20); bytes.writeUInt16LE(2, 22);
bytes.writeUInt32LE(rate, 24); bytes.writeUInt32LE(rate * 4, 28); bytes.writeUInt16LE(4, 32); bytes.writeUInt16LE(16, 34);
bytes.write('data', 36); bytes.writeUInt32LE(left.length * 4, 40);
for (let i = 0; i < left.length; i++) {
  bytes.writeInt16LE(Math.round(left[i] / peak * 28500), 44 + i * 4);
  bytes.writeInt16LE(Math.round(right[i] / peak * 28500), 46 + i * 4);
}
fs.writeFileSync(path.join(__dirname, 'public', 'casper-original.wav'), bytes);
console.log('Original 24-second stereo soundtrack created, 48 kHz / 16 bit.');
