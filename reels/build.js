// Builds one catchy reel: ElevenLabs voice + animated captions + app screens + sound effects -> reels/out/dayNN.mp4
const fs=require('fs'),path=require('path'),{execFileSync}=require('child_process');
const {chromium}=require('playwright');
const R=__dirname,OUT=path.join(R,'out'),FR=path.join(OUT,'frames');fs.mkdirSync(FR,{recursive:true});
const vids=JSON.parse(fs.readFileSync(path.join(R,'videos.json'),'utf8'));
function istDay(){const s=fs.readFileSync(path.join(R,'start.txt'),'utf8').trim();
  const now=new Date(Date.now()+5.5*3600e3);const t0=Date.parse(s+'T00:00:00Z');
  const t1=Date.parse(now.toISOString().slice(0,10)+'T00:00:00Z');return Math.round((t1-t0)/864e5)+1;}
const day=process.argv[2]?+process.argv[2]:istDay();
const v=vids.find(x=>x.day===day);
if(!v){console.log('No video for day',day);fs.writeFileSync(path.join(OUT,'SKIP'),String(day));process.exit(0);}
const nn=String(day).padStart(2,'0'),FPS=30;
const KEY=process.env.ELEVEN_API_KEY,VOICE=process.env.ELEVEN_VOICE_ID||'aHIXlH4qG7eC13lvBlFF';
const dur=f=>parseFloat(execFileSync('ffprobe',['-v','error','-show_entries','format=duration','-of','csv=p=0',f]).toString());
const sh=(...a)=>execFileSync('ffmpeg',['-y','-loglevel','error',...a],{stdio:'inherit'});
const PAGE=fs.readFileSync(path.join(R,'scene.html'),'utf8');
(async()=>{
  const audio=path.join(OUT,`day${nn}.mp3`);
  const text=v.scenes.map(x=>x.vo||'').filter(Boolean).join(' ');
  let al;
  if(process.env.MOCK_AUDIO){ // local test only
    fs.copyFileSync(process.env.MOCK_AUDIO,audio);const d=dur(audio),n=text.length;
    al={character_start_times_seconds:[...Array(n)].map((_,i)=>0.2+(d-0.5)*i/n),character_end_times_seconds:[...Array(n)].map((_,i)=>0.2+(d-0.5)*(i+1)/n)};
  }else{
    if(!KEY)throw new Error('ELEVEN_API_KEY secret is missing');
    const r=await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE}/with-timestamps?output_format=mp3_44100_128`,{method:'POST',
      headers:{'xi-api-key':KEY,'Content-Type':'application/json'},body:JSON.stringify({text,model_id:'eleven_multilingual_v2'})});
    if(!r.ok)throw new Error('ElevenLabs '+r.status+' '+await r.text());
    const j=await r.json();fs.writeFileSync(audio,Buffer.from(j.audio_base64,'base64'));al=j.alignment||j.normalized_alignment;
  }
  const st=al.character_start_times_seconds,en=al.character_end_times_seconds,adur=dur(audio),total=adur+0.9;
  // scene start = time its first spoken character begins
  let off=0;const sOff=[],start=[];
  v.scenes.forEach((s,i)=>{if(s.vo){sOff[i]=off;start[i]=i===0?0:st[Math.min(off,st.length-1)];off+=s.vo.length+1;}else{sOff[i]=null;start[i]=null;}});
  for(let i=0;i<v.scenes.length;i++){if(start[i]===null){let k=i-1;while(k>=0&&start[k]===null)k--;
    let e=i+1;while(e<v.scenes.length&&start[e]===null)e++;const endT=e<v.scenes.length?start[e]:total;
    const n=e-k,t0=start[k],step=(endT-t0)/n;for(let q=k;q<e;q++)start[q]=t0+step*(q-k);}}
  // words with timing
  const words=[];let pos=0;
  text.split(' ').forEach(w=>{const i0=pos,i1=pos+w.length-1;pos+=w.length+1;
    let sc=0;v.scenes.forEach((s,i)=>{if(sOff[i]!==null&&sOff[i]<=i0)sc=i;});
    words.push({w,t0:st[Math.min(i0,st.length-1)],t1:en[Math.min(i1,en.length-1)],sc});});
  const scenes=v.scenes.map((s,i)=>{
    let img='';if(s.type==='shot'){const p=path.join(R,'shots',s.shot+'.png');
      if(!fs.existsSync(p))throw new Error('Missing screen image: reels/shots/'+s.shot+'.png');
      img='data:image/png;base64,'+fs.readFileSync(p).toString('base64');}
    return {type:s.type,title:s.title,sub:s.sub||'',caption:s.caption||'',img,t0:start[i],t1:i+1<v.scenes.length?start[i+1]:total};});
  // render frames
  const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920}});
  await p.setContent(process.env.MOCK_AUDIO?PAGE.replace(/<link[^>]*>/,''):PAGE,{waitUntil:process.env.MOCK_AUDIO?'load':'networkidle'});
  await p.evaluate(D=>init(D),{scenes,words,total});await p.waitForTimeout(500);
  const N=Math.ceil(total*FPS);
  for(let f=0;f<N;f++){await p.evaluate(t=>draw(t),f/FPS);
    await p.screenshot({path:path.join(FR,`f${String(f).padStart(5,'0')}.jpg`),type:'jpeg',quality:88});}
  await b.close();
  // sound effects: a short whoosh at every scene change, a pop on the last scene
  const wh=path.join(OUT,'whoosh.wav');
  sh('-f','lavfi','-i','anoisesrc=d=0.35:c=pink:a=0.6','-af','highpass=f=500,lowpass=f=6000,afade=t=in:d=0.12,afade=t=out:st=0.12:d=0.23',wh);
  const cuts=start.slice(1);const fc=[];const ins=['-framerate',String(FPS),'-i',path.join(FR,'f%05d.jpg'),'-i',audio];
  cuts.forEach(()=>ins.push('-i',wh));
  const music=path.join(R,'music','bg.mp3');const hasM=fs.existsSync(music);if(hasM)ins.push('-stream_loop','-1','-i',music);
  cuts.forEach((t,i)=>fc.push(`[${i+2}:a]volume=0.5,adelay=${Math.max(0,Math.round((t-0.05)*1000))}|${Math.max(0,Math.round((t-0.05)*1000))}[w${i}]`));
  const mix=['[1:a]'].concat(cuts.map((_,i)=>`[w${i}]`));let nIn=mix.length;
  if(hasM){fc.push(`[${cuts.length+2}:a]volume=0.07[m]`);mix.push('[m]');nIn++;}
  fc.push(`${mix.join('')}amix=inputs=${nIn}:duration=first:normalize=0[a]`);
  const outf=path.join(OUT,`day${nn}.mp4`);
  sh(...ins,'-filter_complex',fc.join(';'),'-map','0:v','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-shortest',outf);
  fs.rmSync(FR,{recursive:true,force:true});
  console.log('Built',outf,total.toFixed(1)+'s');
})().catch(e=>{console.error(e);process.exit(1);});
