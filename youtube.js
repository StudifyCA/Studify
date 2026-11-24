// Uploads reels/out/dayNN.mp4 to YouTube as a Short (Data API v3, resumable upload)
const fs=require('fs'),path=require('path');
const R=__dirname,OUT=path.join(R,'out');
if(fs.existsSync(path.join(OUT,'SKIP'))){console.log('Skipped: no video today');process.exit(0);}
const day=+process.argv[2];const nn=String(day).padStart(2,'0');
const v=JSON.parse(fs.readFileSync(path.join(R,'videos.json'),'utf8')).find(x=>x.day===day);
const {YT_CLIENT_ID:CID,YT_CLIENT_SECRET:CS,YT_REFRESH_TOKEN:RT}=process.env;
if(!CID||!CS||!RT||!v)throw new Error('Missing YT secrets or video entry');
const cap=String(v.caption||'');
const tags=[...new Set((cap.match(/#[\w]+/g)||[]).map(t=>t.slice(1)))].slice(0,15);
let title=String(v.title||cap.split('\n')[0].replace(/#[\w]+/g,'').trim()||('Studify CA Day '+day)).slice(0,90);
if(!/#shorts/i.test(title)&&title.length<=91)title+=' #Shorts';
const desc=(cap+(/#shorts/i.test(cap)?'':'\n\n#Shorts')).slice(0,4900);
async function j(url,opt){const r=await fetch(url,opt);const t=await r.text();if(!r.ok)throw new Error(r.status+' '+t);return {r,t};}
(async()=>{
  const tk=JSON.parse((await j('https://oauth2.googleapis.com/token',{method:'POST',
    headers:{'content-type':'application/x-www-form-urlencoded'},
    body:new URLSearchParams({client_id:CID,client_secret:CS,refresh_token:RT,grant_type:'refresh_token'})})).t).access_token;
  const buf=fs.readFileSync(path.join(OUT,`day${nn}.mp4`));
  const meta={snippet:{title,description:desc,tags,categoryId:'27',defaultLanguage:'en'},
    status:{privacyStatus:'public',selfDeclaredMadeForKids:false}};
  const init=await j('https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',{method:'POST',
    headers:{Authorization:'Bearer '+tk,'content-type':'application/json; charset=UTF-8','X-Upload-Content-Type':'video/mp4','X-Upload-Content-Length':String(buf.length)},
    body:JSON.stringify(meta)});
  const loc=init.r.headers.get('location');
  const up=await j(loc,{method:'PUT',headers:{'content-type':'video/mp4','content-length':String(buf.length)},body:buf});
  console.log('YouTube uploaded, video id',JSON.parse(up.t).id);
})().catch(e=>{console.error(e.message);process.exit(1);});
