// Ares Sentinel - frontend en JavaScript simple (aucun framework).

const COULEURS = { vert: "#3ddc97", orange: "#ffb347", rouge: "#ff5a4d", gris: "#8a8f98" };
const EN_LOCAL = ["localhost", "127.0.0.1"].includes(location.hostname);
const NOMS_FACTEURS = {
  froid: "❄️ Froid",
  amplitude: "🌡️ Écart jour/nuit",
  pression: "🌀 Variation de pression",
  anomalie: "⚠️ Jour inhabituel",
};

// Variables globales : l'état de la page
let points = [];          // tous les sols (pour le graphique)
let solsValides = [];     // seulement les sols qui ont un indice
let seuils = null;
let solCourant = null;
let sites = [];

async function api(url, options) {
  const reponse = await fetch(url, options);
  if (!reponse.ok) throw new Error("Erreur " + reponse.status);
  return reponse.json();
}

// ---------- CARTE ----------
// Fenêtre de la carte : on zoome sur la zone où sont les sites
const VUE = { lonMin: 60, lonMax: 160, latMin: -40, latMax: 40 };

function versPixel(lon, lat, canvas) {
  const x = ((lon - VUE.lonMin) / (VUE.lonMax - VUE.lonMin)) * canvas.width;
  const y = ((VUE.latMax - lat) / (VUE.latMax - VUE.latMin)) * canvas.height;
  return { x, y };
}

function dessinerCarte() {
  const canvas = document.getElementById("carte");
  const ctx = canvas.getContext("2d");

  // Fond
  const fond = ctx.createLinearGradient(0, 0, 0, canvas.height);
  fond.addColorStop(0, "#5a2a1c");
  fond.addColorStop(1, "#2e150f");
  ctx.fillStyle = fond;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Grille (tous les 20° de longitude, 20° de latitude)
  ctx.strokeStyle = "rgba(255,255,255,0.12)";
  ctx.fillStyle = "rgba(255,255,255,0.45)";
  ctx.font = "13px sans-serif";
  ctx.lineWidth = 1;
  for (let lon = VUE.lonMin; lon <= VUE.lonMax; lon += 20) {
    const { x } = versPixel(lon, 0, canvas);
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    ctx.fillText(lon + "°E", x + 4, canvas.height - 6);
  }
  for (let lat = VUE.latMin; lat <= VUE.latMax; lat += 20) {
    const { y } = versPixel(VUE.lonMin, lat, canvas);
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
    ctx.fillText(lat + "°", 6, y - 4);
  }
  // Équateur plus visible
  const eq = versPixel(VUE.lonMin, 0, canvas).y;
  ctx.strokeStyle = "rgba(255,255,255,0.3)";
  ctx.beginPath(); ctx.moveTo(0, eq); ctx.lineTo(canvas.width, eq); ctx.stroke();

  // Sites
  for (const site of sites) {
    const { x, y } = versPixel(site.lon, site.lat, canvas);
    const couleur = COULEURS[site.verdict.couleur];
    const actif = site.donnees_reelles;

    ctx.beginPath();
    ctx.arc(x, y, actif ? 16 : 11, 0, Math.PI * 2);
    ctx.fillStyle = couleur;
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = actif ? "#fff" : "rgba(255,255,255,0.4)";
    ctx.stroke();

    if (actif) { // anneau qui pulse autour du site actif
      const t = (performance.now() % 1800) / 1800;
      ctx.beginPath(); ctx.arc(x, y, 16 + t * 24, 0, Math.PI * 2);
      ctx.strokeStyle = couleur; ctx.globalAlpha = 1 - t; ctx.lineWidth = 2; ctx.stroke();
      ctx.globalAlpha = 1;
    }

    ctx.fillStyle = "#fff";
    ctx.font = "bold 14px sans-serif";
    ctx.fillText(site.nom, x + 22, y + 5);
    ctx.font = "12px sans-serif";
    ctx.fillStyle = "rgba(255,255,255,0.75)";
    const sousTitre = actif ? `${site.verdict.texte} (indice ${site.indice})` : site.verdict.texte;
    ctx.fillText(sousTitre, x + 22, y + 21);
  }
}

