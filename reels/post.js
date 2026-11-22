// Posts reels/out/dayNN.mp4 to Instagram (Instagram API with Instagram Login, resumable upload)
const fs=require('fs'),path=require('path');
const R=__dirname,OUT=path.join(R,'out');
if(fs.existsSync(path.join(OUT,'SKIP'))){console.log('Skipped: no video today');process.exit(0);}
const day=+process.argv[2];const nn=String(day).padStart(2,'0');
const v=JSON.parse(fs.readFileSync(path.join(R,'videos.json'),'utf8')).find(x=>x.day===day);
const TOKEN=process.env.IG_TOKEN,ID=process.env.IG_USER_ID;
if(!TOKEN||!ID||!v)throw new Error('Missing IG_TOKEN, IG_USER_ID or video entry');
const base='https://graph.instagram.com/v24.0',sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function j(url,opt){const r=await fetch(url,opt);const t=await r.text();let o;try{o=JSON.parse(t)}catch{o={raw:t}}
  if(!r.ok||o.error)throw new Error(r.status+' '+t);return o;}
(async()=>{
  const buf=fs.readFileSync(path.join(OUT,`day${nn}.mp4`));
  const c=await j(`${base}/${ID}/media`,{method:'POST',body:new URLSearchParams({media_type:'REELS',upload_type:'resumable',
    caption:v.caption,share_to_feed:'true',access_token:TOKEN})});
  await j(c.uri||`https://rupload.facebook.com/ig-api-upload/v24.0/${c.id}`,{method:'POST',
    headers:{Authorization:'OAuth '+TOKEN,offset:'0',file_size:String(buf.length)},body:buf});
  for(let i=0;i<40;i++){
    const s=await j(`${base}/${c.id}?fields=status_code,status&access_token=${TOKEN}`);
    console.log('status',s.status_code);
    if(s.status_code==='FINISHED')break;
    if(s.status_code==='ERROR'||s.status_code==='EXPIRED')throw new Error('Processing failed: '+JSON.stringify(s));
    await sleep(15000);}
  const p=await j(`${base}/${ID}/media_publish`,{method:'POST',body:new URLSearchParams({creation_id:c.id,access_token:TOKEN})});
  console.log('Published media id',p.id);
})().catch(e=>{console.error(e.message);process.exit(1);});
