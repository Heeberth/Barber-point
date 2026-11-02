// Barber Point - front-end (JavaScript puro). Conversa com a API em /api.
const SL=[];for(let h=9;h<18;h++){const x=String(h).padStart(2,'0');SL.push(x+':00',x+':30')}
const PIX='pix@barberpoint.com.br',FORMAS=['Pix','Cartão','Dinheiro'];
const E=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const iso=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
const fd=i=>new Date(i+'T12:00').toLocaleDateString('pt-BR',{weekday:'short',day:'2-digit',month:'2-digit'});
const R=v=>'R$ '+Number(v).toFixed(2).replace('.',',');
const DAYS=[];for(let i=0;DAYS.length<7;i++){const d=new Date();d.setDate(d.getDate()+i);if(d.getDay())DAYS.push(iso(d))}
const TODAY=iso(new Date()),TOM=iso(new Date(Date.now()+864e5));
const LS={g:k=>{try{return JSON.parse(localStorage.getItem(k))}catch(e){return null}},s:(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
const S={me:null,view:'g',tab:'ag',reg:false,msg:'',done:null,servicos:[],barbeiros:[],ocupados:[],mine:{},wl:{},agenda:null,bd:DAYS[0],
sel:{s:[],b:null,d:null,t:null,m:'Pix',cash:''},g:LS.g('bp_g')||{name:'',phone:''}};
const $v=id=>document.getElementById(id).value.trim();
const digits=s=>String(s).replace(/\D/g,'');
const wa=(ph,m)=>`https://wa.me/55${digits(ph)}?text=${encodeURIComponent(m)}`;
const names=a=>a.servicos.map(s=>s.nome).join(' + ');
const past=(d,t)=>{const n=new Date();return d==TODAY&&t<=String(n.getHours()).padStart(2,'0')+':'+String(n.getMinutes()).padStart(2,'0')};
const flash=m=>{S.msg=m;draw()};
async function api(method,url,body){try{const r=await fetch('/api/'+url,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
let d=null;try{d=await r.json()}catch(e){}return{ok:r.ok,status:r.status,d}}catch(e){return{ok:false,status:0,d:{erro:'Sem conexão com o servidor.'}}}}
const A={};
A.set=(k,v)=>{S[k]=v;S.msg='';draw();refresh()};
A.f=(k,v)=>{S.g[k]=v;LS.s('bp_g',S.g)};
A.cash=v=>{S.sel.cash=v};
A.tg=(k,v)=>{const s=S.sel;if(k=='s')s.s=s.s.includes(v)?s.s.filter(x=>x!=v):[...s.s,v];else{s[k]=v;if(k=='b'||k=='d')s.t=null}draw();if(k=='b'||k=='d')refresh()};
const cashV=()=>{const v=parseFloat(String(S.sel.cash||'').replace(',','.'));return S.sel.m=='Dinheiro'&&v>0?v:null};
const cashTxt=a=>a.forma=='Dinheiro'&&a.troco_para?` · troco para ${R(a.troco_para)} (troco ${R(a.troco_para-a.total)})`:'';
const valid=()=>{const g=S.g;if(!g.name||g.name.trim().length<2)return 'Informe seu nome.';const p=digits(g.phone).length;return p<10||p>11?'Informe um telefone com DDD.':''};
const payload=()=>{const s=S.sel;return{nome:S.g.name.trim(),telefone:digits(S.g.phone),barbeiro_id:s.b,data:s.d,hora:s.t,servicos:s.s,forma:s.m,troco_para:cashV()}};
A.book=async()=>{const e=valid();if(e)return flash(e);const s=S.sel;if(!s.s.length||!s.b||!s.d||!s.t)return flash('Complete todas as etapas.');
const r=await api('POST','agendamentos',payload());if(!r.ok)return flash(r.d.erro);
const l=LS.g('bp_c')||[];l.push(r.d.codigo);LS.s('bp_c',l);S.done=r.d.codigo;S.sel={s:[],b:null,d:null,t:null,m:'Pix',cash:''};refresh();draw()};
A.wait=async()=>{const e=valid();if(e)return flash(e);if(!S.sel.s.length)return flash('Escolha os serviços antes.');
const r=await api('POST','espera',payload());if(!r.ok)return flash(r.d.erro);const l=LS.g('bp_w')||[];l.push(r.d.id);LS.s('bp_w',l);S.tab='me';await refresh();flash('Você entrou na lista de espera. Se o horário liberar, avisamos aqui e o barbeiro também pode te chamar.')};
A.rw=async id=>{await api('DELETE','espera/'+id);LS.s('bp_w',(LS.g('bp_w')||[]).filter(x=>x!=id));delete S.wl[id];refresh();draw()};
A.take=async id=>{const r=await api('POST',`espera/${id}/reservar`);if(!r.ok)return flash(r.d.erro);
if(S.me){await refresh();return flash('Reservado. Código: '+r.d.codigo)}
LS.s('bp_w',(LS.g('bp_w')||[]).filter(x=>x!=id));const l=LS.g('bp_c')||[];l.push(r.d.codigo);LS.s('bp_c',l);S.done=r.d.codigo;await refresh();draw()};
A.find=async()=>{const c=$v('cd').toUpperCase();const r=await api('GET','agendamentos/'+c);if(!r.ok)return flash(r.d.erro);const l=LS.g('bp_c')||[];if(!l.includes(c)){l.push(c);LS.s('bp_c',l)}await refresh();draw()};
A.cancel=async c=>{const r=await api('POST',`agendamentos/${c}/cancelar`);if(!r.ok)flash(r.d.erro);await refresh();draw()};
A.act=async(c,x)=>{const r=await api('POST',`agendamentos/${c}/acao`,{acao:x});if(!r.ok)flash(r.d.erro);await refresh();draw()};
A.login=async()=>{const r=await api('POST','login',{email:$v('e'),senha:$v('w')});if(!r.ok)return flash(r.d.erro);S.me=r.d;await refresh();draw()};
A.regis=async()=>{if($v('w')!=$v('w2'))return flash('As senhas não conferem.');const r=await api('POST','cadastro',{shop:$v('sid'),nome:$v('n'),email:$v('e'),senha:$v('w')});if(!r.ok)return flash(r.d.erro);S.me=r.d;await refresh();draw()};
A.out=async()=>{await api('POST','logout');S.me=null;S.agenda=null;S.view='g';draw()};
const chip=(on,fn,txt,x)=>`<button class="b ${on?'on':''} ${x?'x':''}" onclick="${fn}">${txt}</button>`;
const msg=()=>S.msg?`<div class="al">${E(S.msg)}</div>`:'';
function authV(){return `<header><h1>BARBER <span>POINT</span></h1><button class="b s g" onclick="A.set('view','g')">Voltar</button></header><div class="c"><h2 style="margin-top:0">Área do barbeiro</h2>${msg()}
${S.reg?'<label>ID da barbearia</label><input id="sid"><label>Nome</label><input id="n">':''}<label>E-mail</label><input id="e" type="email"><label>Senha</label><input id="w" type="password">${S.reg?'<label>Confirmar senha</label><input id="w2" type="password">':''}
<button class="p" onclick="${S.reg?'A.regis()':'A.login()'}">${S.reg?'Cadastrar':'Entrar'}</button> <button class="b g" onclick="A.set('reg',${!S.reg})">${S.reg?'Já tenho conta':'Criar conta'}</button></div>`}
function card(a){return `<div class="c"><div class="r"><b>${fd(a.data)} · ${a.hora}</b><span class="tag">${a.status}</span></div><div>${names(a)} com ${E(a.barbeiro)}</div><div class="m">${R(a.total)} · ${a.forma}${cashTxt(a)} · pagamento: ${a.pagamento} · código ${a.codigo}</div>
${a.pagamento=='liberado'&&a.forma=='Pix'?`<div class="al" style="margin-top:8px">Pague via Pix: <b>${PIX}</b></div>`:''}${['pendente','confirmado'].includes(a.status)?`<button class="b s g" style="margin-top:8px" onclick="A.cancel('${a.codigo}')">Cancelar</button>`:''}</div>`}
function guest(){const s=S.sel,g=S.g;let h=`<header><h1>BARBER <span>POINT</span></h1><button class="b s g" onclick="A.set('view','login')">Sou barbeiro</button></header>${msg()}`;
if(S.done)return h+`<div class="c"><h2 style="margin-top:0">Agendamento enviado!</h2><p>Seu código: <b style="font-size:22px;letter-spacing:2px">${S.done}</b></p><p class="m">Guarde este código para consultar ou cancelar. O barbeiro vai confirmar em breve.</p><button class="p" onclick="S.done=null;A.set('tab','me')">Ver meus agendamentos</button></div>`;
const mine=Object.values(S.mine).filter(Boolean),wl=Object.values(S.wl).filter(Boolean);
mine.filter(a=>['pendente','confirmado'].includes(a.status)&&(a.data==TODAY||a.data==TOM)).forEach(a=>h+=`<div class="al">Lembrete: ${a.data==TODAY?'hoje':'amanhã'} às ${a.hora} com ${E(a.barbeiro)} (${names(a)}).</div>`);
wl.filter(w=>w.livre&&!past(w.data,w.hora)).forEach(w=>h+=`<div class="al">Vaga liberada: ${fd(w.data)} às ${w.hora}. <button class="p s" onclick="A.take('${w.id}')">Reservar agora</button></div>`);
h+=`<div class="t">${chip(S.tab=='ag',"A.set('tab','ag')",'Agendar')}${chip(S.tab=='me',"A.set('tab','me')",'Meus agendamentos')}</div>`;
if(S.tab=='ag'){h+=`<h2>1. Serviços</h2><div class="ch">${S.servicos.map(v=>chip(s.s.includes(v.id),`A.tg('s',${v.id})`,`${v.nome} · ${R(v.preco)}`)).join('')}</div>
<h2>2. Barbeiro</h2><div class="ch">${S.barbeiros.map(b=>chip(s.b==b.id,`A.tg('b',${b.id})`,E(b.nome))).join('')}</div>
<h2>3. Data</h2><div class="ch">${DAYS.map(d=>chip(s.d==d,`A.tg('d','${d}')`,fd(d))).join('')}</div>`;
if(s.b&&s.d)h+=`<h2>4. Horário</h2><div class="gr">${SL.map(t=>past(s.d,t)?`<button class="b" disabled>${t}</button>`:chip(s.t==t,`A.tg('t','${t}')`,t,S.ocupados.includes(t))).join('')}</div><p class="m">Horários riscados estão ocupados: toque neles para entrar na lista de espera.</p>`;
h+=`<h2>5. Pagamento</h2><div class="ch">${FORMAS.map(p=>chip(s.m==p,`A.tg('m','${p}')`,p)).join('')}</div>${s.m=='Dinheiro'?`<div class="al" style="margin-top:8px">Precisa de troco? Informe com qual valor vai pagar (deixe em branco se não precisar).<input type="number" min="0" step="0.01" placeholder="Ex.: 50" value="${E(s.cash)}" oninput="A.cash(this.value)"></div>`:''}
<h2>6. Seus dados</h2><input placeholder="Nome" value="${E(g.name)}" oninput="A.f('name',this.value)"><input placeholder="Telefone com DDD" type="tel" value="${E(g.phone)}" oninput="A.f('phone',this.value)">`;
const tot=s.s.reduce((a,i)=>a+(S.servicos.find(x=>x.id==i)||{preco:0}).preco,0);
h+=`<div class="c"><div class="r"><b>Total: ${R(tot)}</b>${s.t&&S.ocupados.includes(s.t)?`<button class="p" onclick="A.wait()">Entrar na lista de espera</button>`:`<button class="p" onclick="A.book()">Confirmar agendamento</button>`}</div></div>`}
else{h+=`<div class="c"><label>Tem um código? Consulte aqui</label><input id="cd" placeholder="Código de 8 caracteres" maxlength="8" style="text-transform:uppercase"><button class="p s" onclick="A.find()">Consultar</button></div>`;
h+=mine.length?mine.sort((a,b)=>(b.data+b.hora).localeCompare(a.data+a.hora)).map(card).join(''):'<p class="m">Nenhum agendamento neste aparelho.</p>';
if(wl.length)h+='<h2>Lista de espera</h2>'+wl.map(w=>`<div class="c r"><span>${fd(w.data)} · ${w.hora}</span><button class="b s g" onclick="A.rw('${w.id}')">Remover</button></div>`).join('')}
return h}
function barber(){const ag=S.agenda||{agendamentos:[],espera:[],ocupados:0,resumo:{bruto:0,taxa:0,liquido:0,taxa_percentual:.2}},rs=ag.resumo;
const B=(id,x,t,p)=>`<button class="${p?'p':'b'} s" onclick="A.act('${id}','${x}')">${t}</button>`;
let h=`<header><h1>BARBER <span>POINT</span></h1><div class="m">${E(S.me.nome)} · <button class="b s g" onclick="A.out()">Sair</button></div></header>${msg()}<div class="ch" style="margin-bottom:10px">${DAYS.map(d=>chip(S.bd==d,`A.set('bd','${d}')`,fd(d))).join('')}</div>
<div class="k"><div class="c"><b>${ag.ocupados}</b><span class="m">atendimentos</span></div><div class="c"><b>${SL.length-ag.ocupados}</b><span class="m">horários livres</span></div><div class="c"><b>${R(rs.bruto)}</b><span class="m">recebido (bruto)</span></div><div class="c"><b>${R(rs.taxa)}</b><span class="m">taxa da barbearia (${Math.round(rs.taxa_percentual*100)}%)</span></div><div class="c"><b>${R(rs.liquido)}</b><span class="m">a receber (líquido)</span></div></div>`;
h+=ag.agendamentos.length?ag.agendamentos.map(a=>`<div class="c"><div class="r"><b>${a.hora} · ${E(a.cliente)}</b><span class="tag">${a.status}</span></div><div>${names(a)}</div><div class="m">${R(a.total)} · ${a.forma}${cashTxt(a)} · pagamento: ${a.pagamento} · ${E(a.telefone)}</div>
<div class="ch" style="margin-top:8px">${a.status=='pendente'?B(a.codigo,'confirmar','Confirmar',1)+B(a.codigo,'recusar','Recusar'):''}${a.status=='confirmado'?B(a.codigo,'concluir','Concluir e liberar pagamento',1)+B(a.codigo,'faltou','Faltou')+B(a.codigo,'cancelar','Cancelar'):''}${a.pagamento=='liberado'?B(a.codigo,'pagar','Registrar pagamento',1):''}
${['pendente','confirmado'].includes(a.status)?`<a class="b s" href="${wa(a.telefone,`Olá ${a.cliente}! Lembrando do seu horário na Barber Point: ${fd(a.data)} às ${a.hora}.`)}" target="_blank" rel="noopener">Lembrar no WhatsApp</a>`:''}</div></div>`).join(''):'<p class="m">Sem agendamentos neste dia.</p>';
if(ag.espera.length)h+='<h2>Lista de espera</h2>'+ag.espera.map(w=>`<div class="c"><div class="r"><b>${w.hora} · ${E(w.cliente)}</b><span class="tag">${w.livre?'vaga livre':'ocupado'}</span></div><div class="m">${names(w)} · ${E(w.telefone)}</div>
<div class="ch" style="margin-top:8px">${w.livre?`<button class="p s" onclick="A.take('${w.id}')">Reservar para ele(a)</button>`:''}<a class="b s" href="${wa(w.telefone,`Olá ${w.cliente}! Vagou o horário de ${fd(w.data)} às ${w.hora} na Barber Point. Quer confirmar?`)}" target="_blank" rel="noopener">Chamar no WhatsApp</a></div></div>`).join('');
return h}
function draw(){if(/INPUT/.test(document.activeElement.tagName)&&!S.msg)return;document.getElementById('app').innerHTML=S.me?barber():S.view=='login'?authV():guest();S.msg=''}
async function refresh(){if(S.me){const r=await api('GET','agenda?data='+S.bd);if(r.ok)S.agenda=r.d;else if(r.status==401){S.me=null}}
else{const s=S.sel;if(s.b&&s.d){const r=await api('GET',`horarios?barbeiro=${s.b}&data=${s.d}`);if(r.ok)S.ocupados=r.d}
for(const c of LS.g('bp_c')||[]){const r=await api('GET','agendamentos/'+c);S.mine[c]=r.ok?r.d:null}
for(const c of LS.g('bp_w')||[]){const r=await api('GET','espera/'+c);S.wl[c]=r.ok?r.d:null}}draw()}
(async()=>{S.servicos=(await api('GET','servicos')).d||[];S.barbeiros=(await api('GET','barbeiros')).d||[];
const m=await api('GET','me');if(m.ok&&m.d)S.me=m.d;await refresh();setInterval(refresh,5000)})();
