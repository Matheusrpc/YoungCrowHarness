/* An illustrative walkthrough, not a recording of native clients or model calls.
   Every command, message, code sample and result below is inert display text. */
window.DEMO_SCENES = [
 {seconds:9,demo:'calendar',chapter:'CASO PRÁTICO / CLÍNICA FICTÍCIA',title:['Um atendente. Do zero, na tela.'],role:'ANA · PRODUTO',app:'Atendente da Clínica',active:'produto',caption:'Ana cria um atendente administrativo para uma clínica: conversa, horários e agendamento. Exemplo fictício.',status:0},
 {seconds:13,demo:'terminal',chapter:'01 / ANA PREPARA O PROJETO',title:['Uma pasta para o produto.'],role:'ANA · TERMINAL',app:'Terminal',active:'terminal',caption:'Ela reaproveita o clone da primeira parte, guarda o ponto de retorno e confere o Git.',status:0,lines:['bash YoungCrowHarness/setup.sh atendente-clinica \\', '  --trial --client both --nome "Atendente da Clínica"','cd atendente-clinica','git init','git check-ignore --no-index .env','git ls-files -- .env'],note:'Saída ilustrativa: .env ignorado; nenhum .env rastreado.'},
 {seconds:13,demo:'chat',chapter:'02 / O PRODUTO GANHA CONTEXTO',title:['Ana abre o Codex.'],role:'PERSONALIZER · CODEX',app:'Codex · conversa ilustrativa',active:'perfil',caption:'A entrevista registra decisões e perguntas. O YoungCrow não gera uma aplicação no setup.',status:0,prompt:'$yc-personalizer\nQuero um atendente de clínica que ofereça horários e agende. Vamos criar um protótipo local.',replies:[['CODEX','Qual é o fluxo de atendimento? O agente agenda ou encaminha para uma pessoa?'],['ANA','Agende consultas de 30 minutos. Dúvidas clínicas vão para uma pessoa, sem orientação médica.'],['ARQUIVO SALVO','vault/product/index.md · perfil e decisões']]},
 {seconds:14,demo:'features',chapter:'03 / PM DEFINE O QUE ENTREGAR',title:['O objetivo vira features.'],role:'PM · SESSÃO CODEX',app:'Codex · planejamento ilustrativo',active:'features',caption:'Ana pede ao agente o papel de PM: objetivo, prioridade e critérios de aceite. Não há despacho automático.',status:1,items:[['F1','Atendimento inicial','Entender o pedido e encaminhar dúvidas clínicas.'],['F2','Oferecer horários e agendar','Consultar disponibilidade e recusar conflitos.'],['F3','Cancelamento','Liberar o horário e preservar o registro cancelado.']]},
 {seconds:13,demo:'tasks',chapter:'04 / TECH LEAD DETALHA',title:['Cada tarefa tem um teste.'],role:'TECH LEAD · SESSÃO CODEX',app:'Codex · refinamento ilustrativo',active:'pbis',caption:'O Tech Lead registra dependências. Uma tarefa só avança quando suas condições de entrada estão atendidas.',status:1,items:[['PBI 1','Conversar e encaminhar','Coletar o pedido; encaminhar dúvidas clínicas.'],['PBI 2','Oferecer horários','Consultar a disponibilidade dos profissionais.'],['PBI 3','Confirmar agendamento','Validar disponibilidade e recusar conflito.'],['PBI 4','Cancelar','Preservar registro e liberar intervalo.']]},
 {seconds:12,demo:'markdown',chapter:'05 / O PLANO FICA NO VAULT',title:['Markdown guarda as decisões.'],role:'TECH LEAD · VAULT',app:'Editor · nota de feature',active:'features',caption:'O índice liga épico, features e PBIs. Cada nota real conserva UUID e contrato; aqui vemos um trecho resumido.',status:1,path:'vault/local/product/features/<UUID>/index.md',lines:['# F2 · Agendamento sem conflitos','','Objetivo: o agente confirma um horário disponível.','Aceite: recusar sobreposição do mesmo profissional.','Regra: terminar às 10h permite iniciar às 10h.','','Dependências: conversa e serviço de disponibilidade.','Validação: horário livre, conflito e consecutivos.','Próxima entrega: F3 · cancelamento.'],note:'<UUID> representa a identidade da nota; não é um nome de pasta literal.'},
 {seconds:14,demo:'mission',chapter:'06 / ANA PREPARA A MISSÃO',title:['F1 + F2 agora. F3 depois.'],role:'PM + TECH LEAD · CODEX',app:'Codex · preparação ilustrativa',active:'missao',caption:'prepared confirma o planejamento. Ana conduz a implementação na sessão; a fila automática ainda não existe.',status:1,prompt:'$yc-config  →  escolhas de cada papel\n$yc-missao  →  selecione F1 e F2\nPriorize os PBIs. Preserve F3 no backlog.',replies:[['$yc-status','M001 · prepared'],['ESCOPO','Atendimento + agendamento. Cancelamento permanece pendente.'],['PRÓXIMO PASSO','Ana pede a implementação dentro desse escopo.']]},
 {seconds:13,demo:'code',chapter:'07 / CODEX IMPLEMENTA',title:['O código e as notas avançam.'],role:'DEV · CODEX',app:'Codex · edição ilustrativa',active:'codigo',caption:'Ana pede o fluxo de atendimento e a reserva. Codex edita o código, acrescenta testes e atualiza as notas.',status:2,path:'src/atendente.ts',lines:['async function atender(pedido) {','  if (pedido.tipo === "duvida-clinica")','    return encaminharParaPessoa(pedido);','  const horarios = await agenda.disponiveis(pedido);','  return oferecerHorarios(horarios);','}','','// Reserva: falta validar conflito antes de confirmar.'],note:'Salvos no exemplo: src/atendente.ts · tests/atendente.test.ts · notas do vault.'},
 {seconds:14,demo:'checkpoint',chapter:'08 / SALVAR ANTES DO LIMITE',title:['O checkpoint precede a pausa.'],role:'ANA + CODEX · HANDOFF',app:'Editor · checkpoint ilustrativo',active:'handoff',caption:'Ana pede o registro enquanto a sessão ainda responde. Memória persistente depende dos arquivos que foram salvos.',status:2,path:'vault/local/handoffs/atendente-clinica-001.md',lines:['# Atendente da clínica · checkpoint 01','Decisão: consultas consecutivas são permitidas.','Concluído: conversa e consulta de disponibilidade.','Em andamento: F2 · agendamento.','Falta: recusar conflito. F3 segue no backlog.','Arquivos: src/atendente.ts + tests/atendente.test.ts','Testes: consultar as evidências do exemplo.','Próxima ação: implementar e testar conflito.','Produção: não verificada.'],note:'Em uso real: incluir UUIDs, fontes/revisões, branch, diff, testes e limites.'},
 {seconds:14,demo:'limit',chapter:'09 / A SESSÃO É INTERROMPIDA',title:['A cota acaba. O trabalho fica.'],role:'ANA · TROCA MANUAL',app:'Codex → Claude · transição ilustrativa',active:'handoff',caption:'Nesta encenação a cota se esgota. Ana confere o trabalho salvo, encerra o Codex e abre o Claude na mesma pasta.',status:2,lines:['git status --short','git diff'],note:'Um escritor por checkout. A troca não é automática; o limite varia conforme o plano.'},
 {seconds:14,demo:'recover',chapter:'10 / CLAUDE RECONSTRÓI O CONTEXTO',title:['Outra LLM. Os mesmos registros.'],role:'CLAUDE · NOVA SESSÃO',app:'Claude · conversa ilustrativa',active:'handoff',caption:'A nova sessão lê os índices, o checkpoint e as fontes atuais. Não recebe uma cópia da conversa anterior.',status:2,prompt:'Leia AGENTS.md e CLAUDE.md. Use retrieve-memory para retomar o atendente. Confira o checkpoint, as fontes, git status e git diff antes de editar.',replies:[['FONTES CONSULTADAS','vault/local/index.md → handoff → feature/PBI'],['CLAUDE','F1 atende e encaminha. F2 precisa recusar conflitos. F3 continua pendente.'],['ANA','Continue essa PBI dentro do escopo registrado.']]},
 {seconds:13,demo:'code',chapter:'11 / CLAUDE CONTINUA A MESMA PBI',title:['Retomar sem recriar o backlog.'],role:'DEV · CLAUDE',app:'Claude · edição ilustrativa',active:'codigo',caption:'O Claude implementa a verificação de conflito antes da confirmação. Horários consecutivos continuam permitidos.',status:3,path:'src/atendente.ts · trecho acrescentado',lines:['const conflito = agenda.some(consulta =>','  consulta.profissional === nova.profissional &&','  consulta.inicio < nova.fim &&','  nova.inicio < consulta.fim',');','','if (conflito) throw new Error("Horário ocupado");','','// Só confirme ao paciente após reservar sem conflito.'],note:'Atualizados no exemplo: teste de conflito e checkpoint; F3 preservada.'},
 {seconds:13,demo:'qa',chapter:'12 / REVISÃO EM OUTRO CONTEXTO',title:['QA verifica. Dev corrige.'],role:'QA · CONTEXTO INDEPENDENTE',app:'Revisão · somente leitura',active:'testes',caption:'A implementação encerra a escrita. QA compara o diff com os critérios e registra evidências, sem corrigir arquivos.',status:3,items:[['01','Pedido de consulta','Oferecer horário e confirmar após reservar.'],['02','Mesmo profissional','Recusar sobreposição.'],['03','Profissionais diferentes','Permitir o mesmo horário.'],['04','Dúvida clínica','Encaminhar para uma pessoa; não orientar.']]},
 {seconds:11,demo:'calendar',chapter:'13 / O CONTROLE CONTINUA COM VOCÊ',title:['Uma entrega. Um próximo passo.'],role:'PM + TECH LEAD + QA',app:'Atendente da Clínica · exemplo local',active:'produto',caption:'O atendente conversa e agenda no exemplo. F3 segue pendente. README e checkpoint registram a entrega; produção não verificada.',status:4,note:'Hoje: sessões conduzidas pela pessoa. Coordenação automática: em desenvolvimento.'}
];

