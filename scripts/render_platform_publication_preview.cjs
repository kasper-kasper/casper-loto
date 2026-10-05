const fs=require('node:fs'),path=require('node:path'),{createRequire}=require('node:module');
const root=process.cwd(), req=createRequire(path.join(root,'frontend/admin/package.json'));
const ts=req('typescript'),reactServer=req('react-dom/server'),React=req('react');
const sharp=require('C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
function load(file,local={}) {
  const source=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText;
  const result={};new Function('require','exports',source)((id)=>local[id]||req(id),result);return result;
}
const shared=load(path.join(root,'frontend/shared/publications.ts'));
const admin=load(path.join(root,'frontend/admin/src/PublicationArtwork.tsx'),{'../../shared/publications':shared});
const mini=load(path.join(root,'frontend/miniapp/src/PublicationArtwork.tsx'),{'../../shared/publications':shared});
const catalog=JSON.parse(fs.readFileSync(path.join(root,'backend/src/k_loto/application/publication_templates.json'),'utf8'));
const baseline=JSON.parse(require('node:child_process').execFileSync('git',['show','HEAD:backend/src/k_loto/application/publication_templates.json'],{encoding:'utf8',maxBuffer:8e6}));
if(JSON.stringify(catalog.filter(t=>!t.id.startsWith('platform-b-v1-')))!==JSON.stringify(baseline.filter(t=>!t.id.startsWith('platform-b-v1-')))) throw new Error('A changed');
const fields={kicker:'CASPER LOTO',title:'Новая общая отметка',value:'1 000 000',description:'Выигрышных билетов за всю историю',fact:'Достижение всей платформы'};
async function main() {
 const composites=[];
 for(let i=1;i<=10;i++) {
  const t=catalog.find(t=>t.id===`platform-b-v1-${String(i).padStart(2,'0')}-b1-4`);
  for(const format of ['story','post']) {
   const props={template:t,fields,format,ctaLabel:'Открыть Casper Loto'};
   const markup=reactServer.renderToStaticMarkup(React.createElement(admin.PublicationArtwork,props));
   if(markup!==reactServer.renderToStaticMarkup(React.createElement(mini.PublicationArtwork,props)))throw new Error('Renderer mismatch');
   let svg=markup.slice(markup.indexOf('<svg'),markup.indexOf('</svg>')+6);
   const url=t.formats[format].background, bytes=fs.readFileSync(path.join(root,'frontend/admin/public',url));
   if(!bytes.equals(fs.readFileSync(path.join(root,'frontend/miniapp/public',url))))throw new Error('Asset mismatch');
   svg=svg.replaceAll(url,'data:image/png;base64,'+(await sharp(bytes).png().toBuffer()).toString('base64'));
   svg=svg.replace('width="100%" height="100%"',`width="${t.formats[format].width}" height="${t.formats[format].height}"`);
   const story=format==='story', w=story?216:360,h=story?384:270;
   const buf=await sharp(Buffer.from(svg)).resize(w,h).png().toBuffer();
   composites.push({input:buf,left:24+((i-1)%2)*650+(story?0:238),top:52+Math.floor((i-1)/2)*430});
  }
 }
 const height=2202;
 const labels=`<svg width="1300" height="${height}"><rect width="100%" height="100%" fill="#14243A"/>${Array.from({length:10},(_,i)=>`<text x="${24+(i%2)*650}" y="${32+Math.floor(i/2)*430}" fill="white" font-family="Arial" font-size="18">B · ${i+1} · Story / Post</text>`).join('')}</svg>`;
 await sharp(Buffer.from(labels)).composite(composites).png().toFile(path.join(root,'assets/publications/platform-b-v1/overview.png'));
 console.log('Actual React render checked: ten paired previews; identical Admin/Mini App; all 2130 A choices unchanged.');
}
main().catch(e=>{console.error(e);process.exitCode=1});
