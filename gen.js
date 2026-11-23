// Study-notes generator. Reads notes/sources.json, downloads each public ICAI PDF, asks Gemini to rewrite it
// in simple words with flowcharts, and saves papers/notes/<id>.json + papers/notes/index.json.
const fs=require('fs'),path=require('path');
const KEY=process.env.GEMINI_API_KEY;if(!KEY){console.error('GEMINI_API_KEY secret is missing');process.exit(1);}
const ROOT=path.join(__dirname,'..'),OUT=path.join(ROOT,'papers','notes');fs.mkdirSync(OUT,{recursive:true});
const LIMIT=+(process.argv[2]||process.env.LIMIT||5),sleep=ms=>new Promise(r=>setTimeout(r,ms));
const src=JSON.parse(fs.readFileSync(path.join(__dirname,'sources.json'),'utf8'));
const idxF=path.join(OUT,'index.json');let idx=fs.existsSync(idxF)?JSON.parse(fs.readFileSync(idxF,'utf8')):[];
const PROMPT=u=>`You are a friendly CA teacher writing SELF-STUDY NOTES for a student who has never studied this subject and has no classes.
Source: the attached official study material. Course: ${u.course}. ${u.paper}. ${u.chapter}. ${u.unit}.
Rewrite EVERY topic of this unit in your OWN simple words (do not copy sentences). A book passage of 10 lines should become about 4 to 6 short lines, a little more or less if needed.
Keep exactly as in the source: section numbers, definitions' key terms, figures, time limits, names of cases and Acts.
Do not invent facts. If something is unclear in the source, leave it out.
Return ONLY JSON in this shape:
{"topics":[{"id":"t1","title":"topic name","section":"Act section or standard, or empty","explain":["short simple line","..."],
"flow":{"title":"what the flow shows","steps":["Box 1","Box 2","Box 3"]},
"example":"one simple everyday example","remember":["rule or number to remember"],"mistakes":["common exam mistake"],
"quiz":[{"q":"question","o":["A","B","C","D"],"a":0,"why":"one line reason"}]}]}
Rules: 3 to 8 boxes in each flow, each box max 8 words, in order of how the idea works (a process, a test, or the steps of a rule). 2 quiz questions per topic. Every topic in the unit must appear.`;
async function models(){const r=await fetch('https://generativelanguage.googleapis.com/v1beta/models?pageSize=200&key='+KEY);if(!r.ok)throw new Error('ListModels '+r.status);
  const j=await r.json();const m=(j.models||[]).filter(x=>(x.supportedGenerationMethods||[]).includes('generateContent')&&/gemini-[\d.]+-flash/.test(x.name)&&!/lite|image|tts|live|thinking|exp|preview/.test(x.name));
  m.sort((a,b)=>parseFloat(b.name.match(/gemini-([\d.]+)/)[1])-parseFloat(a.name.match(/gemini-([\d.]+)/)[1]));return m.map(x=>x.name);}
function valid(j){if(!j||!Array.isArray(j.topics)||!j.topics.length)return false;
  j.topics.forEach((t,i)=>{t.id=t.id||'t'+(i+1);t.explain=(t.explain||[]).map(String);t.remember=(t.remember||[]).map(String);t.mistakes=(t.mistakes||[]).map(String);
   t.flow=t.flow&&Array.isArray(t.flow.steps)?{title:String(t.flow.title||''),steps:t.flow.steps.map(String).slice(0,8)}:null;
   t.quiz=(t.quiz||[]).filter(q=>q&&q.q&&Array.isArray(q.o)&&q.o.length>=2&&Number.isInteger(q.a)&&q.a>=0&&q.a<q.o.length);});
  return j.topics.every(t=>t.title&&t.explain.length);}
(async()=>{
  const SKIPF=process.env.SKIP_FILE,skip=SKIPF&&fs.existsSync(SKIPF)?fs.readFileSync(SKIPF,'utf8').split('\n'):[];
  const todo=src.filter(u=>!fs.existsSync(path.join(OUT,u.id+'.json'))&&!skip.includes(u.id)).slice(0,LIMIT);
  if(!todo.length){console.log('Nothing pending. All sources done.');return;}
  const ml=await models();console.log('Models:',ml.slice(0,3).join(', '));if(!ml.length)throw new Error('No Gemini flash model found');
  for(const u of todo){
    try{
      const pr=await fetch(u.url,{headers:{'User-Agent':'Mozilla/5.0 StudifyNotes'}});if(!pr.ok)throw new Error('PDF download '+pr.status);
      const buf=Buffer.from(await pr.arrayBuffer());if(buf.length>19e6)throw new Error('PDF too large for one call');
      let out=null,lastErr='';
      for(const m of ml.slice(0,2)){for(let a=0;a<4&&!out;a++){
        let r;try{r=await fetch(`https://generativelanguage.googleapis.com/v1beta/${m}:generateContent?key=${KEY}`,{method:'POST',headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(300000),
          body:JSON.stringify({contents:[{parts:[{inlineData:{mimeType:'application/pdf',data:buf.toString('base64')}},{text:PROMPT(u)}]}],generationConfig:{temperature:0.3,maxOutputTokens:60000,responseMimeType:'application/json'}})});}
        catch(e){lastErr=m+' timed out';break;}
        if(r.status===429||r.status>=500){lastErr=m+' '+r.status;await sleep(65000+15000*a);continue;}
        if(!r.ok){lastErr=m+' '+r.status+' '+(await r.text()).slice(0,200);break;}
        const j=await r.json();const t=j.candidates&&j.candidates[0]&&j.candidates[0].content.parts.map(p=>p.text||'').join('');
        try{const o=JSON.parse(t);if(valid(o))out=o;else lastErr='invalid shape';}catch(e){lastErr='bad json';}
      }if(out)break;}
      if(!out)throw new Error('Gemini failed: '+lastErr);
      const rec={id:u.id,course:u.course,paper:u.paper,chapter:u.chapter,unit:u.unit,source:u.url,made:new Date().toISOString().slice(0,10),
        note:'AI-written summary of ICAI study material. Check the original for exact wording.',topics:out.topics};
      fs.writeFileSync(path.join(OUT,u.id+'.json'),JSON.stringify(rec));
      idx=idx.filter(x=>x.id!==u.id);idx.push({id:u.id,course:u.course,paper:u.paper,chapter:u.chapter,unit:u.unit,topics:out.topics.length});const ord={};src.forEach((x,i)=>ord[x.id]=i);idx.sort((a,b)=>(ord[a.id]??1e9)-(ord[b.id]??1e9));
      fs.writeFileSync(idxF,JSON.stringify(idx));console.log('OK',u.id,out.topics.length,'topics');
    }catch(e){console.error('FAILED',u.id,e.message);if(SKIPF)fs.appendFileSync(SKIPF,u.id+'\n');}
    await sleep(30000);
  }
})();
