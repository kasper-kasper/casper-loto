// Owner-supplied artwork: deterministic layout only, no automatic event policies.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const sharp = require(process.env.PUBLICATIONS_NODE_PACKAGES ? path.join(process.env.PUBLICATIONS_NODE_PACKAGES, 'sharp') : 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root = path.resolve(__dirname, '..');
const source = path.join(root, 'assets/publications/khan-owner-v1');
const catalogPath = path.join(root, 'backend/src/k_loto/application/publication_templates.json');
const prefix = 'khan-owner-v1-';
const escape = s => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;');
const specs = {
  story: { width: 1080, height: 1920, zones: { kicker: [72,1135,936,40], title: [72,1205,936,155], value: [72,1390,936,110], description: [72,1540,936,110], fact: [72,1678,936,46] }, fonts: { kicker: 27, title: 74, value: 90, description: 34, fact: 27 }, cta: [72,1750,936,90] },
  post: { width: 1200, height: 900, zones: { kicker: [72,190,480,35], title: [72,255,480,160], value: [72,470,480,100], description: [72,635,480,100], fact: [72,788,480,50] }, fonts: { kicker: 21, title: 61, value: 66, description: 26, fact: 23 }, cta: null },
};
function background(art, mark, format) {
  const spec = specs[format], story = format === 'story';
  const brandY = story ? 76 : 52;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${spec.width}" height="${spec.height}" viewBox="0 0 ${spec.width} ${spec.height}">
    <defs><linearGradient id="top" x2="0" y2="1"><stop stop-color="#061122" stop-opacity=".9"/><stop offset="1" stop-color="#061122" stop-opacity="0"/></linearGradient><linearGradient id="copy" x2="0" y2="1"><stop stop-color="#08182e" stop-opacity="0"/><stop offset=".3" stop-color="#08182e" stop-opacity=".38"/><stop offset="1" stop-color="#08182e" stop-opacity=".6"/></linearGradient><linearGradient id="seam"><stop stop-color="#08182e"/><stop offset=".82" stop-color="#08182e"/><stop offset="1" stop-color="#08182e" stop-opacity="0"/></linearGradient></defs>
    <rect width="100%" height="100%" fill="#08182e"/>
    <image href="data:image/png;base64,${art}" x="${story ? 0 : 600}" y="0" width="${story ? 1080 : 600}" height="${story ? 1920 : 1066.667}" preserveAspectRatio="xMidYMin meet"/>
    ${story ? '<rect width="1080" height="260" fill="url(#top)"/><rect y="1100" width="1080" height="650" fill="url(#copy)"/>' : '<rect width="710" height="900" fill="url(#seam)"/>'}
    <image href="data:image/png;base64,${mark}" x="72" y="${brandY}" width="62" height="62"/>
    <text x="152" y="${brandY+25}" font-family="Arial, sans-serif" font-size="19" letter-spacing="2" fill="#E5C483">CASPER LOTO</text>
    <text x="152" y="${brandY+58}" font-family="Georgia, serif" font-size="31" fill="#FFF3DC">6 из 36</text>
    ${story ? '<rect x="72" y="1750" width="936" height="90" rx="24" fill="#E5C483"/>' : '<path d="M72 866H552" stroke="#E5C483" stroke-opacity=".4"/>'}
  </svg>`;
}
async function build(catalog) {
  const original = catalog.filter(t => !t.id.startsWith(prefix));
  const events = [...new Map(original.filter(t => t.lottery === 'khan').map(t => [t.subcategory,t.subcategoryLabel])).entries()];
  if (events.length !== 32) throw new Error('Expected the approved 32 category A labels for 6/36.');
  const manifest = JSON.parse(fs.readFileSync(path.join(source,'manifest.json'),'utf8'));
  const mark = fs.readFileSync(path.join(root,'frontend/miniapp/public/brand/logo-symbol-128-v1.png')).toString('base64');
  const templates = [], previews = [];
  for (const item of manifest.artworks) {
    const art = (await sharp(path.join(source,item.file)).png().toBuffer()).toString('base64'), formats = {};
    for (const format of ['story','post']) {
      const svg = background(art,mark,format), hash = crypto.createHash('sha256').update(svg).digest('hex').slice(0,16);
      const filename = `${prefix}${item.id}-${format}-${hash}.webp`;
      const raster = await sharp(Buffer.from(svg)).webp({quality:90}).toBuffer();
      for (const app of ['admin','miniapp']) fs.writeFileSync(path.join(root,'frontend',app,'public/assets/publications',filename),raster);
      formats[format] = {...specs[format], background:`/assets/publications/${filename}`};
      const copy = format === 'story' ? [72,1135,936,590] : [72,190,480,650];
      const preview = svg.replace('</svg>', `<text x="${copy[0]}" y="${copy[1]+28}" fill="#E5C483" font-family="Arial" font-size="${format==='story'?27:21}">ПРИМЕР · ТЕКСТ РЕДАКТОРА</text><text x="${copy[0]}" y="${format==='story'?1280:315}" fill="#FFF3DC" font-family="Georgia" font-size="${format==='story'?74:58}">Итоги тиража</text><text x="${copy[0]}" y="${format==='story'?1455:535}" fill="#E5C483" font-family="Arial" font-size="${format==='story'?90:66}">6 из 36</text><text x="${copy[0]}" y="${format==='story'?1580:678}" fill="#FFF3DC" font-family="Arial" font-size="${format==='story'?32:25}">Ваш заголовок и факты события</text>${format==='story'?'<text x="104" y="1808" fill="#08182e" font-family="Arial" font-size="30">Открыть лотерею ↗</text>':''}</svg>`);
      const index = manifest.artworks.indexOf(item);
      previews.push({input:await sharp(Buffer.from(preview)).resize(format==='story'?216:360,format==='story'?384:270).png().toBuffer(),left:(index%3)*650+(format==='story'?24:262),top:52+Math.floor(index/3)*420});
    }
    for (const [event,label] of events) templates.push({id:`${prefix}${item.id}-${event.toLowerCase().replace('.','-')}`,lottery:'khan',lotteryLabel:'6 из 36',subcategory:event,subcategoryLabel:label,compositionLabel:`Новая коллекция · ${item.name}`,accent:'#E5C483',base:'#08182E',light:'#FFF3DC',serif:true,formats});
  }
  const labels = `<svg width="1950" height="${52+420*Math.ceil(manifest.artworks.length/3)}"><rect width="100%" height="100%" fill="#08182e"/>${manifest.artworks.map((item,i)=>`<text x="${24+(i%3)*650}" y="${32+Math.floor(i/3)*420}" fill="#E5C483" font-family="Arial" font-size="18">${String(i+1).padStart(2,'0')} · ${escape(item.name)} · Stories / пост</text>`).join('')}</svg>`;
  await sharp(Buffer.from(labels)).composite(previews).png().toFile(path.join(source,'overview.png'));
  const next = [...original,...templates];
  if (new Set(next.map(t=>t.id)).size !== next.length) throw new Error('Duplicate template IDs.');
  fs.writeFileSync(catalogPath,JSON.stringify(next));
  console.log(`Preserved ${original.length} templates; added ${manifest.artworks.length} artwork pairs shared by ${events.length} event labels (${templates.length} entries). Total ${next.length}.`);
  return next;
}
module.exports = build;
if (require.main === module) build(JSON.parse(fs.readFileSync(catalogPath,'utf8'))).catch(error=>{console.error(error);process.exitCode=1;});
