const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const root = __dirname;
const bin = path.join(root, 'node_modules', '@remotion', 'compositor-win32-x64-msvc');
const file = path.join(root, 'out', 'casper-loto-reels-1080x1920.mp4');
const run = (exe, args, binary = false) => {
  const result = spawnSync(path.join(bin, exe), args, {windowsHide: true, encoding: binary ? undefined : 'utf8', maxBuffer: 32 * 1024 * 1024});
  if (result.status !== 0) throw new Error(String(result.stderr || result.error));
  return result.stdout;
};
const metadata = JSON.parse(run('ffprobe.exe', ['-v', 'error', '-show_streams', '-show_format', '-of', 'json', file]));
const v = metadata.streams.find(s => s.codec_type === 'video');
const a = metadata.streams.find(s => s.codec_type === 'audio');
if (v.width !== 1080 || v.height !== 1920 || v.codec_name !== 'h264' || v.pix_fmt !== 'yuv420p' || v.r_frame_rate !== '30/1' || Number(v.nb_frames) !== 720) throw new Error('Unexpected video stream');
if (!a || a.codec_name !== 'aac' || a.channels !== 2 || Number(a.sample_rate) !== 48000) throw new Error('Unexpected audio stream');
if (Math.abs(Number(metadata.format.duration) - 24) > .1) throw new Error('Unexpected duration');
run('ffmpeg.exe', ['-v', 'error', '-i', file, '-c:v', 'rawvideo', '-c:a', 'pcm_s16le', '-f', 'null', '-']);
const wav = run('ffmpeg.exe', ['-v', 'error', '-i', file, '-map', '0:a:0', '-f', 'wav', '-acodec', 'pcm_s16le', '-'], true);
let dataOffset = 12;
while (dataOffset + 8 < wav.length && wav.toString('ascii', dataOffset, dataOffset + 4) !== 'data') {
  const size = wav.readUInt32LE(dataOffset + 4);
  dataOffset += 8 + size + (size % 2);
}
if (dataOffset + 8 >= wav.length) throw new Error('WAV data chunk missing');
const pcm = wav.subarray(dataOffset + 8);
let peak = 0, sum = 0, clipped = 0;
for (let i = 0; i < pcm.length; i += 2) {
  const n = pcm.readInt16LE(i) / 32768;
  peak = Math.max(peak, Math.abs(n)); sum += n * n;
  if (Math.abs(n) > .999) clipped++;
}
const rms = Math.sqrt(sum / (pcm.length / 2));
if (clipped || rms < .01) throw new Error('Clipped or near-silent audio');
const data = fs.readFileSync(file);
const atoms = [];
for (let offset = 0; offset + 8 <= data.length;) {
  let size = data.readUInt32BE(offset);
  const type = data.toString('ascii', offset + 4, offset + 8);
  if (size === 1) size = Number(data.readBigUInt64BE(offset + 8));
  atoms.push({type, offset, size});
  if (size < 8) break;
  offset += size;
}
const fastStart = atoms.find(x => x.type === 'moov')?.offset < atoms.find(x => x.type === 'mdat')?.offset;
const report = {
  file: path.basename(file), bytes: fs.statSync(file).size,
  durationSeconds: Number(metadata.format.duration), width: v.width, height: v.height,
  fps: v.r_frame_rate, frames: Number(v.nb_frames), videoCodec: v.codec_name, pixelFormat: v.pix_fmt,
  audioCodec: a.codec_name, audioChannels: a.channels, audioSampleRate: Number(a.sample_rate),
  audioSamplePeakDbFS: Number((20 * Math.log10(peak)).toFixed(2)),
  audioRmsDbFS: Number((20 * Math.log10(rms)).toFixed(2)), clippedAudioSamples: clipped,
  fullDecode: 'passed', fastStart, qaFrames: [45,135,255,375,495,630],
  checkedAtUtc: new Date().toISOString(),
};
fs.writeFileSync(path.join(root, 'out', 'verification.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