function cliquerCarte(evenement) {
  const canvas = document.getElementById("carte");
  const rect = canvas.getBoundingClientRect();
  const x = (evenement.clientX - rect.left) * (canvas.width / rect.width);
  const y = (evenement.clientY - rect.top) * (canvas.height / rect.height);
  for (const site of sites) {
    const p = versPixel(site.lon, site.lat, canvas);
    if (Math.hypot(p.x - x, p.y - y) < 22) {
      if (site.donnees_reelles) {
        document.getElementById("verdict-panneau").scrollIntoView({ behavior: "smooth" });
      } else {
        alert(site.nom + "\nAltitude : " + site.altitude_km + " km\n\nPas de mesures dans cette version : je préfère ne pas inventer de verdict.");
      }
      return;
    }
  }
}

// ---------- VERDICT ----------
// Anime l'indice de 0 jusqu'à sa valeur
function compter(el, cible) {
  const debut = performance.now(), duree = 700;
  const pas = (t) => {
    const k = Math.min((t - debut) / duree, 1);
    el.textContent = `Indice de risque : ${(cible * (1 - Math.pow(1 - k, 3))).toFixed(1)} / 100`;
    if (k < 1) requestAnimationFrame(pas);
  };
  requestAnimationFrame(pas);
}

function afficherVerdict(d) {
  const boite = document.getElementById("verdict");
  boite.className = "verdict " + d.verdict.couleur;
  boite.innerHTML = "";
  boite.append(d.verdict.texte);
  const petit = document.createElement("small");
  if (d.indice === null) petit.textContent = "Indice indisponible";
  else compter(petit, d.indice);
  boite.append(petit);
  if (window.Plexus) Plexus.setColor(COULEURS[d.verdict.couleur]); // le réseau Plexus prend la couleur du verdict

  document.getElementById("sol-affiche").textContent = "Sol " + d.sol;
  document.getElementById("date-saison").textContent =
    `${d.date} · ${d.saison}` + (d.saison_poussiere ? " · saison des tempêtes de poussière" : "");

  const m = d.mesures;
  const valeur = (v, u) => (v === null ? "–" : v + u);
  document.getElementById("mesures").innerHTML = "";
  [
    ["Temp. min", valeur(m.temp_min_c, " °C")],
    ["Temp. max", valeur(m.temp_max_c, " °C")],
    ["Écart", valeur(m.amplitude_c, " °C")],
    ["Pression", valeur(m.pression_pa, " Pa")],
  ].forEach(([nom, val]) => {
    const div = document.createElement("div");
    div.className = "mesure";
    div.innerHTML = `<b></b><span></span>`;
    div.querySelector("b").textContent = val;
    div.querySelector("span").textContent = nom;
    document.getElementById("mesures").append(div);
  });

  const zoneFacteurs = document.getElementById("facteurs");
  zoneFacteurs.innerHTML = "";
  if (d.facteurs) {
    for (const [cle, f] of Object.entries(d.facteurs)) {
      const bloc = document.createElement("div");
      bloc.className = "facteur";
      bloc.innerHTML = `<div></div><div class="barre"><div></div></div>`;
      bloc.firstChild.textContent = `${NOMS_FACTEURS[cle]} — ${f.valeur} — note ${f.note}/100 (poids ${f.poids * 100} %)`;
      bloc.querySelector(".barre div").style.width = f.note + "%";
      zoneFacteurs.append(bloc);
    }
  } else {
    zoneFacteurs.textContent = "Il manque des mesures pour ce sol.";
  }

  const alerte = document.getElementById("alerte-anomalie");
  alerte.hidden = !d.est_anomalie;
  if (d.est_anomalie) alerte.textContent = "🤖 Jour détecté comme anomalie : " + d.raison_anomalie + ".";
  document.getElementById("avertissement").textContent = d.avertissement;
}

async function choisirSol(sol) {
  solCourant = sol;
  const [detail, carte] = await Promise.all([api("/api/sortie/" + sol), api("/api/carte?sol=" + sol)]);
  sites = carte.sites;
  afficherVerdict(detail);
  dessinerCarte();
  dessinerGraphique();
  const idx = solsValides.findIndex((p) => p.sol === sol);
  if (idx >= 0) document.getElementById("slider").value = idx;
}

// ---------- GRAPHIQUE ----------
const MARGE = { gauche: 40, droite: 10, haut: 10, bas: 25 };

function xDe(sol, canvas) {
  const maxSol = points[points.length - 1].sol;
  return MARGE.gauche + (sol / maxSol) * (canvas.width - MARGE.gauche - MARGE.droite);
}
function yDe(indice, canvas) {
  return MARGE.haut + (1 - indice / 100) * (canvas.height - MARGE.haut - MARGE.bas);
}

