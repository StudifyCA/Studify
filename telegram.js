// Posts today's YouTube Short link to the Telegram channel
const fs=require('fs'),path=require('path');
const R=__dirname,OUT=path.join(R,'out');
const idf=path.join(OUT,'yt_id.txt');
if(!fs.existsSync(idf)){console.log('No YouTube id, nothing to post');process.exit(0);}
const id=fs.readFileSync(idf,'utf8').trim();
const day=+process.argv[2];
const v=JSON.parse(fs.readFileSync(path.join(R,'videos.json'),'utf8')).find(x=>x.day===day)||{};
const {TG_BOT_TOKEN:T,TG_CHAT_ID:C}=process.env;
if(!T||!C)throw new Error('Missing TG_BOT_TOKEN or TG_CHAT_ID');
const first=String(v.title||String(v.caption||'').split('\n')[0].replace(/#[\w]+/g,'').trim()||('Studify CA Day '+day)).slice(0,120);
const text=`🎬 Day ${day}: ${first}\n\n▶️ Watch: https://youtube.com/shorts/${id}\n📱 Free CA study app: https://studifyca.github.io/Studify/`;
(async()=>{
  const r=await fetch(`https://api.telegram.org/bot${T}/sendMessage`,{method:'POST',headers:{'content-type':'application/json'},
    body:JSON.stringify({chat_id:C,text,disable_web_page_preview:false})});
  const t=await r.text();if(!r.ok)throw new Error(r.status+' '+t);console.log('Telegram posted');
})().catch(e=>{console.error(e.message);process.exit(1);});
