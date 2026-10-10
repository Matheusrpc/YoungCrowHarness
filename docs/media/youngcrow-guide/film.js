/* YoungCrow film. Original artwork stays intact; layout and motion are procedural.
   All shell commands below are display text. This presentation never executes them. */
const scenes = [
  {seconds:7, kind:'hero', chapter:'UM GUIA PARA COMEÇAR', title:['YoungCrow'], accent:'Da ideia à primeira missão.', body:['Seu projeto. Suas decisões.','Contexto para continuar.'], tag:'CLAUDE CODE  /  CODEX'},
  {seconds:11, chapter:'01 / PREPARE O ESPAÇO', title:['Tudo começa','com o seu projeto.'], body:['Clone o harness ao lado da pasta do produto.','Tenha Bash, Git e Python 3 disponíveis.'], code:['git clone \\', '  --branch feat/isolated-executor \\', '  https://github.com/Matheusrpc/YoungCrowHarness.git'], label:'TERMINAL · GIT BASH NO WINDOWS', note:'Esta prévia acompanha a branch do PR #24.', diagram:'folders'},
  {seconds:15, chapter:'02 / PROJETO NOVO', title:['Comece com','um ponto de retorno.'], body:['Use --trial e guarde o caminho de recuperação.'], code:['bash YoungCrowHarness/setup.sh meu-projeto \\', '  --trial --client both --nome "Meu Projeto"','cd meu-projeto','git init','git check-ignore --no-index .env','git ls-files -- .env'], label:'TERMINAL · A PARTIR DA PASTA PAI', note:'O primeiro check mostra .env. O último deve ficar vazio.\nO trial pula plugins e downloads de skills.'},
  {seconds:15, chapter:'02 / SE O PROJETO JÁ EXISTE', title:['Preserve o que','você já construiu.'], body:['Salve o trabalho atual e faça uma branch de adoção.','O clone do harness deve ficar numa pasta irmã.'], code:['git status --short','git switch -c chore/adotar-youngcrow','git ls-files -- .env','bash ../YoungCrowHarness/setup.sh . \\', '  --trial --client both --nome "Meu Produto"'], label:'TERMINAL · NA RAIZ DO SEU PRODUTO', note:'Se .env estiver rastreado, resolva antes do setup.\nRevise arquivos novos e mantidos; rode os testes existentes.'},
  {seconds:11, chapter:'03 / ABRA O SEU CLIENTE', title:['Dê ao agente','as regras da casa.'], body:['Abra a pasta do produto no Claude Code ou Codex.','Preencha objetivo, testes, permissões e publicação.'], cards:[['CLAUDE.md + AGENTS.md','Regras e limites do projeto'],['Skills, hooks e MCPs','Revise acesso e confiança no cliente']], note:'Reabra a sessão após o setup e confira as skills.\nMantenha credenciais somente no ambiente local.'},
  {seconds:10, chapter:'04 / PERSONALIZE', title:['Conte o que','quer construir.'], body:['A personalizer registra o produto, as decisões','e as perguntas que ainda precisam de resposta.'], skill:'yc-personalizer', quote:'Quero criar uma agenda de atendimentos.', note:'Projeto existente? Peça a leitura do código e das decisões\nantes de adaptar as instruções.'},
  {seconds:9, chapter:'05 / CONFIGURE', title:['Escolha como','o trabalho acontece.'], body:['Defina modelos, esforço e limites por papel.','As escolhas ficam registradas para este projeto.'], skill:'yc-config', tags:['PM','TECH LEAD','DEV','QA'], note:'Configurar um papel não inicia um agente.\nO instalador não escolhe os modelos por você.'},
  {seconds:12, chapter:'06 / PREPARE A MISSÃO', title:['Uma ideia.','Entregas verificáveis.'], body:['PM define objetivo, features e critérios de aceite.','Tech Lead organiza tarefas e dependências.'], skill:'yc-missao', tags:['OBJETIVO','TAREFAS','ACEITE'], note:'Esses papéis são conduzidos na sessão atual.\nSelecione as features e priorize todas as tarefas da missão.'},
  {seconds:8, chapter:'07 / CONSULTE O ESTADO', title:['Saiba exatamente','o que falta.'], body:['Confira a preparação, os bloqueios','e a próxima ação da missão.'], skill:'yc-status', badge:'prepared', note:'prepared significa missão preparada.\nA execução automática ainda está em desenvolvimento.'},
  {seconds:10, chapter:'08 / CONTINUE EM OUTRA SESSÃO', title:['Guarde o contexto.','Retome o trabalho.'], body:['Registre decisões, resultados de testes','e a próxima ação no vault.'], quote:'Use retrieve-memory para retomar esta feature.', cards:[['VAULT','Decisões → evidências → próxima ação']], note:'Encerre o escritor atual antes de trocar de cliente.\nA nova sessão consulta os registros do projeto.'},
  {seconds:10, kind:'end', chapter:'O QUE VOCÊ PODE FAZER HOJE', title:['Prepare agora.','Construa com contexto.'], body:['Setup, personalização, missões e memória disponíveis.','Execução com acompanhamento na sessão atual.'], roadmap:['PM','TECH LEAD','DEV','QA','RELEASE'], note:'Executor autônomo e coordenação automática:\nem desenvolvimento.', tag:'GUIA COMPLETO · docs/USAGE.md'},
  ...(window.DEMO_SCENES||[])
];
let cursor=0;
for(const s of scenes){s.start=cursor;cursor+=s.seconds;}
const DURATION=cursor;
const canvas=document.querySelector('#film'), ctx=canvas.getContext('2d',{alpha:false});
const params=new URLSearchParams(location.search);
let portrait=params.get('format')==='portrait', W=1920,H=1080;
let playing=false, time=0, origin=0;
const gold='#dfba78', ivory='#f3e7cf', muted='#bbbabd';
const clamp=x=>Math.max(0,Math.min(1,x));
const ease=x=>1-Math.pow(1-clamp(x),3);
const fade=(t,start=0,length=.6)=>ease((t-start)/length);
const art=new Image();
art.src=window.FILM_ART||'../../../assets/vitral.png';
const fontRoot=window.FILM_FONTS||{};
const fonts=[['Cinzel','cinzel-latin.woff2','600'],['Manrope','manrope-latin.woff2','400'],['Manrope','manrope-bold.woff2','700']];
const loaded=Promise.all(fonts.map(async([family,file,weight])=>{
 const face=new FontFace(family,`url(${fontRoot[file]||'vendor/'+file})`,{weight});
 await face.load();document.fonts.add(face);
}));

