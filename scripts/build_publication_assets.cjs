// Compile approved artwork into versioned runtime backgrounds; no event rules.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const sharp = require(process.env.PUBLICATIONS_NODE_PACKAGES ? path.join(process.env.PUBLICATIONS_NODE_PACKAGES,'sharp') : 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root=path.resolve(__dirname,'..'), source=path.join(root,'design/publications/category-a');
const manifest=JSON.parse(fs.readFileSync(path.join(source,'manifest.json'),'utf8'));
async function main(){
  const catalog=[];
  for(const row of manifest.templates){
    const game=manifest.games.find(g=>g.id===row.gameIdentity);
    const item={id:row.id,lottery:row.lottery,lotteryLabel:row.lotteryLabel,subcategory:row.subcategory,subcategoryLabel:row.subcategoryLabel,compositionLabel:row.compositionLabel,accent:game.accent,base:game.base,light:game.light,serif:!['pulse','flash','code'].includes(game.id),formats:{}};
    for(const format of ['story','post']){
      const spec=row.formats[format];
      let svg=fs.readFileSync(path.join(source,spec.background),'utf8');
      svg=svg.replace(/href="([^"]+)"/g,(_,href)=>`href="data:image/png;base64,${fs.readFileSync(path.resolve(path.dirname(path.join(source,spec.background)),href)).toString('base64')}"`);
      const hash=crypto.createHash('sha256').update(svg).digest('hex').slice(0,16);
      const filename=`${row.id}-${format}-${hash}.webp`, url=`/assets/publications/${filename}`;
      const targets=['miniapp','admin'].map(app=>path.join(root,'frontend',app,'public',url));
      if(!fs.existsSync(targets[0])){const raster=await sharp(Buffer.from(svg)).webp({quality:88}).toBuffer();for(const target of targets){fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,raster);}}
      else if(!fs.existsSync(targets[1])){fs.mkdirSync(path.dirname(targets[1]),{recursive:true});fs.copyFileSync(targets[0],targets[1]);}
      item.formats[format]={width:spec.width,height:spec.height,background:url,zones:spec.textSafeZones,fonts:spec.fontSizes,cta:spec.ctaSafeZone};
    }
    catalog.push(item);
  }
  const output=path.join(root,'backend/src/k_loto/application/publication_templates.json');
  fs.writeFileSync(output,JSON.stringify(catalog));console.log(`Compiled ${catalog.length} template pairs.`);
  await require('./build_khan_publication_assets.cjs')(catalog);
}
main().catch(error=>{console.error(error);process.exitCode=1;});
