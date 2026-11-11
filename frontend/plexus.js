// Effet Plexus : un réseau de points reliés par des lignes, qui suit la souris.
// La couleur du réseau change avec le verdict (vert / orange / rouge) : Plexus.setColor("#3ddc97")
(() => {
  const canvas = document.getElementById("plexus");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const reduit = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const DIST = 130, DIST_SOURIS = 170;
  let L, H, points = [];
  const souris = { x: -999, y: -999 };
  const couleur = [255, 106, 61], cible = [255, 106, 61];

  function creer() {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    L = innerWidth; H = innerHeight;
    canvas.width = L * dpr; canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const n = Math.max(35, Math.min(120, Math.round((L * H) / 14000)));
    points = Array.from({ length: n }, () => ({
      x: Math.random() * L, y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.5, vy: (Math.random() - 0.5) * 0.5,
      r: 1 + Math.random() * 1.5,
    }));
  }

  function trait(a, b, alpha, c) {
    ctx.strokeStyle = `rgba(${c},${alpha})`;
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
  }

  function image() {
    for (let i = 0; i < 3; i++) couleur[i] += (cible[i] - couleur[i]) * 0.04; // transition douce
    const c = couleur.map(Math.round).join(",");
    ctx.clearRect(0, 0, L, H);
    ctx.lineWidth = 1;
    for (const p of points) {
      if (!reduit) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > L) p.vx *= -1;
        if (p.y < 0 || p.y > H) p.vy *= -1;
        const dx = souris.x - p.x, dy = souris.y - p.y, d = Math.hypot(dx, dy);
        if (d < DIST_SOURIS && d > 1) { p.x += (dx / d) * 0.6; p.y += (dy / d) * 0.6; } // attirés par la souris
      }
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${c},0.85)`; ctx.fill();
    }
    for (let i = 0; i < points.length; i++) {
      const a = points[i];
      for (let j = i + 1; j < points.length; j++) {
        const d = Math.hypot(a.x - points[j].x, a.y - points[j].y);
        if (d < DIST) trait(a, points[j], (1 - d / DIST) * 0.45, c);
      }
      const ds = Math.hypot(a.x - souris.x, a.y - souris.y);
      if (ds < DIST_SOURIS) trait(a, souris, (1 - ds / DIST_SOURIS) * 0.8, c);
    }
    requestAnimationFrame(image);
  }

  const bouger = (x, y) => { souris.x = x; souris.y = y; };
  addEventListener("mousemove", (e) => bouger(e.clientX, e.clientY));
  addEventListener("touchmove", (e) => bouger(e.touches[0].clientX, e.touches[0].clientY), { passive: true });
  document.addEventListener("mouseleave", () => bouger(-999, -999));
  addEventListener("resize", creer);

  window.Plexus = {
    setColor(hex) {
      const n = parseInt(hex.slice(1), 16);
      cible[0] = n >> 16; cible[1] = (n >> 8) & 255; cible[2] = n & 255;
    },
  };
  creer();
  image();
})();
