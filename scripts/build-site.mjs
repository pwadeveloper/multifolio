import {cp,mkdir,rm,readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
// Explicit public output: never deploy the private admin server, credentials, or old gallery.
const out='dist';
await rm(out,{recursive:true,force:true});await mkdir(out,{recursive:true});
for(const name of ['index.html','.rsc','selected-work.rsc','pricing.rsc','works.json','tick.wav','favicon.ico','favicon.svg','favicon-48x48.png','icon-192.png','icon-512.png','apple-touch-icon.png','site.webmanifest']){
 try{await cp(path.join('mirror',name),path.join(out,name));}catch(error){if(error.code!=='ENOENT')throw error;}
}
for(const name of ['selected-work','pricing','checkout','book']){await mkdir(path.join(out,name),{recursive:true});await cp(path.join('mirror',name,'index.html'),path.join(out,name,'index.html'));}
await cp('mirror/assets',path.join(out,'assets'),{recursive:true});
await writeFile(path.join(out,'gtag-stub.js'),'window.dataLayer=window.dataLayer||[];\n');
// Keep the public metadata consistent with the new portfolio owner.
for(const name of ['selected-work/index.html','pricing/index.html','selected-work.rsc','pricing.rsc','.rsc']){
 let text=await readFile(path.join(out,name),'utf8');text=text.replaceAll('Deji Ajetomobi','Multimudia');await writeFile(path.join(out,name),text);
}
console.log('Built public portfolio in dist/');
