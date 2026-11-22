// Builds one reel: ElevenLabs voice-over + app screens -> reels/out/dayNN.mp4
const fs=require('fs'),path=require('path'),{execFileSync}=require('child_process');
const {chromium}=require('playwright');
const R=__dirname,OUT=path.join(R,'out');fs.mkdirSync(OUT,{recursive:true});
const vids=JSON.parse(fs.readFileSync(path.join(R,'videos.json'),'utf8'));
function istDay(){const s=fs.readFileSync(path.join(R,'start.txt'),'utf8').trim();
  const now=new Date(Date.now()+5.5*3600e3);const t0=Date.parse(s+'T00:00:00Z');
  const t1=Date.parse(now.toISOString().slice(0,10)+'T00:00:00Z');return Math.round((t1-t0)/864e5)+1;}
const day=process.argv[2]?+process.argv[2]:istDay();
const v=vids.find(x=>x.day===day);
if(!v){console.log('No video for day',day,'- nothing to do');fs.writeFileSync(path.join(OUT,'SKIP'),String(day));process.exit(0);}
const nn=String(day).padStart(2,'0');
const KEY=process.env.ELEVEN_API_KEY,VOICE=process.env.ELEVEN_VOICE_ID||'aHIXlH4qG7eC13lvBlFF';
if(!KEY)throw new Error('ELEVEN_API_KEY secret is missing');
const dur=f=>parseFloat(execFileSync('ffprobe',['-v','error','-show_entries','format=duration','-of','csv=p=0',f]).toString());
const BG='background:linear-gradient(160deg,#1e1b4b,#4338ca 60%,#7c3aed)';
const css=`*{margin:0;box-sizing:border-box}body{width:1080px;height:1920px;${BG};font-family:Poppins,Inter,sans-serif;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:80px}
h1{font-size:92px;line-height:1.18;font-weight:800}h2{font-size:64px;font-weight:700;line-height:1.2;margin-bottom:50px}.a{color:#fbbf24}.s{font-size:46px;opacity:.9;margin-top:40px}
.ph{width:700px;height:1240px;border-radius:60px;border:14px solid #0f172a;overflow:hidden;background:#fff;box-shadow:0 30px 80px #0008}.ph img{width:100%;display:block}
.cap{font-size:60px;font-weight:700;margin-top:50px;line-height:1.2}.btn{background:#fbbf24;color:#1e1b4b;font-size:58px;font-weight:800;padding:32px 68px;border-radius:70px;margin-top:60px}`;
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');
function html(s){
  if(s.type==='shot'){const p=path.join(R,'shots',s.shot+'.png');
    const img=fs.existsSync(p)?`<div class="ph"><img src="data:image/png;base64,${fs.readFileSync(p).toString('base64')}"></div>`:'';
    return `<h2>${esc(s.title)} 🎯</h2>${img}<div class="cap"><span class="a">${esc(s.caption)}</span></div>`;}
  if(s.type==='cta')return `<h1><span class="a">${esc(s.title)}</span></h1><div class="s">${esc(s.sub)}</div><div class="btn">Studify CA</div>`;
  return `<h1>${esc(s.title)}</h1>${s.sub?`<div class="s">${esc(s.sub)}</div>`:''}`;}
(async()=>{
  // 1. voice-over
  const audio=path.join(OUT,`day${nn}.mp3`);
  const r=await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE}?output_format=mp3_44100_128`,{method:'POST',
    headers:{'xi-api-key':KEY,'Content-Type':'application/json'},body:JSON.stringify({text:v.voiceover,model_id:'eleven_multilingual_v2'})});
  if(!r.ok)throw new Error('ElevenLabs '+r.status+' '+await r.text());
  fs.writeFileSync(audio,Buffer.from(await r.arrayBuffer()));
  const total=dur(audio)+0.8;
  // 2. frames
  const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920}});
  const sum=v.scenes.reduce((a,s)=>a+s.w,0);let list='';
  for(let i=0;i<v.scenes.length;i++){const s=v.scenes[i];
    await p.setContent(`<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800&display=swap" rel="stylesheet"><style>${css}</style>${html(s)}`,{waitUntil:'networkidle'});
    await p.waitForTimeout(400);const f=path.join(OUT,`f${nn}_${i}.png`);await p.screenshot({path:f});
    list+=`file '${f}'\nduration ${(total*s.w/sum).toFixed(3)}\n`;}
  list+=`file '${path.join(OUT,`f${nn}_${v.scenes.length-1}.png`)}'\n`;await b.close();
  fs.writeFileSync(path.join(OUT,'list.txt'),list);
  // 3. mix (optional quiet background music at reels/music/bg.mp3)
  const music=path.join(R,'music','bg.mp3'),outf=path.join(OUT,`day${nn}.mp4`);
  const a=['-y','-loglevel','error','-f','concat','-safe','0','-i',path.join(OUT,'list.txt'),'-i',audio];
  if(fs.existsSync(music))a.push('-stream_loop','-1','-i',music,'-filter_complex','[2:a]volume=0.08[m];[1:a][m]amix=inputs=2:duration=first[a]','-map','0:v','-map','[a]');
  else a.push('-map','0:v','-map','1:a');
  a.push('-vf','fps=30,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','23','-c:a','aac','-b:a','128k','-shortest',outf);
  execFileSync('ffmpeg',a,{stdio:'inherit'});
  console.log('Built',outf,total.toFixed(1)+'s');
})().catch(e=>{console.error(e);process.exit(1);});
