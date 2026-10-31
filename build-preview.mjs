import {readFile,writeFile} from 'node:fs/promises';
const base=new URL('./',import.meta.url);
const get=f=>readFile(new URL(f,base),'utf8');
const [html,css,model,app,data]=await Promise.all(['index.html','styles.css','model.js','app.js','data/courses.json'].map(get));
const encoded=JSON.stringify(JSON.parse(data)).replace(/</g,'\\u003c');
const js=model.replaceAll('export ','')+'\n'+app.replace(/^import .*?;\n/,'').replace("fetch('./data/courses.json')",`Promise.resolve({ok:true,json:async()=>(${encoded})})`);
const out=html.replace('<link rel="stylesheet" href="styles.css">',`<style>${css}</style>`).replace('<script type="module" src="app.js"></script>',`<script type="module">${js.replaceAll('</script','<\\/script')}</script>`);
await writeFile(new URL('medical-review-preview.html',base),out);
console.log('Standalone interactive preview built');