function dessinerGraphique() {
  if (!points.length) return;
  const canvas = document.getElementById("graphique");
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#1a0f0d";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Axes et seuils
  ctx.font = "12px sans-serif";
  for (const [valeur, couleur, nom] of [
    [seuils.orange, COULEURS.orange, "orange"],
    [seuils.rouge, COULEURS.rouge, "rouge"],
  ]) {
    const y = yDe(valeur, canvas);
    ctx.strokeStyle = couleur;
    ctx.setLineDash([6, 4]);
    ctx.beginPath(); ctx.moveTo(MARGE.gauche, y); ctx.lineTo(canvas.width - MARGE.droite, y); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = couleur;
    ctx.fillText(nom + " ≥ " + valeur.toFixed(0), MARGE.gauche + 6, y - 4);
  }
  ctx.fillStyle = "#b59a90";
  for (const v of [0, 50, 100]) ctx.fillText(v, 8, yDe(v, canvas) + 4);
  const maxSol = points[points.length - 1].sol;
  for (let s = 0; s <= maxSol; s += 1000) ctx.fillText("sol " + s, xDe(s, canvas) - 14, canvas.height - 6);

  // Courbe
  ctx.strokeStyle = "#e2572b";
  ctx.lineWidth = 1;
  ctx.beginPath();
  let enCours = false;
  for (const p of points) {
    if (p.indice === null) { enCours = false; continue; }
    const x = xDe(p.sol, canvas), y = yDe(p.indice, canvas);
    if (!enCours) { ctx.moveTo(x, y); enCours = true; } else ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Anomalies
  ctx.fillStyle = COULEURS.rouge;
  for (const p of points) {
    if (p.anomalie && p.indice !== null) {
      ctx.beginPath();
      ctx.arc(xDe(p.sol, canvas), yDe(p.indice, canvas), 2.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // Sol sélectionné
  if (solCourant !== null) {
    const x = xDe(solCourant, canvas);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(x, MARGE.haut); ctx.lineTo(x, canvas.height - MARGE.bas); ctx.stroke();
  }
}

function cliquerGraphique(evenement) {
  const canvas = document.getElementById("graphique");
  const rect = canvas.getBoundingClientRect();
  const x = (evenement.clientX - rect.left) * (canvas.width / rect.width);
  const maxSol = points[points.length - 1].sol;
  const solVise = ((x - MARGE.gauche) / (canvas.width - MARGE.gauche - MARGE.droite)) * maxSol;
  // On prend le sol valide le plus proche
  let meilleur = solsValides[0];
  for (const p of solsValides) {
    if (Math.abs(p.sol - solVise) < Math.abs(meilleur.sol - solVise)) meilleur = p;
  }
  choisirSol(meilleur.sol);
}

// ---------- ANOMALIES ----------
async function chargerAnomalies() {
  const data = await api("/api/anomalies?limite=20");
  document.getElementById("total-anomalies").textContent =
    `${data.total} jours anormaux sur toute la période. Voici les 20 plus marqués (clique pour voir le détail).`;
  const liste = document.getElementById("liste-anomalies");
  liste.innerHTML = "";
  for (const a of data.anomalies) {
    const li = document.createElement("li");
    const couleur = { VERT: "vert", ORANGE: "orange", ROUGE: "rouge" }[a.verdict] || "gris";
    const pastille = document.createElement("span");
    pastille.className = "pastille";
    pastille.style.background = COULEURS[couleur];
    li.append(pastille, `Sol ${a.sol} (${a.date}) – ${a.raison} – intensité ${a.intensite}/100`);
    li.onclick = () => { choisirSol(a.sol); window.scrollTo({ top: 0, behavior: "smooth" }); };
    liste.append(li);
  }
}

// ---------- ASSISTANT ----------
function ajouterMessage(classe, contenu) {
  const zone = document.getElementById("discussion");
  const div = document.createElement("div");
  div.className = "msg " + classe;
  if (typeof contenu === "string") div.textContent = contenu;
  else div.append(contenu);
  zone.append(div);
  zone.scrollTop = zone.scrollHeight;
  return div;
}

function construireReponse(r) {
  const conteneur = document.createElement("div");
  const ajouterTitre = (texte) => { const h = document.createElement("h4"); h.textContent = texte; conteneur.append(h); };

  ajouterTitre("Constat");
  const p = document.createElement("div"); p.textContent = r.constat; conteneur.append(p);

  if (r.preuves.length) {
    ajouterTitre("Preuves (données)");
    const ul = document.createElement("ul");
    r.preuves.forEach((t) => { const li = document.createElement("li"); li.textContent = t; ul.append(li); });
    conteneur.append(ul);
  }
  ajouterTitre("Limites");
  const l = document.createElement("div"); l.textContent = r.limites; conteneur.append(l);

  const s = document.createElement("div");
  s.className = "petit";
  let texteSource = `Source : ${r.source} · ${r.type}`;
  if (r.outils_utilises && r.outils_utilises.length) texteSource += ` · outils appelés : ${r.outils_utilises.join(", ")}`;
  s.textContent = texteSource;
  conteneur.append(s);

  if (r.chiffres_non_verifies && r.chiffres_non_verifies.length) {
    const alerte = document.createElement("div");
    alerte.className = "alerte";
    alerte.textContent =
      "⚠️ Chiffres non retrouvés dans les données : " + r.chiffres_non_verifies.join(", ") +
      ". Le modèle a peut-être inventé ou mal recopié : fie-toi aux Preuves.";
    conteneur.append(alerte);
  }

  if (r.sol_cite !== null && r.sol_cite !== undefined) {
    const b = document.createElement("button");
    b.textContent = "Voir le sol " + r.sol_cite;
    b.style.marginTop = "6px";
    b.onclick = () => { choisirSol(r.sol_cite); window.scrollTo({ top: 0, behavior: "smooth" }); };
    conteneur.append(b);
  }
  return conteneur;
}

async function poserQuestion(texte) {
  texte = texte.trim();
  if (!texte) return;
  ajouterMessage("moi", texte);
  document.getElementById("question").value = "";
  const attente = ajouterMessage("ia", "⏳ L'assistant consulte les données…");
  try {
    const reponse = await api("/api/assistant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: texte, sol: solCourant }),
    });
    attente.remove();
    ajouterMessage("ia", construireReponse(reponse));
  } catch (e) {
    attente.remove();
    ajouterMessage("ia", "Oups, le serveur ne répond pas. Est-il bien lancé ?");
  }
}

// ---------- DÉMARRAGE ----------
async function demarrer() {
  try {
    const serie = await api("/api/serie");
    points = serie.points;
    seuils = serie.seuils;
    solsValides = points.filter((p) => p.indice !== null);

    const slider = document.getElementById("slider");
    slider.max = solsValides.length - 1;
    slider.oninput = () => choisirSol(solsValides[Number(slider.value)].sol);
    document.getElementById("btn-dernier").onclick = () => choisirSol(solsValides[solsValides.length - 1].sol);
    document.getElementById("carte").onclick = cliquerCarte;
    document.getElementById("graphique").onclick = cliquerGraphique;
    document.getElementById("btn-envoyer").onclick = () => poserQuestion(document.getElementById("question").value);
    document.getElementById("question").onkeydown = (e) => { if (e.key === "Enter") poserQuestion(e.target.value); };

    const exemples = await api("/api/exemples");
    for (const ex of exemples.exemples) {
      const b = document.createElement("button");
      b.textContent = ex;
      b.onclick = () => poserQuestion(ex);
      document.getElementById("exemples").append(b);
    }

    await choisirSol(solsValides[solsValides.length - 1].sol);
    if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
      (function boucleCarte() { dessinerCarte(); requestAnimationFrame(boucleCarte); })();
    }
    await chargerAnomalies();
    const sante = await api("/api/sante");
    ajouterMessage(
      "ia",
      sante.assistant === "ollama"
        ? `Bonjour ! Je suis branché sur un LLM local gratuit (Ollama, modèle ${sante.assistant_modele}). Je ne cite que les chiffres que mes outils lisent dans les données de Curiosity. Essaie un des exemples ci-dessus.`
        : `Bonjour ! Mode sans LLM : ${EN_LOCAL ? sante.assistant_raison + " " : ""}En attendant, je réponds avec des règles, uniquement à partir des mesures de Curiosity.`
    );
  } catch (e) {
    document.getElementById("verdict").textContent = "Impossible de joindre le serveur. Lance le backend (voir README).";
    console.error(e);
  }
}

demarrer();