function demoAvatar(x,y,r=20){
 ctx.fillStyle='#403d56';ctx.beginPath();ctx.arc(x,y,r,0,7);ctx.fill();
 ctx.fillStyle='#bc9185';ctx.beginPath();ctx.arc(x,y-4,r*.37,0,7);ctx.fill();
 ctx.fillStyle='#2a2636';ctx.beginPath();ctx.arc(x-1,y-8,r*.38,Math.PI,Math.PI*2);ctx.fill();
 ctx.fillStyle='#9b7cba';ctx.beginPath();ctx.ellipse(x,y+r*.6,r*.63,r*.46,0,Math.PI,Math.PI*2);ctx.fill();
}
function demoCursor(x,y,t){
 ctx.save();ctx.translate(x,y);ctx.shadowColor='#000';ctx.shadowBlur=8;
 ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(0,29);ctx.lineTo(8,22);ctx.lineTo(14,34);ctx.lineTo(20,31);ctx.lineTo(14,20);ctx.lineTo(26,20);ctx.closePath();ctx.fillStyle=ivory;ctx.fill();ctx.strokeStyle='#10131d';ctx.lineWidth=2;ctx.stroke();ctx.shadowBlur=0;
 const pulse=(t%3)/3;if(pulse<.3){ctx.beginPath();ctx.arc(2,5,pulse*90,0,7);ctx.strokeStyle=`rgba(223,186,120,${1-pulse*3})`;ctx.lineWidth=2;ctx.stroke();}ctx.restore();
}
function demoRows(lines,x,y,w,fs,t,kind='text'){
 let bottom=y,used=0;const visibleCharacters=Math.floor(Math.max(0,t-.2)*160);
 lines.forEach((row,i)=>{
  ctx.save();ctx.globalAlpha*=fade(t,.25+i*.12,.42);
  const rows=wrap(row,w,fs,kind==='code'?'monospace':'Manrope');
  for(const r of rows){text(r.slice(0,Math.max(0,visibleCharacters-used)),x,bottom,fs,r.trim().startsWith('//')?'#8e949f':r.startsWith('#')?gold:ivory,kind==='code'?'monospace':'Manrope');used+=r.length;bottom+=fs*1.5;}
  ctx.restore();
 });return bottom;
}
function demoBoard(s,x,y,w,compact){
 const labels=['F1 · Atendimento','F2 · Agendamento','F3 · Cancelamento'];
 const states=s.status===4?['Revisada no exemplo','Revisada no exemplo','Próxima entrega']:s.status>=2?['Implementada no exemplo',s.status===3?'Em revisão':'Em andamento','No backlog']:['Planejada','Planejada','No backlog'];
 const fs=compact?18:19;
 if(compact){
  const cw=(w-24)/3;labels.forEach((label,i)=>{panel(x+i*(cw+12),y,cw,92);text(label,x+i*(cw+12)+14,y+17,18,gold);text(states[i],x+i*(cw+12)+14,y+50,16,muted);});return;
 }
 tracked('MISSÃO 01',x,y,16,2);y+=50;
 labels.forEach((label,i)=>{text(label,x,y,fs,gold);y=paragraph(states[i],x,y+34,w,18,muted,1.4)+37;});
 line(x,y,w,.3);y+=30;tracked('CONTROLE',x,y,14,2);y+=37;
 paragraph('Um escritor por checkout.\nProdução fora deste exemplo.',x,y,w,19,muted,1.5);
}
function demoCards(s,x,y,w,t){
 const gap=portrait?22:16,h=portrait?151:(s.items.length===4?102:140);
 s.items.forEach(([id,name,detail],i)=>{
  ctx.save();ctx.globalAlpha*=fade(t,.45+i*.28,.45);panel(x,y+i*(h+gap),w,h);
  text(id,x+22,y+i*(h+gap)+19,portrait?24:21,gold,'monospace');
  text(name,x+(portrait?112:104),y+i*(h+gap)+19,portrait?30:27,ivory,'Manrope','700');
  paragraph(detail,x+22,y+i*(h+gap)+61,w-44,portrait?28:23,muted,1.4);
  if(s.demo==='qa'&&t>2+i*1.7){text('✓',x+w-45,y+i*(h+gap)+20,28,'#80c6b0');}
  ctx.restore();
 });return y+s.items.length*(h+gap);
}
function demoChat(s,x,y,w,t){
 const fs=portrait?31:26;panel(x,y,w,portrait?204:158);
 demoAvatar(x+31,y+28,16);tracked('ANA',x+57,y+17,14,2);
 const prompt=s.prompt.slice(0,Math.floor(Math.max(0,t)*140));
 paragraph(prompt,x+24,y+57,w-48,fs,ivory,1.4);y+=portrait?230:180;
 for(let i=0;i<s.replies.length;i++){
  const [label,value]=s.replies[i];ctx.save();ctx.globalAlpha*=fade(t,1.9+i*1.2,.5);
  tracked(label,x,y,portrait?17:14,1.1,label==='ANA'?gold:'#83c3b9');
  y=paragraph(value,x,y+33,w,fs,ivory,1.4)+(portrait?31:25);ctx.restore();
 }return y;
}
function demoCalendar(x,y,w,h,t){
 tracked('ATENDENTE · PROTÓTIPO ILUSTRATIVO',x,y,portrait?21:18,1.3);y+=44;
 const rows=[['PACIENTE FICTÍCIO','Quero marcar uma consulta amanhã.'],['AGENTE DA CLÍNICA','Para qual especialidade?'],['PACIENTE FICTÍCIO','Clínica geral, pela manhã.'],['AGENTE DA CLÍNICA','Há 9h e 9h30. Qual horário prefere?'],['PACIENTE FICTÍCIO','9h30.'],['AGENTE DA CLÍNICA','Reserva feita. Consulta confirmada às 9h30.']];
 const fs=portrait?30:24,lh=portrait?100:62;
 rows.forEach(([label,value],i)=>{
  ctx.save();ctx.globalAlpha*=fade(t,.3+i*.7,.35);
  ctx.fillStyle=i%2?'#19302e':'#172235';ctx.fillRect(x,y+i*lh,w,lh-7);
  tracked(label,x+18,y+i*lh+10,portrait?16:12,1,i%2?'#94c9b7':gold);
  paragraph(value,x+18,y+i*lh+(portrait?40:30),w-36,fs,ivory,1.3);ctx.restore();
 });y+=rows.length*lh+10;
 ctx.save();ctx.globalAlpha*=fade(t,4.1,.4);
 text('AGENDA · Profissional A · 09:30 reservado',x,y,portrait?24:20,'#91c2ad');ctx.restore();
 return y+(portrait?40:28);
}
function drawDemo(s,t,index){
 const step=index-11,chapterN=window.DEMO_SCENES.length;
 // Keep the original chapter unchanged. The wide screen is replaced by a stacked mobile view.
 const px=portrait?52:80,py=portrait?367:252,pw=portrait?976:1760,ph=portrait?1110:644;
 const top=portrait?160:137;
 tracked(s.chapter,px,top,portrait?20:17,2.4);
 lettering(s.title,px,top+45,pw,portrait?56:54,t);
 ctx.save();ctx.globalAlpha=fade(t,0,.45)*clamp((s.seconds-t)/.3);ctx.translate(0,(1-fade(t,0,.6))*16);
 ctx.fillStyle='#0d1420';ctx.fillRect(px,py,pw,ph);ctx.strokeStyle='#b2925a99';ctx.lineWidth=1;ctx.strokeRect(px+.5,py+.5,pw-1,ph-1);
 ctx.fillStyle='#1a2332';ctx.fillRect(px,py,pw,64);
 ['#b6575e','#b7a05e','#679b86'].forEach((c,i)=>{ctx.fillStyle=c;ctx.beginPath();ctx.arc(px+25+i*19,py+29,5,0,7);ctx.fill();});
 text(s.app,px+96,py+19,portrait?25:23,ivory);
 demoAvatar(px+pw-164,py+29,21);text('Ana',px+pw-130,py+18,22,gold);text('PESSOA',px+pw-78,py+24,11,muted);
 ctx.fillStyle='#121b29';ctx.fillRect(px,py+64,pw,48);tracked(s.role,px+23,py+79,portrait?19:15,1.2,'#9ecdc4');
 const sidebar=portrait?0:252,rightbar=portrait?0:270;
 let cx=px+sidebar+26,cy=py+139,cw=pw-sidebar-rightbar-52;
 if(portrait){
  ctx.fillStyle='#202a38';ctx.fillRect(px+20,cy-5,pw-40,70);
  text('atendente-clinica / '+(s.active==='codigo'?'src/atendente.ts':s.active==='testes'?'tests/atendente.test.ts':'vault / '+s.active),px+36,cy+14,27,gold,'monospace');cy+=97;
 }else{
  tracked('EXPLORADOR',px+20,cy,13,2);let yy=cy+39;
  const files=[['atendente-clinica/','produto'],['  src/atendente.ts','codigo'],['  tests/atendente.test.ts','testes'],['  vault/product/','perfil'],['  vault/local/',''],['    product/',''],['      features/','features'],['      pbis/','pbis'],['    handoffs/','handoff'],['  M001','missao']];
  files.forEach(([f,id])=>{if(id===s.active){ctx.fillStyle='#9b793433';ctx.fillRect(px+9,yy-6,sidebar-19,32);}text(f,px+20,yy,17,id===s.active?gold:'#91a0b2','monospace');yy+=34;});
  line(px+sidebar,py+112,1,.2);demoBoard(s,px+pw-rightbar+12,cy,rightbar-32,false);
 }
 let bottom=cy;
 if(s.demo==='calendar')bottom=demoCalendar(cx,cy,cw,ph-180,t);
 else if(s.demo==='features'||s.demo==='tasks'||s.demo==='qa')bottom=demoCards(s,cx,cy,cw,t);
 else if(s.demo==='chat'||s.demo==='mission'||s.demo==='recover')bottom=demoChat(s,cx,cy,cw,t);
 else if(s.demo==='limit'){
  const phase=t<4?'LIMITE DA SESSÃO ATINGIDO':t<8?'CODEX ENCERRADO':'CLAUDE · NOVA SESSÃO';
  const color=t<4?'#c87776':t<8?gold:'#99cbbf';panel(cx,cy,cw,portrait?145:105);
  tracked(phase,cx+24,cy+24,portrait?25:21,1.3,color);text('Interrupção encenada; mensagem ilustrativa.',cx+24,cy+(portrait?80:63),portrait?25:20,muted);
  bottom=demoRows(s.lines,cx,cy+(portrait?198:143),cw,portrait?35:26,t,'code');
  ctx.save();ctx.globalAlpha*=fade(t,4,.5);bottom=paragraph('Checkpoint já salvo.\nAna revisa o diff e encerra o escritor.\nClaude abre a mesma pasta, com o vault intacto.',cx,bottom+20,cw,portrait?33:24,ivory,portrait?1.55:1.35);ctx.restore();
  if(t>8){panel(cx,bottom+15,cw,64);text('claude',cx+25,bottom+32,29,'#a1d3c1','monospace');bottom+=84;}
 }else{
  if(s.path){cy=paragraph(s.path,cx,cy,cw,portrait?26:21,'#849eb4',1.4)+26;}
  const fs=portrait?29:(s.demo==='terminal'?27:23);
  bottom=demoRows(s.lines,cx,cy,cw,fs,t,s.demo==='terminal'||s.demo==='code'?'code':'text');
  if(s.demo!=='terminal'){
   ctx.save();ctx.globalAlpha*=fade(t,3.8,.5);text('●  salvo no exemplo',cx,bottom+23,portrait?24:19,'#86c4a9');ctx.restore();bottom+=52;
  }
 }
 if(s.note&&s.demo!=='calendar'){
  bottom+=25;bottom=paragraph(s.note,cx,bottom,cw,portrait?25:20,'#abb2be',1.4);
 }
 const contentLimit=py+ph-(portrait?135:23);
 if(portrait)demoBoard(s,px+22,py+ph-118,pw-44,true);
 // A moving pointer represents Ana's actions; it never dispatches commands.
 const progress=ease((t%5)/2.8);
 demoCursor(cx+cw*(.12+.68*progress),py+118+(ph-230)*(.42+.12*Math.sin(t*.7)),t);
 ctx.restore();
 let capY=py+ph+31;
 capY=paragraph(s.caption,px,capY,pw,portrait?35:28,ivory,1.45);
 if(s.demo==='calendar'&&s.note)capY=paragraph(s.note,px,capY+19,pw,portrait?29:21,gold,1.4);
 const foot=H-(portrait?90:51);
 tracked('ENCENAÇÃO · INTERFACES, DADOS E RESULTADOS FICTÍCIOS',px,foot,portrait?14:14,portrait?.7:1.1,'#b9a37d');
 text(String(step+1).padStart(2,'0')+' / '+chapterN,px+pw-85,foot+23,17,gold,'monospace');
 const metric={index,width:W,height:H,bottom,contentLimit,captionBottom:capY,footerY:foot,overflow:bottom>contentLimit||capY>foot-12};
 window.filmMetrics=metric;return metric;
}
