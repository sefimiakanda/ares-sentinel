const C={vert:'#3ee0ae',orange:'#ffc857',rouge:'#ff7272',gris:'#6d7d95'};let points=[],seuils,solCourant,carte,pins;
async function api(u,o){let r;try{r=await fetch(u,o)}catch{throw Error('Le serveur ne répond pas. Vérifie ta connexion et réessaie.')}let data;try{data=await r.json()}catch{data={}}if(!r.ok)throw Error(data.detail||`Erreur du serveur (HTTP ${r.status}).`);return data}
function initMap(){carte=L.map('carte-mars',{crs:L.CRS.EPSG4326,center:[-5,137],zoom:1,minZoom:1,maxZoom:7});L.tileLayer('https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg',{maxNativeZoom:7,noWrap:true,attribution:'NASA Mars Trek'}).addTo(carte);pins=L.layerGroup().addTo(carte)}
function drawMap(sites){pins.clearLayers();sites.forEach(s=>{const icon=L.divIcon({className:'',html:`<div style="width:18px;height:18px;border-radius:50%;background:${C[s.verdict.couleur]||C.gris};border:3px solid white"></div>`,iconSize:[18,18]});L.marker([s.lat,s.lon],{icon}).bindTooltip(`<b>${s.nom}</b><br>${s.verdict.texte}`,{permanent:true,direction:'top'}).addTo(pins)})}
function graph(){const c=document.querySelector('#graphique'),x=c.getContext('2d'),w=c.width,h=c.height,L=45,B=35,max=points.at(-1).sol,X=s=>L+s/max*(w-L-12),Y=v=>15+(1-v/100)*(h-50);x.fillStyle='#081525';x.fillRect(0,0,w,h);x.font='12px system-ui';[[seuils.orange,C.orange],[seuils.rouge,C.rouge]].forEach(a=>{x.strokeStyle=a[1];x.setLineDash([6,4]);x.beginPath();x.moveTo(L,Y(a[0]));x.lineTo(w-12,Y(a[0]));x.stroke();x.setLineDash([])});x.strokeStyle='#61a5ff';x.beginPath();let on=false;points.forEach(p=>{if(p.indice===null){on=false;return}const px=X(p.sol),py=Y(p.indice);if(on)x.lineTo(px,py);else{x.moveTo(px,py);on=true}});x.stroke();x.fillStyle='#94a8c5';[0,50,100].forEach(v=>x.fillText(v,12,Y(v)));if(solCourant){x.strokeStyle='#fff';x.beginPath();x.moveTo(X(solCourant),15);x.lineTo(X(solCourant),h-B);x.stroke()}}
function render(d){solCourant=d.sol;document.querySelector('#sol-input').value=d.sol;document.querySelector('#date-input').value=d.date;document.querySelector('#sol-affiche').textContent='SOL '+d.sol;let v=document.querySelector('#verdict');v.className='verdict '+d.verdict.couleur;v.textContent=d.verdict.texte+' · '+d.indice+'/100';document.querySelector('#date-saison').innerHTML=`<div class="ligne"><span>Date terrestre</span><b>${d.date}</b></div><div class="ligne"><span>Saison martienne</span><b>${d.saison}</b></div><div class="ligne"><span>Ls</span><b>${Math.round(d.ls)}°</b></div>`;let m=d.mesures;document.querySelector('#mesures').innerHTML=[['Temp. min',m.temp_min_c+' °C'],['Temp. max',m.temp_max_c+' °C'],['Amplitude',m.amplitude_c+' °C'],['Pression',m.pression_pa+' Pa']].map(a=>`<div class="mesure"><b>${a[1]}</b><span>${a[0]}</span></div>`).join('');document.querySelector('#facteurs').innerHTML=Object.entries(d.facteurs||{}).map(([n,f])=>`<div class="facteur">${n} · ${f.valeur}<div class="barre"><div style="width:${f.note}%"></div></div></div>`).join('');graph()}
async function withButtonFeedback(button,label,action){if(button?.disabled)return;if(!button){await action();return}const initial=button.textContent;button.disabled=true;button.setAttribute('aria-busy','true');button.textContent=label;try{await action()}finally{button.disabled=false;button.removeAttribute('aria-busy');button.textContent=initial}}
let selectionRequest=0,assistantRequest=0;
async function choose(sol,button){await withButtonFeedback(button,'Chargement…',async()=>{const request=++selectionRequest;try{const[d,c]=await Promise.all([api('/api/sortie/'+sol),api('/api/carte?sol='+sol)]);if(request!==selectionRequest)return;render(d);drawMap(c.sites)}catch(e){if(request===selectionRequest)alert(e.message)}})}
async function ask(q){const question=q.trim(),discussion=document.querySelector('#discussion'),button=document.querySelector('#btn-envoyer');if(!question){discussion.textContent='Écris une question avant de l’envoyer.';return}await withButtonFeedback(button,'Réponse…',async()=>{const request=++assistantRequest;discussion.textContent='Consultation des données en cours…';try{const r=await api('/api/assistant',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,sol:solCourant})});if(request===assistantRequest)discussion.textContent=[r.constat,...r.preuves,r.limites&&`Limites : ${r.limites}`].filter(Boolean).join('\n\n')}catch(e){if(request===assistantRequest)discussion.textContent=`Erreur OpenRouter : ${e.message}`}})}
async function start(){const s=await api('/api/serie');points=s.points;seuils=s.seuils;initMap();const last=points.filter(p=>p.indice!==null).at(-1);await choose(last.sol);document.querySelector('#btn-sol').onclick=()=>choose(document.querySelector('#sol-input').value,document.querySelector('#btn-sol'));document.querySelector('#btn-dernier').onclick=()=>choose(last.sol,document.querySelector('#btn-dernier'));document.querySelector('#btn-envoyer').onclick=()=>ask(document.querySelector('#question').value);document.querySelector('#question').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.isComposing){e.preventDefault();ask(e.currentTarget.value)}});const h=await api('/api/sante');const chip=document.querySelector('#chip');chip.textContent=h.assistant==='openrouter'?'OpenRouter · '+h.assistant_modele:'OpenRouter indisponible';chip.title=h.assistant_raison||''}
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
}).catch(console.error);
