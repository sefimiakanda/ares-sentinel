const C={vert:'#3ee0ae',orange:'#ffc857',rouge:'#ff7272',gris:'#6d7d95'};let points=[],seuils,solCourant,carte,pins;
async function api(u,o){let r;try{r=await fetch(u,o)}catch{throw Error('Le serveur ne répond pas. Vérifie ta connexion et réessaie.')}let data;try{data=await r.json()}catch{data={}}if(!r.ok)throw Error(data.detail||`Erreur du serveur (HTTP ${r.status}).`);return data}
function initMap(){carte=L.map('carte-mars',{crs:L.CRS.EPSG4326,center:[-5,137],zoom:1,minZoom:1,maxZoom:7});L.tileLayer('https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg',{maxNativeZoom:7,noWrap:true,attribution:'NASA Mars Trek'}).addTo(carte);pins=L.layerGroup().addTo(carte)}
function drawMap(sites){pins.clearLayers();sites.forEach(s=>{const icon=L.divIcon({className:'',html:`<div style="width:18px;height:18px;border-radius:50%;background:${C[s.verdict.couleur]||C.gris};border:3px solid white"></div>`,iconSize:[18,18]});L.marker([s.lat,s.lon],{icon}).bindTooltip(`<b>${s.nom}</b><br>${s.verdict.texte}`,{permanent:true,direction:'top'}).addTo(pins)})}
function graph(){
  const canvas=document.querySelector('#graphique'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
  const gauche=55,droite=w-12,haut=18,bas=h-38,max=Math.max(points.at(-1)?.sol||1,1);
  const X=sol=>gauche+sol/max*(droite-gauche),Y=val=>haut+(1-val/100)*(bas-haut);
  ctx.fillStyle='#081525';ctx.fillRect(0,0,w,h);ctx.font='12px system-ui';ctx.lineWidth=1;
  [0,50,100].forEach(v=>{ctx.strokeStyle='#223653';ctx.beginPath();ctx.moveTo(gauche,Y(v));ctx.lineTo(droite,Y(v));ctx.stroke();ctx.fillStyle='#94a8c5';ctx.fillText(String(v),18,Y(v)+4)});
  [[seuils.orange,C.orange],[seuils.rouge,C.rouge]].forEach(([value,color])=>{ctx.strokeStyle=color;ctx.setLineDash([6,4]);ctx.beginPath();ctx.moveTo(gauche,Y(value));ctx.lineTo(droite,Y(value));ctx.stroke();ctx.setLineDash([])});
  ctx.strokeStyle='#61a5ff';ctx.lineWidth=2;ctx.beginPath();let started=false;
  points.forEach(p=>{if(p.indice===null){started=false;return}const px=X(p.sol),py=Y(p.indice);if(started)ctx.lineTo(px,py);else{ctx.moveTo(px,py);started=true}});
  ctx.stroke();ctx.fillStyle='#ff7272';points.filter(p=>p.anomalie&&p.indice!==null).forEach(p=>{ctx.beginPath();ctx.arc(X(p.sol),Y(p.indice),2.5,0,Math.PI*2);ctx.fill()});ctx.fillStyle='#94a8c5';ctx.fillText('Sol 0',gauche, h-12);ctx.fillText(`Sol ${max}`,droite-42,h-12);
  const selected=points.find(p=>p.sol===solCourant&&p.indice!==null);
  if(selected){const px=X(selected.sol),py=Y(selected.indice);ctx.strokeStyle='#fff';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(px,haut);ctx.lineTo(px,bas);ctx.stroke();ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(px,py,5,0,Math.PI*2);ctx.fill()}
}
function drawProfile(d){
  const canvas=document.querySelector('#profil'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
  const factors=Object.entries(d.facteurs||{}),labels={froid:'Froid',amplitude:'Amplitude',pression:'Pression',anomalie:'Anomalie'};
  ctx.fillStyle='#081525';ctx.fillRect(0,0,w,h);ctx.font='12px system-ui';ctx.fillStyle='#94a8c5';
  if(!factors.length){ctx.fillText('Profil indisponible : mesures manquantes.',18,38);document.querySelector('#profil-lecture').textContent='Aucun score ne peut être calculé pour ce sol.';return}
  const left=142,right=w-48,top=52,row=47,barWidth=right-left;
  [0,50,100].forEach(value=>{const x=left+barWidth*value/100;ctx.strokeStyle='#223653';ctx.beginPath();ctx.moveTo(x,top-18);ctx.lineTo(x,top+row*factors.length-13);ctx.stroke();ctx.fillText(String(value),x-7,top+row*factors.length+4)});
  factors.forEach(([name,f],i)=>{const y=top+i*row,note=Number(f.note)||0;ctx.fillStyle='#edf4ff';ctx.fillText(labels[name]||name,12,y+5);ctx.fillStyle='#17283c';ctx.fillRect(left,y-8,barWidth,14);ctx.fillStyle=['#61a5ff','#ffc857','#3ee0ae','#ff7272'][i%4];ctx.fillRect(left,y-8,barWidth*Math.max(0,Math.min(note,100))/100,14);ctx.fillStyle='#edf4ff';ctx.fillText(`${note.toFixed(1)}`,right+8,y+5)});
  document.querySelector('#profil-lecture').textContent=`Notes des facteurs sur 100 pour le sol ${d.sol}. Une note élevée augmente l’indice pédagogique, pas le danger réel.`;
}
function renderMetricCards(selector,cards){
  const container=document.querySelector(selector);container.replaceChildren(...cards.map(([value,label])=>{const card=document.createElement('div'),strong=document.createElement('b'),caption=document.createElement('span');card.className='mesure';strong.textContent=value;caption.textContent=label;card.append(strong,caption);return card}));
}
function renderExplorerStats(){
  const valid=points.filter(p=>p.indice!==null);
  if(!valid.length){renderMetricCards('#stats-explorateur',[['—','Aucune mesure']]);return}
  const average=valid.reduce((sum,p)=>sum+p.indice,0)/valid.length;
  const high=valid.reduce((a,b)=>a.indice>b.indice?a:b),low=valid.reduce((a,b)=>a.indice<b.indice?a:b);
  renderMetricCards('#stats-explorateur',[[valid.length.toLocaleString('fr-FR'),'Jours mesurés'],[`${average.toFixed(1)}/100`,'Indice moyen'],[`Sol ${high.sol} · ${high.indice}`,'Indice maximal'],[`Sol ${low.sol} · ${low.indice}`,'Indice minimal']]);
}
function renderAnomalies(data){
  const stats=data.statistiques||{};
  document.querySelector('#total-anomalies').textContent=`${data.total} anomalie(s) parmi ${stats.jours_analyses||0} jours analysés`;
  renderMetricCards('#stats-anomalies',[[String(data.total),'Jours atypiques'],[`${stats.taux_pct??0}%`,'Part des jours analysés'],[stats.intensite_moyenne===null?'—':`${stats.intensite_moyenne}/100`,'Intensité moyenne'],[stats.sol_le_plus_atypique?`Sol ${stats.sol_le_plus_atypique.sol}`:'—','Sol le plus atypique']]);
  const list=document.querySelector('#liste-anomalies');
  if(!data.anomalies.length){const empty=document.createElement('li');empty.textContent='Aucune anomalie détectée dans les jours analysés.';list.replaceChildren(empty);return}
  list.replaceChildren(...data.anomalies.map(a=>{const item=document.createElement('li'),button=document.createElement('button'),title=document.createElement('strong'),detail=document.createElement('span');button.type='button';button.className='anomaly-item';button.dataset.sol=a.sol;title.textContent=`SOL ${a.sol} · ${a.date}`;detail.textContent=`${a.raison||'Variation inhabituelle'} · intensité ${a.intensite}/100 · verdict ${a.verdict}`;button.append(title,detail);item.append(button);return item}));
}
function formatValeur(value,unit=''){return value===null||value===undefined?'n.d.':`${Number(value).toLocaleString('fr-FR',{maximumFractionDigits:1})}${unit}`}
function selectGraphPoint(point){
  if(!point)return;
  solCourant=point.sol;graph();
  document.querySelector('#lecture-graphique').textContent=`SOL ${point.sol} · ${point.date} · indice ${formatValeur(point.indice,'/100')} · min ${formatValeur(point.temp_min,' °C')} · max ${formatValeur(point.temp_max,' °C')} · pression ${formatValeur(point.pression,' Pa')} · ${point.anomalie?'anomalie détectée':'pas d’anomalie détectée'}.`;
  choose(point.sol);
}
function graphPointAt(clientX){
  const canvas=document.querySelector('#graphique'),rect=canvas.getBoundingClientRect(),x=(clientX-rect.left)*canvas.width/rect.width,max=Math.max(points.at(-1)?.sol||1,1),left=55,right=canvas.width-12;
  return points.filter(p=>p.indice!==null).reduce((nearest,p)=>Math.abs(left+p.sol/max*(right-left)-x)<Math.abs(left+nearest.sol/max*(right-left)-x)?p:nearest,points.find(p=>p.indice!==null));
}
function render(d){solCourant=d.sol;document.querySelector('#sol-input').value=d.sol;document.querySelector('#date-input').value=d.date;document.querySelector('#sol-affiche').textContent='SOL '+d.sol;let v=document.querySelector('#verdict');v.className='verdict '+d.verdict.couleur;v.textContent=d.verdict.texte+' · '+d.indice+'/100';document.querySelector('#date-saison').innerHTML=`<div class="ligne"><span>Date terrestre</span><b>${d.date}</b></div><div class="ligne"><span>Saison martienne</span><b>${d.saison}</b></div><div class="ligne"><span>Ls</span><b>${Math.round(d.ls)}°</b></div>`;let m=d.mesures;document.querySelector('#mesures').innerHTML=[['Temp. min',m.temp_min_c+' °C'],['Temp. max',m.temp_max_c+' °C'],['Amplitude',m.amplitude_c+' °C'],['Pression',m.pression_pa+' Pa']].map(a=>`<div class="mesure"><b>${a[1]}</b><span>${a[0]}</span></div>`).join('');document.querySelector('#facteurs').innerHTML=Object.entries(d.facteurs||{}).map(([n,f])=>`<div class="facteur">${n} · ${f.valeur}<div class="barre"><div style="width:${f.note}%"></div></div></div>`).join('');drawProfile(d);graph()}
async function withButtonFeedback(button,label,action){if(button?.disabled)return;if(!button){await action();return}const initial=button.textContent;button.disabled=true;button.setAttribute('aria-busy','true');button.textContent=label;try{await action()}finally{button.disabled=false;button.removeAttribute('aria-busy');button.textContent=initial}}
let selectionRequest=0,assistantRequest=0;
async function choose(sol,button){await withButtonFeedback(button,'Chargement…',async()=>{const request=++selectionRequest;try{const[d,c]=await Promise.all([api('/api/sortie/'+sol),api('/api/carte?sol='+sol)]);if(request!==selectionRequest)return;render(d);drawMap(c.sites)}catch(e){if(request===selectionRequest)alert(e.message)}})}
async function ask(q){const question=q.trim(),discussion=document.querySelector('#discussion'),button=document.querySelector('#btn-envoyer');if(!question){discussion.textContent='Écris une question avant de l’envoyer.';return}await withButtonFeedback(button,'Réponse…',async()=>{const request=++assistantRequest;discussion.textContent='Consultation des données en cours…';try{const r=await api('/api/assistant',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,sol:solCourant})});if(request===assistantRequest)discussion.textContent=[r.constat,...r.preuves,r.limites&&`Limites : ${r.limites}`].filter(Boolean).join('\n\n')}catch(e){if(request===assistantRequest)discussion.textContent=`Erreur OpenRouter : ${e.message}`}})}
async function start(){
  const s=await api('/api/serie');points=s.points;seuils=s.seuils;renderExplorerStats();initMap();
  const last=points.filter(p=>p.indice!==null).at(-1);
  document.querySelector('#btn-sol').onclick=()=>choose(document.querySelector('#sol-input').value,document.querySelector('#btn-sol'));
  document.querySelector('#btn-dernier').onclick=()=>choose(last.sol,document.querySelector('#btn-dernier'));
  document.querySelector('#btn-envoyer').onclick=()=>ask(document.querySelector('#question').value);
  document.querySelector('#question').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.isComposing){e.preventDefault();ask(e.currentTarget.value)}});
  document.querySelector('#graphique').addEventListener('click',e=>selectGraphPoint(graphPointAt(e.clientX)));
  document.querySelector('#graphique').addEventListener('keydown',e=>{
    if(!['ArrowLeft','ArrowRight'].includes(e.key))return;e.preventDefault();
    const valid=points.filter(p=>p.indice!==null),current=valid.findIndex(p=>p.sol===solCourant),next=Math.max(0,Math.min(valid.length-1,current+(e.key==='ArrowRight'?1:-1)));
    if(valid.length)selectGraphPoint(valid[next]);
  });
  document.querySelector('#liste-anomalies').addEventListener('click',e=>{
    const button=e.target.closest('button[data-sol]');if(!button)return;
    montrerVue('tableau');choose(button.dataset.sol,button);
  });
  await choose(last.sol);
  const [a,h]=await Promise.allSettled([api('/api/anomalies'),api('/api/sante')]);
  if(a.status==='fulfilled')renderAnomalies(a.value);else document.querySelector('#liste-anomalies').textContent=`Impossible de charger les anomalies : ${a.reason.message}`;
  const chip=document.querySelector('#chip');
  if(h.status==='fulfilled'){chip.textContent=h.value.assistant==='openrouter'?'OpenRouter · '+h.value.assistant_modele:'OpenRouter indisponible';chip.title=h.value.assistant_raison||''}
  else{chip.textContent='État OpenRouter inconnu';chip.title=h.reason.message}
}
function montrerVue(nom){
  const vue=document.querySelector('#vue-'+nom);
  if(!vue)return;
  document.querySelectorAll('.vue').forEach(v=>v.classList.toggle('actif',v.id==='vue-'+nom));
  document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('actif',b.dataset.vue===nom));
  if(nom==='historique'&&points.length)graph();
  if(nom==='tableau'&&carte)setTimeout(()=>carte.invalidateSize(),50);
  const behavior=window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth';
  vue.scrollIntoView({behavior,block:'start'});
}
document.querySelector('#onglets').addEventListener('click',e=>{
  const bouton=e.target.closest('button[data-vue]');
  if(bouton)montrerVue(bouton.dataset.vue);
});
start().then(()=>{
  document.querySelector('#btn-date').onclick=()=>{
    const cible=new Date(document.querySelector('#date-input').value);
    if(Number.isNaN(cible.getTime()))return;
    const point=points.reduce((a,b)=>Math.abs(new Date(a.date)-cible)<Math.abs(new Date(b.date)-cible)?a:b);
    choose(point.sol,document.querySelector('#btn-date'));
  };
}).catch(e=>{document.querySelector('#chip').textContent='Erreur de chargement';document.querySelector('#chip').title=e.message;console.error(e)});