// Three.js supplies a slowly turning rose window, glass facets and a field of light.
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:true});
renderer.setClearColor(0x000000,0);
renderer.setPixelRatio(1);
renderer.outputColorSpace=THREE.SRGBColorSpace;
const world=new THREE.Scene();
const camera=new THREE.PerspectiveCamera(38,16/9,.1,50);
camera.position.z=8;
const rose=new THREE.Group();world.add(rose);
const colors=[0x275eb5,0xa52943,0xca963e,0x26775a,0x674395,0x268391];
const goldLine=new THREE.LineBasicMaterial({color:0xd8b16a,transparent:true,opacity:.5});
for(let ring=0;ring<3;ring++){
 const count=[12,24,36][ring],inner=[.24,1.04,1.75][ring],outer=[1.0,1.68,2.02][ring];
 for(let k=0;k<count;k++){
  const a=k/count*Math.PI*2,da=Math.PI/count*.82;
  const shape=new THREE.Shape();
  shape.moveTo(Math.cos(a)*inner,Math.sin(a)*inner);
  shape.lineTo(Math.cos(a-da)*(inner+outer)/2,Math.sin(a-da)*(inner+outer)/2);
  shape.lineTo(Math.cos(a)*outer,Math.sin(a)*outer);
  shape.lineTo(Math.cos(a+da)*(inner+outer)/2,Math.sin(a+da)*(inner+outer)/2);
  shape.closePath();
  const geo=new THREE.ShapeGeometry(shape);
  const glass=new THREE.Mesh(geo,new THREE.MeshBasicMaterial({color:colors[(k+ring)%6],side:THREE.DoubleSide,transparent:true,opacity:.22}));
  glass.position.z=Math.sin(k*1.9)*.08;rose.add(glass);
  const outline=new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(shape.getPoints()),goldLine);
  outline.position.z=glass.position.z+.01;rose.add(outline);
 }
}
for(const radius of [.17,1.02,1.72,2.08,2.18]){
 const points=Array.from({length:129},(_,k)=>new THREE.Vector3(Math.cos(k/128*Math.PI*2)*radius,Math.sin(k/128*Math.PI*2)*radius,0));
 rose.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),goldLine));
}
let seed=83;const rnd=()=>{seed=(seed*16807)%2147483647;return(seed-1)/2147483646;};
const dustPositions=new Float32Array(165*3);
for(let i=0;i<dustPositions.length;i+=3){dustPositions[i]=(rnd()-.5)*15;dustPositions[i+1]=(rnd()-.5)*9;dustPositions[i+2]=(rnd()-.5)*4;}
const dustGeo=new THREE.BufferGeometry();dustGeo.setAttribute('position',new THREE.BufferAttribute(dustPositions,3));
const dust=new THREE.Points(dustGeo,new THREE.PointsMaterial({color:0xe8c58a,size:.018,transparent:true,opacity:.5,depthWrite:false}));world.add(dust);
const facets=new THREE.Group();world.add(facets);
for(let i=0;i<12;i++){
 const shape=new THREE.Shape();shape.moveTo(0,.28);shape.lineTo(.15,0);shape.lineTo(0,-.28);shape.lineTo(-.15,0);shape.closePath();
 const mesh=new THREE.Mesh(new THREE.ShapeGeometry(shape),new THREE.MeshBasicMaterial({color:colors[i%6],transparent:true,opacity:.18,side:THREE.DoubleSide}));
 mesh.position.set((rnd()-.5)*14,(rnd()-.5)*8,-1-rnd()*3);mesh.userData={x:mesh.position.x,y:mesh.position.y,phase:rnd()*6};facets.add(mesh);
}

