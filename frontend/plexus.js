// Effet Plexus : un réseau de points reliés par des lignes, qui réagit à la souris.
// Il vit DANS l'en-tête (le canvas prend la taille de son parent) et ne touche pas au reste de la page.
// La couleur peut changer avec le verdict : Plexus.setColor("#34d399")
(() => {
  const canvas = document.getElementById("plexus");
  if (!canvas) return;
  const zone = canvas.parentElement;
  const ctx = canvas.getContext("2d");
  const reduit = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const DIST = 120, DIST_SOURIS = 160;
  let L = 0, H = 0, points = [], visible = true;
  const souris = { x: -999, y: -999 };
  const couleur = [110, 168, 254], cible = [110, 168, 254];

  function creer() {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    L = zone.clientWidth; H = zone.clientHeight;
    canvas.width = L * dpr; canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const n = Math.max(28, Math.min(80, Math.round((L * H) / 9000)));
    points = Array.from({ length: n }, () => ({
      x: Math.random() * L, y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.4, vy: (Math.random() - 0.5) * 0.4, r: 1 + Math.random() * 1.3,
    }));
  }

  function trait(a, b, alpha, c) {
    ctx.strokeStyle = `rgba(${c},${alpha})`;
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
  }

  function image() {
    requestAnimationFrame(image);
    if (!visible || !L) return;
    for (let i = 0; i < 3; i++) couleur[i] += (cible[i] - couleur[i]) * 0.05; // transition douce
    const c = couleur.map(Math.round).join(",");
    ctx.clearRect(0, 0, L, H);
    ctx.lineWidth = 1;
    for (const p of points) {
      if (!reduit) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > L) p.vx *= -1;
        if (p.y < 0 || p.y > H) p.vy *= -1;
        const dx = souris.x - p.x, dy = souris.y - p.y, d = Math.hypot(dx, dy);
        if (d < DIST_SOURIS && d > 1) { p.x += (dx / d) * 0.5; p.y += (dy / d) * 0.5; } // attirés par la souris
      }
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${c},0.7)`; ctx.fill();
    }
    for (let i = 0; i < points.length; i++) {
      const a = points[i];
      for (let j = i + 1; j < points.length; j++) {
        const d = Math.hypot(a.x - points[j].x, a.y - points[j].y);
        if (d < DIST) trait(a, points[j], (1 - d / DIST) * 0.35, c);
      }
      const ds = Math.hypot(a.x - souris.x, a.y - souris.y);
      if (ds < DIST_SOURIS) trait(a, souris, (1 - ds / DIST_SOURIS) * 0.7, c);
    }
  }

  zone.addEventListener("mousemove", (e) => {
    const r = zone.getBoundingClientRect();
    souris.x = e.clientX - r.left; souris.y = e.clientY - r.top;
  });
  zone.addEventListener("mouseleave", () => { souris.x = -999; souris.y = -999; });
  new ResizeObserver(creer).observe(zone);                                   // s'adapte quand la fenêtre change
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(zone); // pause quand l'en-tête n'est plus visible

  window.Plexus = {
    setColor(hex) {
      const n = parseInt(hex.slice(1), 16);
      cible[0] = n >> 16; cible[1] = (n >> 8) & 255; cible[2] = n & 255;
    },
  };
  creer();
  image();
})();
