// Owner-supplied B backgrounds. All editable copy sits in a centered cluster.
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const sharp = require(process.env.PUBLICATIONS_NODE_PACKAGES ? path.join(process.env.PUBLICATIONS_NODE_PACKAGES, 'sharp') : 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root = path.resolve(__dirname, '..'), dir = path.join(root, 'assets/publications/platform-b-v1');
const catalogPath = path.join(root, 'backend/src/k_loto/application/publication_templates.json');
const specs = {
  story:{width:1080,height:1920,zones:{kicker:[180,620,720,50],title:[180,690,720,150],value:[180,860,720,120],description:[180,1000,720,120],fact:[180,1140,720,60]},fonts:{kicker:29,title:70,value:88,description:34,fact:28},cta:[240,1230,600,80]},
  post:{width:1200,height:900,zones:{kicker:[240,165,720,42],title:[240,225,720,140],value:[240,390,720,95],description:[240,510,720,100],fact:[240,640,720,50]},fonts:{kicker:25,title:62,value:76,description:30,fact:26},cta:null},
};
async function build(catalog) {
  const original=catalog.filter(t=>!t.id.startsWith('platform-b-v1-'));
  const manifest=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json'),'utf8'));
  const templates=[];
  for(const art of manifest.artworks) {
    const formats={};
    for(const [format,spec] of Object.entries(specs)) {
      let raster=await sharp(path.join(dir,art.file)).resize(spec.width,spec.height,{fit:'cover',position:'centre'}).png().toBuffer();
      if(spec.cta) {
        const [x,y,w,h]=spec.cta;
        raster=await sharp(raster).composite([{input:Buffer.from(`<svg width="${spec.width}" height="${spec.height}"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="24" fill="${art.accent}"/></svg>`)}]).webp({quality:90}).toBuffer();
      } else raster=await sharp(raster).webp({quality:90}).toBuffer();
      const hash=crypto.createHash('sha256').update(raster).digest('hex').slice(0,16),filename=`platform-b-v1-${art.id}-${format}-${hash}.webp`;
      for(const app of ['admin','miniapp']) fs.writeFileSync(path.join(root,'frontend',app,'public/assets/publications',filename),raster);
      formats[format]={...spec,background:`/assets/publications/${filename}`};
    }
    for(const event of manifest.events) templates.push({id:`platform-b-v1-${art.id}-${event.code.toLowerCase().replace('.','-')}`,lottery:'casper-loto',lotteryLabel:'Casper Loto · события B',subcategory:event.code,subcategoryLabel:event.label,compositionLabel:art.name,accent:art.accent,base:art.base,light:art.light,serif:false,textAlign:'center',formats});
  }
  const next=[...original,...templates];
  if(manifest.artworks.length!==10 || manifest.events.length!==18 || new Set(next.map(t=>t.id)).size!==next.length) throw new Error('Incomplete or duplicate B catalog.');
  fs.writeFileSync(catalogPath,JSON.stringify(next));
  console.log(`Preserved ${original.length}; added ${templates.length} B choices using all ten owner backgrounds.`);
  return next;
}
module.exports=build;
if(require.main===module) build(JSON.parse(fs.readFileSync(catalogPath,'utf8'))).catch(e=>{console.error(e);process.exitCode=1;});