function size(){
 [W,H]=portrait?[1080,1920]:[1920,1080];canvas.width=W;canvas.height=H;
 // Background renders at 75%; lettering is always rendered at full output resolution.
 renderer.setSize(Math.round(W*.75),Math.round(H*.75),false);lastGlassTime=null;lastDemoBackground=null;
 camera.aspect=W/H;camera.updateProjectionMatrix();
 document.querySelector('#format').value=portrait?'portrait':'landscape';
}
function text(value,x,y,sz=30,color=ivory,font='Manrope',weight='400'){
 ctx.fillStyle=color;ctx.font=`${weight} ${sz}px ${font}`;ctx.textBaseline='top';ctx.fillText(value,x,y);
}
function tracked(value,x,y,sz=20,spacing=4,color=gold){
 ctx.font=`700 ${sz}px Manrope`;ctx.fillStyle=color;ctx.textBaseline='top';
 for(const c of value){ctx.fillText(c,x,y);x+=ctx.measureText(c).width+spacing;}
}
function wrap(value,maxWidth,sz=32,font='Manrope',weight='400'){
 ctx.font=`${weight} ${sz}px ${font}`;
 const rows=[];
 for(const paragraph of value.split('\n')){
  let line='';for(const word of paragraph.split(' ')){
   const next=line?line+' '+word:word;
   if(ctx.measureText(next).width>maxWidth&&line){rows.push(line);line=word;}else line=next;
  }rows.push(line);
 }return rows;
}
function paragraph(value,x,y,width,sz,color=muted,lineHeight=1.5){
 for(const line of wrap(value,width,sz)){text(line,x,y,sz,color);y+=sz*lineHeight;}return y;
}
function line(x,y,width,alpha=1){ctx.save();ctx.globalAlpha*=alpha;ctx.fillStyle=gold;ctx.fillRect(x,y,width,1);ctx.restore();}
function panel(x,y,w,h){ctx.fillStyle='#101824e8';ctx.fillRect(x,y,w,h);ctx.strokeStyle='#b793564a';ctx.lineWidth=1;ctx.strokeRect(x+.5,y+.5,w-1,h-1);ctx.fillStyle=gold;ctx.fillRect(x,y,3,Math.min(h,54));}
function diamond(x,y,r=5){ctx.beginPath();ctx.moveTo(x,y-r);ctx.lineTo(x+r,y);ctx.lineTo(x,y+r);ctx.lineTo(x-r,y);ctx.closePath();ctx.fill();}
function lettering(lines,x,y,width,sz,t){
 for(let row=0;row<lines.length;row++){
  const str=lines[row];ctx.font=`600 ${sz}px Cinzel`;
  const actual=Math.min(sz,sz*width/Math.max(width,ctx.measureText(str).width));
  ctx.font=`600 ${actual}px Cinzel`;let px=x;
  for(let j=0;j<str.length;j++){
   const p=fade(t,.16+row*.11+j*.017,.62);ctx.save();ctx.globalAlpha*=p;
   text(str[j],px,y+row*sz*1.19+(1-p)*24,actual,row===lines.length-1&&lines.length>1?gold:ivory,'Cinzel','600');ctx.restore();
   ctx.font=`600 ${actual}px Cinzel`;px+=ctx.measureText(str[j]).width;
  }
 }return y+lines.length*sz*1.19;
}
let lastGlassTime=null;
let lastDemoBackground=null;
const demoBackground=document.createElement('canvas'),demoBackgroundContext=demoBackground.getContext('2d');
function background(t,scene){
 const tick=Math.floor(t*6)/6;
 if(scene.demo&&lastDemoBackground===tick){ctx.drawImage(demoBackground,0,0);return;}
 ctx.fillStyle='#090c14';ctx.fillRect(0,0,W,H);
 const drift=Math.sin(t*.07)*9, zoom=1.035+Math.sin(t*.043)*.017;
 ctx.save();
 if(portrait){
  // Portrait is recomposed: the original raven window occupies the upper tier.
  const hh=scene.kind==='hero'?1220:920,scale=hh/art.height*zoom;
  ctx.drawImage(art,W*.5-art.width*.234*scale+drift,-90-(zoom-1)*hh/2,art.width*scale,art.height*scale);
  const g=ctx.createLinearGradient(0,200,0,scene.kind==='hero'?1150:800);
  g.addColorStop(0,'#090c1400');g.addColorStop(.57,'#090c1459');g.addColorStop(1,'#090c14');ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
 }else{
  const hh=H*zoom,ww=hh*art.width/art.height;ctx.drawImage(art,-65+drift,-(hh-H)/2,ww,hh);
  const g=ctx.createLinearGradient(450,0,1260,0);g.addColorStop(0,'#090c1400');g.addColorStop(.48,'#090c14ad');g.addColorStop(1,'#090c14fa');ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
 }
 ctx.restore();
 // The mostly covered glass in the screen demo updates at 6 Hz; foreground stays 24 fps.
 // The original chapter retains its exact renderer timeline.
 const gt=scene.demo?Math.floor(t*6)/6:t;
 if(lastGlassTime!==gt||!scene.demo){
  rose.position.set(portrait?1.35:4.7,portrait?-1.3:.4,-2);
  rose.scale.setScalar(portrait?1.32:1.25);rose.rotation.set(.11*Math.sin(gt*.08),.13*Math.sin(gt*.065),gt*.017);
  dust.rotation.z=gt*.006;dust.position.y=Math.sin(gt*.1)*.12;
  facets.children.forEach((m,i)=>{m.rotation.y=gt*.11+m.userData.phase;m.rotation.z=gt*.035+i;m.position.y=m.userData.y+Math.sin(gt*.15+i)*.2;});
  renderer.render(world,camera);lastGlassTime=gt;
 }
 ctx.drawImage(renderer.domElement,0,0,W,H);
 const vignette=ctx.createRadialGradient(W*.4,H*.4,H*.1,W*.5,H*.5,H*.85);vignette.addColorStop(0,'#00000000');vignette.addColorStop(1,'#03050bb3');ctx.fillStyle=vignette;ctx.fillRect(0,0,W,H);
 // Thin brass rules and enamel inlays use the repository palette.
 ctx.strokeStyle='#c8a56755';ctx.lineWidth=1;ctx.strokeRect(36.5,36.5,W-73,H-73);
 const palette=['#1f4fa3','#b3202f','#e8a317','#1f7a4d','#5b2e8a','#1b7f8c'];
 const stripeW=(W-160)/palette.length;
 palette.forEach((c,i)=>{ctx.fillStyle=c;ctx.fillRect(80+i*stripeW,H-39,stripeW-7,3);});
 tracked('YOUNGCROW',76,68,portrait?21:19,5);text('FIELD GUIDE  /  2026',portrait?690:1584,71,portrait?15:17,'#ada798');
 if(scene.demo){
  if(demoBackground.width!==W||demoBackground.height!==H){demoBackground.width=W;demoBackground.height=H;}
  demoBackgroundContext.drawImage(canvas,0,0);lastDemoBackground=tick;
 }else lastDemoBackground=null;
}
function shell(s,x,y,w,t){
 const pad=portrait?27:30;
 let fs=portrait?32:25;
 ctx.font=`${fs}px monospace`;
 const longest=Math.max(...s.code.map(command=>ctx.measureText(command).width));
 fs=Math.min(fs,fs*(w-pad*2)/longest);
 const lh=fs*1.63;
 const h=78+s.code.length*lh+17;panel(x,y,w,h);
 tracked(s.label,x+pad,y+22,portrait?14:13,1.5,'#b5aca0');line(x+pad,y+53,w-pad*2,.2);
 const chars=Math.floor(Math.max(0,t-.8)*160);
 let used=0;
 s.code.forEach((cmd,i)=>{
  const visible=cmd.slice(0,Math.max(0,chars-used));used+=cmd.length;
  text(visible,x+pad,y+72+i*lh,fs,cmd.startsWith('  ')?'#c4d5d7':'#f0dbb4','monospace');
 });return y+h;
}
function skill(s,x,y,w,t){
 const gap=18,columns=portrait?1:2,cw=(w-gap*(columns-1))/columns,ch=portrait?112:124;
 [['CLAUDE CODE','/'+s.skill],['CODEX','$'+s.skill]].forEach(([label,cmd],i)=>{
  const px=x+(columns===1?0:i*(cw+gap)),py=y+(columns===1?i*(ch+gap):0);panel(px,py,cw,ch);
  tracked(label,px+26,py+20,15,2.5);text(cmd,px+26,py+55,portrait?36:28,ivory,'monospace');
 });return y+(columns===1?ch*2+gap:ch);
}
function body(s,x,y,w,t){
 ctx.save();ctx.globalAlpha*=fade(t,.45,.6);
 const fs=portrait?40:29;
 for(const row of s.body||[])y=paragraph(row,x,y,w,fs,muted,1.5);
 y+=portrait?34:29;ctx.restore();
 ctx.save();ctx.globalAlpha*=fade(t,.75,.6);
 if(s.code)y=shell(s,x,y,w,t)+28;
 if(s.skill)y=skill(s,x,y,w,t)+32;
 if(s.diagram){
  const h=90;panel(x,y,w,h);text('workspace/',x+26,y+18,23,gold,'monospace');
  text('YoungCrowHarness/   +   meu-projeto/',x+26,y+51,portrait?23:25,ivory,'monospace');y+=h+27;
 }
 if(s.cards){for(const [a,b] of s.cards){panel(x,y,w,portrait?131:108);tracked(a,x+26,y+19,portrait?19:17,1.5);text(b,x+26,y+57,portrait?29:26,ivory);y+=portrait?151:129;}}
 if(s.quote){
  line(x,y,72,.7);y+=22;
  const lines=wrap('“'+s.quote+'”',w,portrait?37:33,'Manrope');
  lines.forEach(row=>{text(row,x,y,portrait?37:33,ivory);y+=portrait?54:48;});y+=22;
 }
 if(s.tags){s.tags.forEach((tag,i)=>{
  const ww=(w-(s.tags.length-1)*13)/s.tags.length;
  ctx.strokeStyle='#a5864f66';ctx.strokeRect(x+i*(ww+13),y,ww,48);
  const size=portrait?18:17;ctx.font=`700 ${size}px Manrope`;text(tag,x+i*(ww+13)+(ww-ctx.measureText(tag).width)/2,y+14,size,gold,'Manrope','700');
 });y+=77;}
 if(s.badge){panel(x,y,w,100);ctx.fillStyle='#68bca3';diamond(x+28,y+50,7);text('MISSION  /',x+50,y+36,22,muted,'monospace');text(s.badge,x+220,y+31,32,'#8ed5bd','monospace');y+=132;}
 if(s.roadmap){
  tracked('A ESTEIRA QUE ESTAMOS CONSTRUINDO',x,y,portrait?16:15,1.3);y+=48;
  const labels=s.roadmap,ww=w/labels.length;
  line(x+15,y+21,w-30,.35);
  labels.forEach((label,i)=>{const cx=x+ww*i+ww*.5;ctx.fillStyle='#0b111b';ctx.beginPath();ctx.arc(cx,y+21,15,0,7);ctx.fill();ctx.strokeStyle=gold;ctx.stroke();ctx.fillStyle=gold;diamond(cx,y+21,4);ctx.font='700 15px Manrope';text(label,cx-ctx.measureText(label).width/2,y+49,15,gold,'Manrope','700');});y+=110;
 }
 if(s.note)y=paragraph(s.note,x,y,w,portrait?31:23,'#b4ada2',1.5);
 if(s.tag){y+=45;tracked(s.tag,x,y,portrait?19:18,1.6,gold);}
 ctx.restore();return y;
}
function draw(t){
 time=Math.min(DURATION-.001,Math.max(0,t));
 const index=scenes.findIndex(s=>time<s.start+s.seconds),s=scenes[index],local=time-s.start;
 background(time,s);
 if(s.demo)return drawDemo(s,local,index);
 const x=portrait?92:835,w=portrait?896:975;
 const y=portrait?(s.kind==='hero'?900:545):(s.kind==='hero'?310:150);
 const exit=clamp((s.seconds-local)/.45);
 ctx.save();ctx.globalAlpha=exit;
 tracked(s.chapter,x,y,portrait?19:18,portrait?3:3.2);
 line(x,y+44,w*fade(local,.05,.95),.6);
 const titleY=y+76;
 const titleSize=s.kind==='hero'?(portrait?107:109):(portrait?68:66);
 let after=lettering(s.title,x,titleY,w,titleSize,local);
 if(s.accent){ctx.globalAlpha*=fade(local,.55,.65);text(s.accent,x,after+12,portrait?37:38,gold);after+=93;}
 const bottom=body(s,x,after+26,w,local);
 ctx.restore();
 // Chapter ruler is separate from content and is stable during transitions.
 const footerY=H-117,navX=portrait?92:835,navW=portrait?896:975;
 line(navX,footerY,navW,.25);
 for(let i=0;i<11;i++){
  const gap=9,sw=(navW-gap*10)/11;
  ctx.fillStyle=i===index?gold:i<index?'#746340':'#303039';ctx.fillRect(navX+i*(sw+gap),footerY+22,sw,3);
 }
 text(String(index+1).padStart(2,'0')+' / 11',navX,footerY+43,19,gold,'monospace');
 text('PRÉVIA · PR #24',navX+navW-210,footerY+44,17,'#a9a397');
 if(!portrait){text(s.kind==='hero'?'O COMEÇO DE UMA ENTREGA':String(index).padStart(2,'0'),88,H-238,s.kind==='hero'?17:105,s.kind==='hero'?gold:'#dfba7855','Cinzel','600');text('VITRAL · CORVO · SÃO BENTO',88,H-104,15,'#afa389');}
 window.filmMetrics={index,bottom,footerY,overflow:bottom>footerY-16&&s.kind!=='hero',width:W,height:H};
 return window.filmMetrics;
}
const scrub=document.querySelector('#scrub'),button=document.querySelector('#play');
scrub.max=DURATION;
function stamp(t){return Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0');}
function displayTime(){scrub.value=time;document.querySelector('#time').textContent=stamp(time)+' / '+stamp(DURATION);}
function toggle(){playing=!playing;if(time>=DURATION-.01)time=0;origin=performance.now()/1000-time;button.textContent=playing?'Pausar':'Reproduzir';button.setAttribute('aria-label',playing?'Pausar apresentação':'Reproduzir apresentação');}
button.onclick=toggle;
scrub.oninput=()=>{time=Number(scrub.value);origin=performance.now()/1000-time;draw(time);displayTime();};
document.querySelector('#format').onchange=e=>{portrait=e.target.value==='portrait';size();draw(time);};
document.onkeydown=e=>{if(/INPUT|SELECT|BUTTON/.test(e.target.tagName))return;if(e.code==='Space'){e.preventDefault();toggle();}if(e.code==='ArrowRight'||e.code==='ArrowLeft'){const i=window.filmMetrics.index+(e.code==='ArrowRight'?1:-1);time=scenes[Math.max(0,Math.min(scenes.length-1,i))].start;origin=performance.now()/1000-time;draw(time);displayTime();}};
window.seekFilm=t=>{playing=false;const m=draw(t);displayTime();return m;};
window.setFilmFormat=value=>{portrait=value==='portrait';size();draw(time);};
window.filmScenes=scenes;window.filmDuration=DURATION;
window.filmReady=Promise.all([loaded,art.decode()]).then(()=>{
 size();draw(0);displayTime();if(params.has('export'))document.body.classList.add('export');
 if(!params.has('export')){const loop=now=>{if(playing){draw((now/1000-origin));displayTime();if(time>=DURATION-.002){playing=false;button.textContent='Reproduzir';}}requestAnimationFrame(loop);};requestAnimationFrame(loop);}
 return true;
});
