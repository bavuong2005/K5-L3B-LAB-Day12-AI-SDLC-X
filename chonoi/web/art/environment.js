/*
 * Chợ Nổi - environment art (100% procedural, PixiJS v7 API).
 * Không dùng ảnh/âm/mạng ngoài. Chỉ lấy "phong cách" 2D nhiều lớp nhìn ngang dưới nước;
 * mọi hình tự vẽ bằng PIXI.Graphics + canvas 2D (tạo texture một lần, cache theo PIXI).
 *
 * window.ChoNoiArt.env = {
 *   createUnderwater(PIXI, {width,height,surfaceY,pxPerDepth,depthMax,pxPerX,seed})
 *   createSurface(PIXI, {width,height,surfaceY,pxPerX,worldWidth,dockX,seed})
 *   createFish(PIXI, kind)         createCrocodile(PIXI)      createNode(PIXI, kind)
 *   createQuanScene(PIXI, {width,height,pxPerUnit})            createFX(PIXI)
 * }
 * Toạ độ nhìn ngang: screenX = worldX - camX ; screenY = surfaceY + depthPx - camDepthPx
 * (worldX = x * pxPerX, depthPx = d * pxPerDepth).
 */
(function () {
  'use strict';
  var G = typeof window !== 'undefined' ? window : globalThis;
  G.ChoNoiArt = G.ChoNoiArt || {};

  var TAU = Math.PI * 2;
  var DEF = { width: 1280, height: 720, surfaceY: 190, pxPerDepth: 40, depthMax: 30, pxPerX: 40, worldX: 100 };

  /* ---------- helpers ---------- */
  function rng(seed) {
    var a = (seed || 1) >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function hex(n) { return '#' + ('000000' + (n >>> 0).toString(16)).slice(-6); }
  function mixC(a, b, t) {
    var ar = a >> 16 & 255, ag = a >> 8 & 255, ab = a & 255, br = b >> 16 & 255, bg = b >> 8 & 255, bb = b & 255;
    return (Math.round(lerp(ar, br, t)) << 16) | (Math.round(lerp(ag, bg, t)) << 8) | Math.round(lerp(ab, bb, t));
  }
  function cvs(w, h) { var c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
  function mod(a, n) { return ((a % n) + n) % n; }

  function cache(PIXI) { return PIXI.__chonoiEnvTex || (PIXI.__chonoiEnvTex = {}); }
  function tex(PIXI, key, make, repeat) {
    var c = cache(PIXI);
    if (c[key]) return c[key];
    var t = PIXI.Texture.from(make());
    if (repeat) t.baseTexture.wrapMode = PIXI.WRAP_MODES.REPEAT;
    return (c[key] = t);
  }
  function sprite(PIXI, t, ax, ay) {
    var s = new PIXI.Sprite(t);
    s.anchor.set(ax === undefined ? 0.5 : ax, ay === undefined ? 0.5 : ay);
    return s;
  }
  function add(PIXI, s) { s.blendMode = PIXI.BLEND_MODES.ADD; return s; }

  /* ---------- shared textures ---------- */
  function T_soft(PIXI) {
    return tex(PIXI, 'soft', function () {
      var c = cvs(64, 64), x = c.getContext('2d'), g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
      g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.35, 'rgba(255,255,255,0.55)');
      g.addColorStop(1, 'rgba(255,255,255,0)');
      x.fillStyle = g; x.fillRect(0, 0, 64, 64); return c;
    });
  }
  function T_bubble(PIXI) {
    return tex(PIXI, 'bubble', function () {
      var c = cvs(64, 64), x = c.getContext('2d');
      var g = x.createRadialGradient(32, 32, 14, 32, 32, 30);
      g.addColorStop(0, 'rgba(255,255,255,0.04)'); g.addColorStop(0.85, 'rgba(210,245,255,0.28)'); g.addColorStop(1, 'rgba(255,255,255,0.75)');
      x.fillStyle = g; x.beginPath(); x.arc(32, 32, 30, 0, TAU); x.fill();
      x.fillStyle = 'rgba(255,255,255,0.9)'; x.beginPath(); x.ellipse(22, 20, 7, 4, -0.7, 0, TAU); x.fill();
      return c;
    });
  }
  function T_ray(PIXI) {
    return tex(PIXI, 'ray', function () {
      var c = cvs(64, 512), x = c.getContext('2d'), g = x.createLinearGradient(0, 0, 64, 0);
      g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(0.5, 'rgba(255,255,255,1)'); g.addColorStop(1, 'rgba(255,255,255,0)');
      x.fillStyle = g; x.fillRect(0, 0, 64, 512);
      x.globalCompositeOperation = 'destination-in';
      var v = x.createLinearGradient(0, 0, 0, 512);
      v.addColorStop(0, 'rgba(0,0,0,1)'); v.addColorStop(0.6, 'rgba(0,0,0,0.35)'); v.addColorStop(1, 'rgba(0,0,0,0)');
      x.fillStyle = v; x.fillRect(0, 0, 64, 512); return c;
    });
  }
  function T_vignette(PIXI) {
    return tex(PIXI, 'vig', function () {
      var c = cvs(256, 144), x = c.getContext('2d');
      var g = x.createRadialGradient(128, 72, 40, 128, 72, 150);
      g.addColorStop(0, 'rgba(0,10,25,0)'); g.addColorStop(0.6, 'rgba(0,10,25,0.18)'); g.addColorStop(1, 'rgba(0,6,16,0.8)');
      x.fillStyle = g; x.fillRect(0, 0, 256, 144); return c;
    });
  }
  function T_puff(PIXI) {
    return tex(PIXI, 'puff', function () {
      var c = cvs(96, 96), x = c.getContext('2d'), r = rng(7);
      for (var i = 0; i < 9; i++) {
        var px = 48 + (r() - 0.5) * 30, py = 48 + (r() - 0.5) * 30, rad = 20 + r() * 14;
        var g = x.createRadialGradient(px, py, 0, px, py, rad);
        g.addColorStop(0, 'rgba(255,255,255,0.55)'); g.addColorStop(1, 'rgba(255,255,255,0)');
        x.fillStyle = g; x.fillRect(0, 0, 96, 96);
      }
      return c;
    });
  }
  function T_miniFish(PIXI) {
    return tex(PIXI, 'minifish', function () {
      var c = cvs(40, 16), x = c.getContext('2d');
      x.fillStyle = '#fff'; x.beginPath(); x.moveTo(36, 8); x.quadraticCurveTo(24, 0, 10, 6); x.lineTo(2, 1); x.lineTo(4, 8); x.lineTo(2, 15);
      x.lineTo(10, 10); x.quadraticCurveTo(24, 16, 36, 8); x.fill(); return c;
    });
  }

  /* ---------- silhouette / terrain texture painters (2D canvas) ---------- */
  function wrapAt(x, W, fn) { fn(x); if (x < 260) fn(x + W); if (x > W - 260) fn(x - W); }
  function blade(c, base, h, w, bend, up) {
    return function (x) {
      c.beginPath(); c.moveTo(x - w, base);
      c.quadraticCurveTo(x - w * 0.3 + bend * 0.3, base - h * 0.5 * up, x + bend, base - h * up);
      c.quadraticCurveTo(x + w * 0.3 + bend * 0.3, base - h * 0.5 * up, x + w, base); c.fill();
    };
  }
  // lá dài kiểu rong/rau (có viền tối + gradient sáng ở ngọn)
  function leafBlade(c, x, base, h, w, bend, dark, lite, outline) {
    var g = c.createLinearGradient(0, base, 0, base - h);
    g.addColorStop(0, dark); g.addColorStop(1, lite);
    c.beginPath(); c.moveTo(x - w, base);
    c.bezierCurveTo(x - w * 0.9, base - h * 0.45, x + bend * 0.5 - w * 0.5, base - h * 0.8, x + bend, base - h);
    c.bezierCurveTo(x + bend * 0.5 + w * 0.7, base - h * 0.75, x + w * 0.9, base - h * 0.4, x + w, base); c.closePath();
    c.fillStyle = g; c.fill(); c.lineWidth = 2; c.strokeStyle = outline; c.stroke();
    c.strokeStyle = 'rgba(255,255,255,0.18)'; c.lineWidth = 1.2; c.beginPath(); c.moveTo(x, base - 4);
    c.quadraticCurveTo(x + bend * 0.2, base - h * 0.5, x + bend * 0.95, base - h * 0.96); c.stroke();
  }
  function lilyPad(c, x, y, rx, ry, rot, dark, lite) {
    c.save(); c.translate(x, y); c.rotate(rot);
    var g = c.createLinearGradient(0, -ry, 0, ry); g.addColorStop(0, lite); g.addColorStop(1, dark);
    c.fillStyle = g; c.strokeStyle = '#124a28'; c.lineWidth = 2;
    c.beginPath(); c.ellipse(0, 0, rx, ry, 0, 0.18, TAU - 0.18); c.lineTo(0, 0); c.closePath(); c.fill(); c.stroke();
    c.strokeStyle = 'rgba(255,255,255,0.25)'; c.lineWidth = 1;
    for (var i = 0; i < 6; i++) { var a = 0.5 + i * 0.9; c.beginPath(); c.moveTo(0, 0); c.lineTo(Math.cos(a) * rx * 0.9, Math.sin(a) * ry * 0.9); c.stroke(); }
    c.restore();
  }
  function rockPath(c, x, y, w, h, r) {
    c.beginPath(); c.moveTo(x - w / 2, y);
    var n = 6, pts = [];
    for (var i = 0; i <= n; i++) {
      var a = Math.PI + (i / n) * Math.PI, k = 0.8 + r() * 0.25;
      pts.push([x + Math.cos(a) * w / 2 * k, y + Math.sin(a) * h * k]);
    }
    for (i = 0; i < pts.length; i++) c.lineTo(pts[i][0], pts[i][1]);
    c.lineTo(x + w / 2, y); c.closePath();
  }
  function paintStalks(c, W, H, r, col, n, hMin, hMax) {
    c.fillStyle = col; c.strokeStyle = col; c.lineCap = 'round';
    for (var i = 0; i < n; i++) {
      var x = r() * W, h = hMin + r() * (hMax - hMin), bend = (r() - 0.5) * 50;
      wrapAt(x, W, function (xx) {
        c.lineWidth = 2 + r() * 2.5;
        c.beginPath(); c.moveTo(xx, H); c.quadraticCurveTo(xx + bend * 0.2, H - h * 0.5, xx + bend, H - h); c.stroke();
        if (h > hMin + (hMax - hMin) * 0.4) { c.beginPath(); c.ellipse(xx + bend, H - h, 20 + r() * 14, 5 + r() * 3, bend * 0.004, 0, TAU); c.fill(); }
      });
    }
  }
  function clearTop(c, W) { c.clearRect(0, 0, W, 3); }
  function T_far(PIXI) {
    return tex(PIXI, 'far', function () {
      var W = 2048, H = 560, c0 = cvs(W, H), c = c0.getContext('2d'), r = rng(11), i;
      c.fillStyle = '#2aa593';
      for (i = 0; i < 8; i++) { (function () { var x = r() * W, w = 260 + r() * 300, h = 70 + r() * 110;
        wrapAt(x, W, function (xx) { rockPath(c, xx, H, w, h, r); c.fill(); }); })(); }
      paintStalks(c, W, H, r, '#23998a', 36, 140, 380);
      c.fillStyle = '#1f8f86';
      for (i = 0; i < 40; i++) { (function () { var x = r() * W, h = 120 + r() * 260, b = (r() - 0.5) * 70;
        wrapAt(x, W, blade(c, H, h, 6 + r() * 6, b, 1)); })(); }
      c.globalCompositeOperation = 'destination-in';
      var fade = c.createLinearGradient(0, 0, 0, H);
      fade.addColorStop(0, 'rgba(0,0,0,0)'); fade.addColorStop(0.5, 'rgba(0,0,0,0.65)'); fade.addColorStop(1, 'rgba(0,0,0,0.9)');
      c.fillStyle = fade; c.fillRect(0, 0, W, H); clearTop(c, W);
      return c0;
    }, true);
  }
  function T_mid(PIXI) {
    return tex(PIXI, 'mid', function () {
      var W = 2048, H = 520, c0 = cvs(W, H), c = c0.getContext('2d'), r = rng(23), i;
      c.fillStyle = '#16866f';
      for (i = 0; i < 6; i++) { (function () { var x = r() * W, w = 200 + r() * 260, h = 90 + r() * 100;
        wrapAt(x, W, function (xx) { rockPath(c, xx, H, w, h, r); c.fill(); }); })(); }
      c.fillStyle = '#157a68';
      for (i = 0; i < 60; i++) { (function () { var x = r() * W, h = 90 + r() * 240, b = (r() - 0.5) * 60;
        wrapAt(x, W, blade(c, H, h, 5 + r() * 6, b, 1)); })(); }
      paintStalks(c, W, H, r, '#127462', 16, 180, 420);
      for (i = 0; i < 7; i++) { (function () { var x = r() * W, h = 220 + r() * 160, t = (r() - 0.5) * 0.3;
        wrapAt(x, W, function (xx) { c.save(); c.translate(xx, H); c.rotate(t); c.fillStyle = '#5a4a2a'; c.fillRect(-7, -h, 14, h);
          c.beginPath(); c.moveTo(-7, -h); c.lineTo(7, -h - 12); c.lineTo(7, -h); c.fill();
          c.strokeStyle = 'rgba(50,60,40,0.7)'; c.lineWidth = 1.2;
          for (var k = 1; k < 5; k++) { c.beginPath(); c.moveTo(7, -h + k * 10); c.quadraticCurveTo(40, -h + k * 18 + 25, 80, -h + 20 + k * 6); c.stroke(); }
          c.restore(); }); })(); }
      c.globalCompositeOperation = 'destination-in';
      var fade = c.createLinearGradient(0, 0, 0, H);
      fade.addColorStop(0, 'rgba(0,0,0,0)'); fade.addColorStop(0.4, 'rgba(0,0,0,0.75)'); fade.addColorStop(1, 'rgba(0,0,0,0.95)');
      c.fillStyle = fade; c.fillRect(0, 0, W, H); clearTop(c, W);
      return c0;
    }, true);
  }
  function paintRoots(c, W, H, r, col, n, lenMin, lenMax, thick) {
    c.strokeStyle = col; c.lineCap = 'round';
    for (var i = 0; i < n; i++) {
      var x = r() * W, len = lenMin + r() * (lenMax - lenMin);
      wrapAt(x, W, function (xx) {
        c.lineWidth = thick * (0.6 + r() * 0.8);
        for (var k = 0; k < 9; k++) {
          var dx = (r() - 0.5) * 70, l = len * (0.45 + r() * 0.55), sw = (r() - 0.5) * 40;
          c.beginPath(); c.moveTo(xx + dx * 0.3, 8);
          c.bezierCurveTo(xx + dx, l * 0.35, xx + dx + sw, l * 0.7, xx + dx + sw * 1.4, l); c.stroke();
        }
        c.fillStyle = col; c.beginPath(); c.ellipse(xx, 6, 48 + r() * 30, 11 + r() * 5, 0, 0, TAU); c.fill();
      });
    }
  }
  function T_hang(PIXI, kind) {
    return tex(PIXI, 'hang' + kind, function () {
      var W = 2048, H = kind === 0 ? 360 : 280, c0 = cvs(W, H), c = c0.getContext('2d'), r = rng(31 + kind);
      if (kind === 0) paintRoots(c, W, H, r, 'rgba(20,70,70,0.7)', 8, 150, 330, 2.2);
      else paintRoots(c, W, H, r, 'rgba(10,50,55,0.75)', 5, 100, 230, 3);
      return c0;
    }, true);
  }
  function T_stilt(PIXI) { // cột nhà sàn/bến buông từ mặt nước
    return tex(PIXI, 'stilt', function () {
      var W = 2048, H = 560, c0 = cvs(W, H), c = c0.getContext('2d'), r = rng(41);
      for (var i = 0; i < 12; i++) { (function () { var x = r() * W, h = 200 + r() * 330, w = 10 + r() * 8, wi = 80 + r() * 120;
        wrapAt(x, W, function (xx) {
          var g = c.createLinearGradient(xx - w / 2, 0, xx + w / 2, 0); g.addColorStop(0, '#6a5a3a'); g.addColorStop(1, '#2f4a3a');
          c.globalAlpha = 0.38; c.fillStyle = g; c.fillRect(xx - w / 2, 0, w, h); c.fillRect(xx + wi - w / 2, 0, w, h - 40);
          c.beginPath(); c.moveTo(xx - w / 2, h); c.lineTo(xx, h + 16); c.lineTo(xx + w / 2, h); c.fill();
          c.fillStyle = '#4a5a3a'; c.fillRect(xx - w / 2, 70, wi + w, 6); c.fillRect(xx - w / 2, 150, wi + w, 5);
          c.strokeStyle = '#4a5a3a'; c.lineWidth = 4; c.beginPath(); c.moveTo(xx, 74); c.lineTo(xx + wi, 150); c.moveTo(xx + wi, 74); c.lineTo(xx, 150); c.stroke();
          c.globalAlpha = 1; }); })(); }
      return c0;
    }, true);
  }
  function T_fore(PIXI) { // lá sen/súng + rong tối phía trước
    return tex(PIXI, 'fore', function () {
      var W = 2048, H = 420, c0 = cvs(W, H), c = c0.getContext('2d'), r = rng(53), i;
      c.fillStyle = 'rgba(8,60,50,0.92)';
      for (i = 0; i < 14; i++) { (function () { var x = r() * W, h = 120 + r() * 300, b = (r() - 0.5) * 110;
        wrapAt(x, W, blade(c, H + 6, h, 9 + r() * 9, b, 1)); })(); }
      for (i = 0; i < 8; i++) { (function () { var x = r() * W, y = H - 30 - r() * 90, rx = 50 + r() * 50;
        wrapAt(x, W, function (xx) { c.fillStyle = 'rgba(10,80,55,0.95)'; c.beginPath(); c.ellipse(xx, y, rx, rx * 0.28, (r() - 0.5) * 0.5, 0, TAU); c.fill();
          c.strokeStyle = 'rgba(10,80,55,0.95)'; c.lineWidth = 4; c.beginPath(); c.moveTo(xx, y); c.quadraticCurveTo(xx + 10, y + 60, xx - 6, H); c.stroke(); }); })(); }
      c.clearRect(0, 0, W, 3);
      return c0;
    }, true);
  }
  function T_floor(PIXI) {
    return tex(PIXI, 'floor', function () {
      var W = 2048, H = 320, c0 = cvs(W, H), c = c0.getContext('2d'), r = rng(67), x, i;
      function top(x) { return 60 + Math.sin(x / W * TAU * 3) * 14 + Math.sin(x / W * TAU * 7 + 1) * 7 + Math.sin(x / W * TAU * 13) * 3; }
      var g = c.createLinearGradient(0, 40, 0, H);
      g.addColorStop(0, '#f0cb86'); g.addColorStop(0.3, '#d9a560'); g.addColorStop(1, '#8a5a30');
      c.fillStyle = g; c.beginPath(); c.moveTo(0, H);
      for (x = 0; x <= W; x += 8) c.lineTo(x, top(x));
      c.lineTo(W, H); c.closePath(); c.fill();
      c.strokeStyle = 'rgba(255,240,190,0.7)'; c.lineWidth = 3; c.beginPath();
      for (x = 0; x <= W; x += 8) c[x ? 'lineTo' : 'moveTo'](x, top(x) + 1); c.stroke();
      c.strokeStyle = 'rgba(120,70,20,0.18)'; c.lineWidth = 2;
      for (i = 0; i < 80; i++) { var rx = r() * W, ry = 80 + r() * 200, rl = 30 + r() * 80;
        wrapAt(rx, W, function (xx) { c.beginPath(); c.moveTo(xx, ry); c.quadraticCurveTo(xx + rl / 2, ry - 6, xx + rl, ry); c.stroke(); }); }
      for (i = 0; i < 18; i++) {
        (function () {
          var rx = r() * W, w = 40 + r() * 110, h = 24 + r() * 44, by = top(rx) + 14 + r() * 10;
          wrapAt(rx, W, function (xx) {
            rockPath(c, xx, by, w, h, r);
            var rg = c.createLinearGradient(xx - w / 2, by - h, xx + w / 2, by);
            rg.addColorStop(0, '#a89a86'); rg.addColorStop(0.5, '#6a6258'); rg.addColorStop(1, '#3a342c');
            c.fillStyle = rg; c.fill(); c.strokeStyle = '#2a241c'; c.lineWidth = 2; c.stroke();
            c.strokeStyle = 'rgba(255,240,215,0.35)'; c.lineWidth = 2; c.beginPath(); c.arc(xx - w * 0.08, by, w * 0.4, Math.PI * 1.1, Math.PI * 1.6); c.stroke();
            c.fillStyle = 'rgba(90,150,70,0.6)'; c.beginPath(); c.ellipse(xx + w * 0.1, by - h * 0.8, w * 0.22, h * 0.14, 0, 0, TAU); c.fill();
          });
        })();
      }
      var cols = [['#2f8a3c', '#7bd04a'], ['#2f9a5c', '#8fe06a'], ['#3a8a30', '#a8e050']];
      for (i = 0; i < 60; i++) { (function () { var rx = r() * W, h = 40 + r() * 100, b = (r() - 0.5) * 36, cc = cols[i % 3];
        wrapAt(rx, W, function (xx) { leafBlade(c, xx, top(xx) + 10, h, 4 + r() * 3, b, cc[0], cc[1], '#1a5a2a'); }); })(); }
      for (i = 0; i < 70; i++) { var sx = r() * W; c.fillStyle = 'rgba(255,240,210,' + (0.25 + r() * 0.4) + ')'; c.beginPath(); c.ellipse(sx, top(sx) + 14 + r() * 100, 2 + r() * 4, 1.5 + r() * 2, 0, 0, TAU); c.fill(); }
      return c0;
    }, true);
  }
  function T_edge(PIXI, side) { // cụm cây nước cao hai bên khung (xanh tươi bão hoà)
    return tex(PIXI, 'edge' + side, function () {
      var W = 340, H = 900, c0 = cvs(W, H), c = c0.getContext('2d'), r = rng(200 + side), i;
      var cols = [['#1d7a3a', '#6ed04a'], ['#2a8a4a', '#8fe05a'], ['#16683a', '#4fc05a'], ['#2f9a3a', '#b4ea5a']];
      var n = 18;
      for (i = 0; i < n; i++) {
        var u = i / (n - 1), x = side ? W - 20 - u * 230 + (r() - 0.5) * 30 : 20 + u * 230 + (r() - 0.5) * 30;
        var h = 260 + (1 - u) * 560 * (0.55 + r() * 0.45), bend = (side ? -1 : 1) * (30 + r() * 110) * (r() < 0.2 ? -0.5 : 1), cc = cols[i % 4];
        leafBlade(c, x, H + 8, h, 11 + r() * 12, bend, cc[0], cc[1], '#134a26');
      }
      // lá sen/súng rộng
      for (i = 0; i < 4; i++) { var px = side ? W - 60 - r() * 160 : 60 + r() * 160, py = H - 40 - r() * 180;
        c.strokeStyle = '#1d6a38'; c.lineWidth = 4; c.beginPath(); c.moveTo(px, H); c.quadraticCurveTo(px + (r() - 0.5) * 30, py + 80, px, py); c.stroke();
        lilyPad(c, px, py, 70 + r() * 26, 26 + r() * 8, (r() - 0.5) * 0.5, '#1d7a3a', '#5ec040'); }
      c.clearRect(0, 0, W, 3);
      return c0;
    });
  }
  function T_caustic(PIXI) {
    return tex(PIXI, 'caustic', function () {
      var S = 256, c0 = cvs(S, S), c = c0.getContext('2d'), im = c.createImageData(S, S), d = im.data, y, x;
      var P = [[2, 1, 0.3], [1, -2, 1.7], [-3, 1, 2.9], [2, 3, 4.1]];
      for (y = 0; y < S; y++) for (x = 0; x < S; x++) {
        var v = 0;
        for (var k = 0; k < 4; k++) v += Math.sin(TAU * (P[k][0] * x + P[k][1] * y) / S + P[k][2]);
        var a = Math.pow(Math.max(0, 1 - Math.abs(v) / 1.15), 5), i = (y * S + x) * 4;
        d[i] = 255; d[i + 1] = 250; d[i + 2] = 210; d[i + 3] = Math.min(255, a * 360);
      }
      c.putImageData(im, 0, 0); return c0;
    }, true);
  }
  function T_causticFade(PIXI) { // nửa trên mặt nước: hoa nắng mờ dần xuống sâu (không lặp theo chiều dọc)
    return tex(PIXI, 'causticFade', function () {
      var Wd = 512, Hd = 520, c0 = cvs(Wd, Hd), c = c0.getContext('2d'), im = c.createImageData(Wd, Hd), d = im.data, y, x;
      var P = [[4, 2, 0.3], [2, -4, 1.7], [-6, 2, 2.9], [4, 6, 4.1]];
      for (y = 0; y < Hd; y++) for (x = 0; x < Wd; x++) {
        var v = 0;
        for (var k = 0; k < 4; k++) v += Math.sin(TAU * (P[k][0] * x + P[k][1] * y) / Wd + P[k][2]);
        var a = Math.pow(Math.max(0, 1 - Math.abs(v) / 1.15), 5) * Math.pow(1 - y / Hd, 1.6), i = (y * Wd + x) * 4;
        d[i] = 255; d[i + 1] = 250; d[i + 2] = 210; d[i + 3] = Math.min(255, a * 360);
      }
      c.putImageData(im, 0, 0); return c0;
    }, true);
  }
  function T_log(PIXI) { // khúc gỗ trôi rêu phủ + nấm
    return tex(PIXI, 'log', function () {
      var W = 560, H = 230, c0 = cvs(W, H), c = c0.getContext('2d'), r = rng(9), i;
      var g = c.createLinearGradient(0, 40, 0, 190); g.addColorStop(0, '#9a7a52'); g.addColorStop(0.5, '#6a4a2c'); g.addColorStop(1, '#3a2614');
      c.fillStyle = g; c.strokeStyle = '#2a1a0c'; c.lineWidth = 3;
      c.beginPath(); c.moveTo(20, 150); c.bezierCurveTo(30, 70, 120, 56, 220, 66); c.bezierCurveTo(330, 74, 430, 40, 530, 20);
      c.lineTo(548, 40); c.bezierCurveTo(520, 80, 440, 110, 340, 150); c.bezierCurveTo(240, 188, 100, 200, 20, 150); c.closePath(); c.fill(); c.stroke();
      c.strokeStyle = 'rgba(30,18,8,0.5)'; c.lineWidth = 2;
      for (i = 0; i < 12; i++) { var y = 62 + i * 9; c.beginPath(); c.moveTo(60 + r() * 40, y + 30); c.bezierCurveTo(180, y + 10 + r() * 20, 340, y + 4, 480 + r() * 40, y - 30 + r() * 10); c.stroke(); }
      c.fillStyle = '#3a2a16'; c.beginPath(); c.ellipse(36, 118, 20, 38, 0.1, 0, TAU); c.fill(); c.strokeStyle = '#8a6a3c'; c.lineWidth = 2;
      for (i = 1; i < 4; i++) { c.beginPath(); c.ellipse(36, 118, 20 - i * 5, 38 - i * 9, 0.1, 0, TAU); c.stroke(); }
      c.fillStyle = 'rgba(80,170,70,0.75)';
      for (i = 0; i < 14; i++) { c.beginPath(); c.ellipse(80 + i * 32, 70 - (i % 3) * 4 + Math.sin(i) * 10, 22, 7, 0.1, 0, TAU); c.fill(); }
      [[190, 62, 1], [320, 60, 0.8], [420, 40, 1.1]].forEach(function (m) { c.save(); c.translate(m[0], m[1]); c.scale(m[2], m[2]);
        c.fillStyle = '#e8d8b8'; c.fillRect(-3, -6, 6, 10); c.fillStyle = '#d88a3a'; c.beginPath(); c.ellipse(0, -8, 16, 8, 0, Math.PI, 0); c.fill(); c.fillStyle = '#c8702a'; c.fillRect(-16, -8, 32, 3); c.restore(); });
      return c0;
    });
  }
  function T_jar(PIXI, broken) { // chum đất nung
    return tex(PIXI, 'jar' + broken, function () {
      var W = 240, H = 220, c0 = cvs(W, H), c = c0.getContext('2d');
      c.save(); c.translate(120, 205); if (broken) c.rotate(-0.5);
      var g = c.createLinearGradient(-80, 0, 80, 0); g.addColorStop(0, '#9a4a22'); g.addColorStop(0.35, '#e08a4a'); g.addColorStop(1, '#8a3a18');
      c.fillStyle = g; c.strokeStyle = '#4a1e0a'; c.lineWidth = 3;
      c.beginPath(); c.moveTo(-42, -10); c.bezierCurveTo(-95, -60, -80, -150, -46, -165); c.lineTo(-52, -178); c.lineTo(52, -178); c.lineTo(46, -165);
      c.bezierCurveTo(80, -150, 95, -60, 42, -10); c.quadraticCurveTo(0, 6, -42, -10); c.fill(); c.stroke();
      c.fillStyle = '#1a0a04'; c.beginPath(); c.ellipse(0, -176, 48, 11, 0, 0, TAU); c.fill(); c.stroke();
      c.strokeStyle = '#c86a30'; c.lineWidth = 3; c.beginPath(); c.moveTo(-60, -80); c.bezierCurveTo(-30, -66, 30, -66, 62, -80); c.stroke();
      c.fillStyle = 'rgba(80,160,60,0.65)'; c.beginPath(); c.ellipse(-30, -30, 26, 10, 0, 0, TAU); c.ellipse(40, -120, 20, 8, 0, 0, TAU); c.fill();
      c.fillStyle = 'rgba(255,230,190,0.4)'; c.beginPath(); c.ellipse(-44, -100, 7, 30, 0.2, 0, TAU); c.fill();
      c.restore(); return c0;
    });
  }
  function T_wreck(PIXI) { // xuồng chìm
    return tex(PIXI, 'wreck', function () {
      var W = 520, H = 260, c0 = cvs(W, H), c = c0.getContext('2d');
      c.save(); c.translate(250, 175); c.rotate(-0.2);
      var g = c.createLinearGradient(0, -70, 0, 60);
      g.addColorStop(0, '#8a6a42'); g.addColorStop(1, '#3d2a18');
      c.fillStyle = g; c.beginPath(); c.moveTo(-210, -50);
      c.bezierCurveTo(-190, 30, -100, 60, 20, 60); c.bezierCurveTo(120, 60, 190, 20, 230, -70);
      c.lineTo(205, -62); c.bezierCurveTo(150, -10, 80, 5, -20, 5); c.bezierCurveTo(-110, 5, -170, -20, -210, -50); c.closePath(); c.fill();
      c.strokeStyle = '#2a1a0c'; c.lineWidth = 2.5; c.stroke();
      c.fillStyle = '#1a1410'; c.beginPath(); c.moveTo(-200, -44); c.bezierCurveTo(-160, -12, -90, 2, -10, 2); c.bezierCurveTo(80, 2, 150, -8, 215, -64);
      c.bezierCurveTo(150, -30, 60, -22, -20, -22); c.bezierCurveTo(-100, -22, -160, -34, -200, -44); c.fill();
      c.strokeStyle = '#a07a50'; c.lineWidth = 7; c.lineCap = 'round';
      for (var i = 0; i < 7; i++) { var x = -150 + i * 55; c.beginPath(); c.moveTo(x, -18 + Math.abs(x) * 0.02); c.quadraticCurveTo(x + 8, -52 - (i % 3) * 8, x + 14, -78 + (i % 2) * 14); c.stroke(); }
      c.strokeStyle = 'rgba(0,0,0,0.35)'; c.lineWidth = 2;
      for (i = 1; i < 4; i++) { c.beginPath(); c.moveTo(-190 + i * 10, -40 + i * 18); c.bezierCurveTo(-100, 30 + i * 8, 100, 30 + i * 6, 220 - i * 10, -60 + i * 12); c.stroke(); }
      c.fillStyle = '#0a0806'; c.beginPath(); c.ellipse(60, 28, 26, 14, 0.1, 0, TAU); c.fill();
      c.fillStyle = 'rgba(80,170,70,0.75)';
      for (i = 0; i < 12; i++) { c.beginPath(); c.ellipse(-180 + i * 38, -30 + (i % 4) * 14, 14, 6, 0.3, 0, TAU); c.fill(); }
      c.strokeStyle = '#8a6a44'; c.lineWidth = 6; c.beginPath(); c.moveTo(120, -50); c.lineTo(200, -125); c.stroke();
      c.restore();
      var s = c.createLinearGradient(0, 160, 0, 260); s.addColorStop(0, '#e6c07c'); s.addColorStop(1, '#c08a50');
      c.fillStyle = s; c.beginPath(); c.moveTo(0, H); c.lineTo(0, 232); c.quadraticCurveTo(130, 168, 250, 188); c.quadraticCurveTo(380, 160, W, 235); c.lineTo(W, H); c.fill();
      return c0;
    });
  }

  /* ============================================================
   * createUnderwater
   * ============================================================ */
  function createUnderwater(PIXI, o) {
    o = o || {};
    var W = o.width || DEF.width, H = o.height || DEF.height;
    var surfaceY = o.surfaceY !== undefined ? o.surfaceY : DEF.surfaceY;
    var pxD = o.pxPerDepth || DEF.pxPerDepth, dMax = o.depthMax || DEF.depthMax, pxX = o.pxPerX || DEF.pxPerX;
    var floorY = surfaceY + dMax * pxD, totalH = floorY + 250, maxCam = Math.max(0, totalH - H);
    var worldW = o.worldWidth || DEF.worldX * pxX;
    var r = rng(o.seed || 5), i;
    var root = new PIXI.Container();
    var cont = new PIXI.Container(); root.addChild(cont);

    // nền gradient theo độ sâu (ngọc lam sáng -> xanh biển, không đen)
    var gh = Math.min(2048, Math.ceil(totalH));
    var gt = tex(PIXI, 'grad' + totalH, function () {
      var c = cvs(4, gh), x = c.getContext('2d'), g = x.createLinearGradient(0, 0, 0, gh), span = totalH - surfaceY;
      [[0, '#6fe6d2'], [70, '#43d0c4'], [260, '#27b4b8'], [560, '#1a96b4'], [880, '#1590b0'], [1150, '#1280a8'], [1300, '#0f70a0'], [span, '#0c5c8c']].forEach(function (s) { g.addColorStop(clamp(s[0] / span, 0, 1), s[1]); });
      x.fillStyle = g; x.fillRect(0, 0, 4, gh); return c;
    });
    var bg = new PIXI.Sprite(gt); bg.width = W; bg.height = totalH - surfaceY; cont.addChild(bg);

    var rays = new PIXI.Container(); cont.addChild(rays);
    var rayList = [];
    for (i = 0; i < 9; i++) {
      var s = add(PIXI, sprite(PIXI, T_ray(PIXI), 0.5, 0));
      s.height = 1000 + r() * 400; s.width = 90 + r() * 170; s.tint = 0xfff6c8;
      rayList.push({ s: s, x: (i + 0.3 + r() * 0.5) * W / 8 - 100, ph: r() * TAU, sp: 0.2 + r() * 0.3, a: 0.16 + r() * 0.14, rot: 0.26 + (r() - 0.5) * 0.1 });
      rays.addChild(s);
    }
    var cTop = add(PIXI, new PIXI.TilingSprite(T_causticFade(PIXI), W, 520)); cTop.tint = 0xfff6c0; cont.addChild(cTop);

    function tiling(t, h, fx, fy, hang) {
      var ts = new PIXI.TilingSprite(t, W, h); cont.addChild(ts);
      return { s: ts, h: h, fx: fx, fy: fy, hang: !!hang };
    }
    var L = [];
    var hang0 = tiling(T_stilt(PIXI), 560, 0.2, 0.45, true);
    var far = tiling(T_far(PIXI), 560, 0.22, 0.38);
    var mid = tiling(T_mid(PIXI), 520, 0.5, 0.68);
    L.push(hang0, far, mid);

    var school = new PIXI.Container(); cont.addChild(school);
    var fishes = [];
    for (i = 0; i < 26; i++) {
      var f = sprite(PIXI, T_miniFish(PIXI)); f.tint = 0x137a86; f.alpha = 0.5; f.scale.set(0.7 + r() * 0.8);
      var grp = i % 3;
      fishes.push({ s: f, g: grp, ox: (r() - 0.5) * 140, oy: (r() - 0.5) * 60, sp: 24 + grp * 8 + r() * 6, ph: r() * TAU, y: surfaceY + 250 + grp * 330 });
      school.addChild(f);
    }
    var hang1 = tiling(T_hang(PIXI, 0), 360, 0.7, 0.85, true);
    L.push(hang1);

    var floor = tiling(T_floor(PIXI), 320, 1, 1);
    L.push(floor);
    var fcaust = add(PIXI, new PIXI.TilingSprite(T_caustic(PIXI), W, 330)); fcaust.tint = 0xfff0b0; fcaust.alpha = 0.3; fcaust.tileScale.set(1.3); cont.addChild(fcaust);
    // vật trang trí trên đáy (toạ độ thế giới)
    var decor = [];
    function addDecor(t, wx, scale, dy, ax) { var s = sprite(PIXI, t, ax === undefined ? 0.5 : ax, 1); s.scale.set(scale); cont.addChild(s); decor.push({ s: s, x: wx, dy: dy || 0, w: t.width * scale }); return s; }
    addDecor(T_wreck(PIXI), o.wreckX !== undefined ? o.wreckX : 0.56 * worldW, 1, 20);
    addDecor(T_log(PIXI), 0.17 * worldW, 1.25, 38);
    addDecor(T_jar(PIXI, 0), 0.74 * worldW, 1.15, 40);
    addDecor(T_jar(PIXI, 1), 0.74 * worldW + 150, 0.7, 36);
    addDecor(T_jar(PIXI, 0), 0.34 * worldW, 0.6, 30);
    addDecor(T_log(PIXI), 0.88 * worldW, 0.8, 34);

    var actors = new PIXI.Container(); actors.sortableChildren = true; cont.addChild(actors);

    // cây nước cao hai bên khung
    var edgeL = new PIXI.Sprite(T_edge(PIXI, 0)), edgeR = new PIXI.Sprite(T_edge(PIXI, 1));
    cont.addChild(edgeL, edgeR);
    var fore = tiling(T_fore(PIXI), 420, 1.35, 1.25);
    var hang2 = tiling(T_hang(PIXI, 1), 280, 1.1, 1.05, true); hang2.s.alpha = 0.6;
    L.push(fore, hang2);

    var parts = new PIXI.Container(); cont.addChild(parts);
    var pl = [];
    for (i = 0; i < 90; i++) {
      var isB = i < 26;
      var p = sprite(PIXI, isB ? T_bubble(PIXI) : T_soft(PIXI)), depthF = 0.5 + r() * 1.1;
      p.scale.set(isB ? 0.1 + r() * 0.22 : 0.04 + r() * 0.07 * depthF);
      p.alpha = isB ? 0.6 + r() * 0.4 : 0.25 + r() * 0.4;
      if (!isB) p.tint = 0xe6fff4;
      pl.push({ s: p, b: isB, x: r() * (W + 80), y: r() * (H + 80), f: depthF, sp: isB ? 20 + r() * 40 : 2 + r() * 6, ph: r() * TAU, am: 4 + r() * 12 });
      parts.addChild(p);
    }

    // thước độ sâu + vạch giới hạn lặn (tuỳ chọn)
    var ruler = new PIXI.Container(); ruler.visible = false; cont.addChild(ruler);
    var rulerG = new PIXI.Graphics(); ruler.addChild(rulerG);
    var rulerLbl = [], limitD = null;
    var rs = { fontFamily: 'Arial, sans-serif', fontSize: 12, fontWeight: '700', fill: 0xeafff8, stroke: 0x0a4a5a, strokeThickness: 3 };
    for (i = 0; i <= Math.floor(dMax / 5); i++) { var tl = new PIXI.Text(i * 5 + ' m', rs); tl.x = 30; tl.anchor.set(0, 0.5); ruler.addChild(tl); rulerLbl.push(tl); }
    var limText = new PIXI.Text('', { fontFamily: 'Arial, sans-serif', fontSize: 14, fontWeight: '700', fill: 0xffffff, stroke: 0x0a4a5a, strokeThickness: 3 }); limText.x = 110; limText.anchor.set(0, 1); ruler.addChild(limText);

    var dark = new PIXI.Sprite(PIXI.Texture.WHITE); dark.width = W; dark.height = H; dark.tint = 0x021a38; dark.alpha = 0; cont.addChild(dark);
    var vig = new PIXI.Sprite(T_vignette(PIXI)); vig.width = W; vig.height = H; vig.alpha = 0.7; cont.addChild(vig);

    var t = 0, curCamX = 0, curCamD = 0;
    var api = {
      container: root, actors: actors, width: W, height: H, surfaceY: surfaceY, floorY: floorY,
      pxPerDepth: pxD, pxPerX: pxX, maxCamDepthPx: maxCam,
      toScreenX: function (worldX) { return worldX - curCamX; },
      toScreenY: function (depthPx) { return surfaceY + depthPx - curCamD; },
      setRuler: function (on) { ruler.visible = !!on; return api; },
      setDepthLimit: function (depthUnits, label) { limitD = depthUnits; limText.text = label || ('Giới hạn mũ lặn: ' + depthUnits + ' m'); return api; },
      update: function (dt, camX, camDepthPx) {
        dt = Math.min(dt || 0, 0.1); t += dt;
        camX = curCamX = camX || 0; camDepthPx = curCamD = clamp(camDepthPx || 0, 0, maxCam);
        bg.y = surfaceY - camDepthPx;
        var df = clamp((camDepthPx + H * 0.5) / totalH, 0, 1);
        var tintC = mixC(0xffffff, 0x8fb8d8, clamp(df * 1.0, 0, 1));
        for (var i = 0; i < L.length; i++) {
          var l = L[i], sp = l.s;
          sp.tilePosition.x = -camX * l.fx + (l.hang ? Math.sin(t * 0.5 + i) * 9 : 0);
          sp.y = Math.round(l.hang ? surfaceY - camDepthPx * l.fy - 6 : H - l.h + (maxCam - camDepthPx) * l.fy);
          sp.tint = (l === fore || l === hang2) ? 0xffffff : l === floor ? mixC(0xffffff, 0xd8e8f0, df * 0.6) : tintC;
        }
        floor.s.y = Math.round(totalH - 320 - camDepthPx);
        for (i = 0; i < decor.length; i++) { var d = decor[i], sx2 = d.x - camX; d.s.visible = sx2 > -d.w && sx2 < W + d.w; d.s.x = sx2; d.s.y = floorY + d.dy - camDepthPx; }
        fcaust.y = Math.round(floor.s.y + 40); fcaust.tilePosition.set(-camX + Math.sin(t * 0.6) * 30, t * 14); fcaust.visible = fcaust.y < H;
        cTop.y = Math.round(surfaceY - camDepthPx); cTop.alpha = clamp(0.55 - camDepthPx / 1000, 0, 0.55); cTop.visible = cTop.alpha > 0.01;
        cTop.tilePosition.set(-camX * 0.9 + t * 18, 0);
        // cây hai bên: cố định theo khung, bám đáy
        var eY = H - 900 + (maxCam - camDepthPx) * 0.55;
        edgeL.x = 0 - camX * 0.04; edgeR.x = W - 340 + camX * 0.04; edgeL.y = edgeR.y = eY;
        rays.y = surfaceY - camDepthPx; rays.alpha = clamp(1 - camDepthPx / 900, 0, 1); rays.visible = rays.alpha > 0.01;
        if (rays.visible) for (i = 0; i < rayList.length; i++) {
          var ry = rayList[i];
          ry.s.x = ry.x + Math.sin(t * ry.sp + ry.ph) * 40 - camX * 0.1;
          ry.s.rotation = ry.rot + Math.sin(t * 0.3 + ry.ph) * 0.05;
          ry.s.alpha = ry.a * (0.7 + 0.3 * Math.sin(t * 0.8 + ry.ph * 2));
        }
        for (i = 0; i < fishes.length; i++) {
          var fi = fishes[i], span = W + 700, base = (fi.g + 1) * 0.3;
          var wx = mod(fi.ph * 400 + t * fi.sp * (fi.g % 2 ? -1 : 1) - camX * base, span) - 350;
          fi.s.x = wx + fi.ox; fi.s.y = fi.y + fi.oy + Math.sin(t * 1.3 + fi.ph) * 6 - camDepthPx * (0.38 + fi.g * 0.12);
          fi.s.scale.x = Math.abs(fi.s.scale.x) * (fi.g % 2 ? -1 : 1);
        }
        for (i = 0; i < pl.length; i++) {
          var q = pl[i], yy = q.b ? mod(q.y - t * q.sp - camDepthPx * q.f, H + 80) - 40 : mod(q.y + t * q.sp * 0.4 - camDepthPx * q.f, H + 80) - 40;
          q.s.x = mod(q.x - camX * q.f * 0.9, W + 80) - 40 + Math.sin(t * 0.7 + q.ph) * q.am; q.s.y = yy;
        }
        dark.alpha = clamp(df - 0.5, 0, 1) * 0.3;
        if (ruler.visible) {
          rulerG.clear(); rulerG.lineStyle(2, 0xeafff8, 0.7);
          for (i = 0; i < rulerLbl.length; i++) { var yy2 = surfaceY + i * 5 * pxD - camDepthPx, on = yy2 > 6 && yy2 < H - 6; rulerLbl[i].visible = on; if (on) { rulerLbl[i].y = yy2; rulerG.moveTo(6, yy2).lineTo(24, yy2); } }
          for (var m = 0; m <= dMax; m++) { var ym = surfaceY + m * pxD - camDepthPx; if (m % 5 && ym > 0 && ym < H) { rulerG.moveTo(6, ym).lineTo(14, ym); } }
          limText.visible = limitD !== null;
          if (limitD !== null) {
            var ly = surfaceY + limitD * pxD - camDepthPx; limText.visible = ly > 10 && ly < H + 20; limText.y = ly - 4;
            rulerG.lineStyle(2, 0xffffff, 0.75); for (var dx = 0; dx < W; dx += 22) rulerG.moveTo(dx, ly).lineTo(dx + 11, ly);
          }
        }
      },
      destroy: function () { root.destroy({ children: true }); }
    };
    api.update(0, 0, 0);
    return api;
  }

  /* ============================================================
   * Surface: bầu trời, rặng dừa nước, Chợ Nổi (xuồng hàng hóa, lồng đèn), bến, sóng
   * ============================================================ */
  function T_sky(PIXI, h) {
    return tex(PIXI, 'sky' + h, function () {
      var c = cvs(4, h), x = c.getContext('2d'), g = x.createLinearGradient(0, 0, 0, h);
      g.addColorStop(0, '#6fb7e8'); g.addColorStop(0.55, '#c6e3f0'); g.addColorStop(0.85, '#ffe6bd'); g.addColorStop(1, '#ffd2a1');
      x.fillStyle = g; x.fillRect(0, 0, 4, h); return c;
    });
  }
  function palm(c, x, base, h, lean, r, dark, lite) {
    // thân cong
    var tx = x + lean, ty = base - h;
    c.strokeStyle = '#6a4a2a'; c.lineWidth = 7; c.lineCap = 'round';
    c.beginPath(); c.moveTo(x, base); c.quadraticCurveTo(x + lean * 0.1, base - h * 0.6, tx, ty); c.stroke();
    c.strokeStyle = 'rgba(40,24,10,0.4)'; c.lineWidth = 1.5;
    for (var k = 1; k < 8; k++) { var u = k / 8, px = lerp(x, tx, u * u), py = base - h * u; c.beginPath(); c.moveTo(px - 4, py); c.lineTo(px + 4, py - 2); c.stroke(); }
    // tàu lá
    for (var i = 0; i < 9; i++) {
      var a = -Math.PI * 0.95 + i * (Math.PI * 0.95 / 4) * 1.0, len = 62 + r() * 24;
      if (i > 8) break;
      var ang = -Math.PI + (i + 0.5) / 9 * Math.PI, ex = tx + Math.cos(ang) * len, ey = ty + Math.sin(ang) * len * 0.55 + len * 0.45;
      var mx = tx + Math.cos(ang) * len * 0.55, my = ty + Math.sin(ang) * len * 0.8 - 10;
      var g = c.createLinearGradient(tx, ty, ex, ey); g.addColorStop(0, lite); g.addColorStop(1, dark);
      c.strokeStyle = g; c.lineWidth = 3; c.beginPath(); c.moveTo(tx, ty); c.quadraticCurveTo(mx, my, ex, ey); c.stroke();
      c.lineWidth = 1.6;
      for (var j = 1; j < 9; j++) { var u2 = j / 9, qx = (1 - u2) * (1 - u2) * tx + 2 * (1 - u2) * u2 * mx + u2 * u2 * ex, qy = (1 - u2) * (1 - u2) * ty + 2 * (1 - u2) * u2 * my + u2 * u2 * ey;
        c.beginPath(); c.moveTo(qx, qy); c.lineTo(qx - 4, qy + 14 - u2 * 5); c.moveTo(qx, qy); c.lineTo(qx + 4, qy + 14 - u2 * 5); c.stroke(); }
    }
    c.fillStyle = '#5a3a1a'; c.beginPath(); c.arc(tx - 3, ty + 6, 4.5, 0, TAU); c.arc(tx + 4, ty + 7, 4.5, 0, TAU); c.fill();
  }
  function stiltHouse(c, x, base, w, r) {
    var h = 34 + r() * 14, y = base - 26 - h;
    c.fillStyle = '#4a3420'; for (var i = 0; i <= 3; i++) c.fillRect(x - w / 2 + i * (w - 5) / 3, base - 26, 5, 30);
    c.fillStyle = '#7a5230'; c.fillRect(x - w / 2 - 4, base - 28, w + 8, 5);
    var g = c.createLinearGradient(0, y, 0, y + h); g.addColorStop(0, '#b88a56'); g.addColorStop(1, '#8a5e36');
    c.fillStyle = g; c.fillRect(x - w / 2, y, w, h);
    c.strokeStyle = 'rgba(60,34,14,0.5)'; c.lineWidth = 1; for (i = 1; i < 6; i++) { c.beginPath(); c.moveTo(x - w / 2 + i * w / 6, y); c.lineTo(x - w / 2 + i * w / 6, y + h); c.stroke(); }
    c.fillStyle = '#ffd27a'; c.fillRect(x - 8, y + 10, 16, 14); c.strokeStyle = '#5a3a1a'; c.lineWidth = 2; c.strokeRect(x - 8, y + 10, 16, 14);
    var rg = c.createLinearGradient(0, y - 30, 0, y); rg.addColorStop(0, '#e8c46a'); rg.addColorStop(1, '#a8803a');
    c.fillStyle = rg; c.beginPath(); c.moveTo(x - w / 2 - 12, y + 4); c.lineTo(x - 6, y - 32); c.lineTo(x + 6, y - 32); c.lineTo(x + w / 2 + 12, y + 4); c.closePath(); c.fill();
    c.strokeStyle = 'rgba(100,70,20,0.6)'; c.lineWidth = 1.2; for (i = -3; i <= 3; i++) { c.beginPath(); c.moveTo(x + i * 4, y - 32); c.lineTo(x + i * 12, y + 4); c.stroke(); }
  }
  function T_trees(PIXI) {
    return tex(PIXI, 'trees', function () {
      var W = 2048, H = 200, c0 = cvs(W, H), c = c0.getContext('2d'), r = rng(77), i;
      // đồi cây xa
      c.fillStyle = '#7ab59a';
      for (i = 0; i < 34; i++) { (function () { var x = r() * W, h = 30 + r() * 50, w = 50 + r() * 80;
        wrapAt(x, W, function (xx) { c.beginPath(); c.ellipse(xx, H, w, h, 0, Math.PI, 0); c.fill(); }); })(); }
      c.fillStyle = '#4a9a6c';
      for (i = 0; i < 22; i++) { (function () { var x = r() * W, h = 24 + r() * 40, w = 36 + r() * 60;
        wrapAt(x, W, function (xx) { c.beginPath(); c.ellipse(xx, H, w, h, 0, Math.PI, 0); c.fill(); }); })(); }
      var hx = [140, 560, 980, 1390, 1760];
      for (i = 0; i < hx.length; i++) { (function (x, w) { wrapAt(x, W, function (xx) { stiltHouse(c, xx, H - 6, w, r); }); })(hx[i], 44 + (i % 2) * 14); }
      for (i = 0; i < 10; i++) { (function () { var x = 20 + r() * (W - 40), h = 90 + r() * 70, ln = (r() - 0.5) * 60;
        wrapAt(x, W, function (xx) { palm(c, xx, H - 4, h, ln, r, '#2f7a3a', '#6ac048'); }); })(); }
      // lục bình/súng sát mặt nước
      c.fillStyle = '#3a8a3a'; for (i = 0; i < 70; i++) { var lx = r() * W; c.beginPath(); c.ellipse(lx, H - 5, 12 + r() * 14, 4 + r() * 3, 0, 0, TAU); c.fill(); }
      c.fillStyle = '#2f7a4a'; c.fillRect(0, H - 8, W, 8);
      return c0;
    }, true);
  }
  function T_cloud(PIXI) {
    return tex(PIXI, 'cloud', function () {
      var c = cvs(256, 80), x = c.getContext('2d'), r = rng(3);
      for (var i = 0; i < 12; i++) {
        var px = 40 + r() * 176, py = 40 + (r() - 0.5) * 18, rad = 20 + r() * 20;
        var g = x.createRadialGradient(px, py, 0, px, py, rad);
        g.addColorStop(0, 'rgba(255,255,255,0.95)'); g.addColorStop(1, 'rgba(255,255,255,0)');
        x.fillStyle = g; x.fillRect(0, 0, 256, 80);
      }
      return c;
    });
  }

  function lantern(PIXI, color) {
    var c = new PIXI.Container(), g = new PIXI.Graphics();
    g.lineStyle(1.5, 0x3a2410).moveTo(0, -12).lineTo(0, -6);
    g.lineStyle(0).beginFill(0x4a2d14).drawRect(-4, -7, 8, 3).drawRect(-4, 8, 8, 3).endFill();
    g.beginFill(color).drawEllipse(0, 1, 7, 8.5).endFill();
    g.beginFill(0xffffff, 0.3).drawEllipse(-2.5, -1.5, 2, 4).endFill();
    g.lineStyle(1, 0x8a1f10, 0.7).moveTo(-7, 1).quadraticCurveTo(0, -3, 7, 1).moveTo(-6, 5).quadraticCurveTo(0, 8, 6, 5);
    c.addChild(g);
    var glow = add(PIXI, sprite(PIXI, T_soft(PIXI))); glow.tint = 0xffb050; glow.scale.set(1.5); glow.alpha = 0.55; glow.y = 1; c.addChild(glow);
    c.glow = glow; c.tf = 0;
    return c;
  }
  function fruit(PIXI, kind, r) {
    var g = new PIXI.Graphics();
    if (kind === 0) { // dứa
      g.beginFill(0xe8b422).drawEllipse(0, 0, 9, 12).endFill();
      g.lineStyle(1, 0xa8741a, 0.7); for (var i = -2; i <= 2; i++) g.moveTo(i * 3.5, -10).lineTo(i * 3.5 + 3, 9);
      g.lineStyle(0).beginFill(0x3f9a3e); for (i = -2; i <= 2; i++) g.drawPolygon([0, -10, i * 6 - 3, -22 + Math.abs(i) * 3, i * 6 + 2, -12]); g.endFill();
    } else if (kind === 1) { // dưa hấu
      g.beginFill(0x2f8a3c).drawCircle(0, 0, 12).endFill();
      g.lineStyle(2, 0x1b5e28); g.arc(0, 0, 8, 0.5, 2.6); g.arc(0, 0, 8, 3.6, 5.5);
      g.lineStyle(0).beginFill(0xffffff, 0.2).drawEllipse(-4, -5, 4, 2).endFill();
    } else if (kind === 2) { // chuối
      g.lineStyle(5, 0xf2cc2f, 1, 0.5).moveTo(-9, -8).quadraticCurveTo(10, -2, 4, 12);
      g.lineStyle(5, 0xe6bd26, 1, 0.5).moveTo(-5, -8).quadraticCurveTo(14, 0, 9, 13);
      g.lineStyle(3, 0x6a7a2a).moveTo(-9, -9).lineTo(-6, -14);
    } else { // bí / cà
      g.beginFill(0xe0782a).drawEllipse(0, 0, 11, 9).endFill(); g.lineStyle(1.2, 0xa8501a, 0.8); g.moveTo(-4, -8).quadraticCurveTo(-7, 0, -4, 8); g.moveTo(4, -8).quadraticCurveTo(7, 0, 4, 8);
      g.lineStyle(0).beginFill(0x4a7a2a).drawRect(-1.5, -12, 3, 5).endFill();
    }
    return g;
  }
  function boat(PIXI, kind, r, scale) {
    var c = new PIXI.Container(), g = new PIXI.Graphics();
    var hullCol = [0x7a4a28, 0x2f6d8f, 0x9a3a2a, 0x3d7a4f][Math.floor(r() * 4)];
    var rim = mixC(hullCol, 0xffffff, 0.35), dk = mixC(hullCol, 0x000000, 0.4);
    var len = kind === 'goods' ? 128 : 110;
    // thân xuồng
    g.beginFill(dk).moveTo(-len, -20).bezierCurveTo(-len * 0.8, 16, -len * 0.3, 22, 0, 22).bezierCurveTo(len * 0.4, 22, len * 0.9, 12, len + 18, -26)
      .lineTo(len - 2, -22).bezierCurveTo(len * 0.7, -8, len * 0.3, -4, 0, -4).bezierCurveTo(-len * 0.4, -4, -len * 0.8, -10, -len, -20).endFill();
    g.beginFill(hullCol).moveTo(-len, -20).bezierCurveTo(-len * 0.8, 10, -len * 0.3, 14, 0, 14).bezierCurveTo(len * 0.4, 14, len * 0.9, 6, len + 18, -26)
      .lineTo(len + 10, -28).bezierCurveTo(len * 0.8, -6, len * 0.4, 0, 0, 0).bezierCurveTo(-len * 0.4, 0, -len * 0.8, -8, -len - 6, -24).endFill();
    g.lineStyle(3, rim).moveTo(-len - 6, -24).bezierCurveTo(-len * 0.8, -8, -len * 0.4, 0, 0, 0).bezierCurveTo(len * 0.4, 0, len * 0.8, -6, len + 10, -28);
    g.lineStyle(2, 0xf3d9a0, 0.8).moveTo(-len + 10, -4).bezierCurveTo(-len * 0.4, 8, len * 0.4, 8, len - 6, -8);
    c.addChild(g);
    // mắt thuyền
    var eye = new PIXI.Graphics().beginFill(0xffffff).drawCircle(len - 10, -8, 5).endFill().beginFill(0x111111).drawCircle(len - 8, -8, 2.5).endFill();
    c.addChild(eye);
    var cargo = new PIXI.Container(); c.addChild(cargo);
    var swing = [];
    if (kind === 'goods') {
      // cây bẹo: cột cao treo hàng của thuyền
      var pole = new PIXI.Graphics().lineStyle(5, 0x6a4a28).moveTo(-20, -4).lineTo(-20, -190).lineStyle(3, 0x6a4a28).moveTo(-20, -190).lineTo(26, -190);
      cargo.addChild(pole);
      var flag = new PIXI.Graphics().beginFill(0xe23b2e).drawPolygon([-18, -188, -18, -170, -44, -179]).endFill(); cargo.addChild(flag); swing.push({ o: flag, a: 0.05 });
      for (var i = 0; i < 4; i++) {
        var hx = -20 + i * 15 - (i > 1 ? 0 : 0), hy = -184 + (i % 2) * 6;
        var s = new PIXI.Container(); s.x = hx; s.y = hy; s.pivot.set(0, 0);
        var str = new PIXI.Graphics().lineStyle(1.3, 0x4a3a2a).moveTo(0, 0).lineTo(0, 24 + (i % 3) * 14); s.addChild(str);
        var fr = fruit(PIXI, i % 4, r); fr.y = 36 + (i % 3) * 14; s.addChild(fr);
        cargo.addChild(s); swing.push({ o: s, a: 0.08 });
      }
      // chất hàng trên thân xuồng
      for (i = 0; i < 12; i++) { var f = fruit(PIXI, Math.floor(r() * 4), r); f.x = -90 + i * 12 + (r() - 0.5) * 6; f.y = -14 - (i % 3) * 8 - r() * 4; f.scale.set(0.9); cargo.addChild(f); }
    } else if (kind === 'food') {
      var canopy = new PIXI.Graphics().beginFill(0xd8b25a).drawPolygon([-80, -34, -60, -78, 60, -78, 80, -34]).endFill()
        .lineStyle(2, 0x8a6a2a, 0.8);
      for (i = -3; i <= 3; i++) canopy.moveTo(i * 20, -78).lineTo(i * 24, -34);
      cargo.addChild(canopy);
      var pots = new PIXI.Graphics().beginFill(0x2a2a30).drawRoundedRect(-40, -34, 36, 14, 4).endFill().beginFill(0xb8a898).drawEllipse(-22, -34, 17, 4).endFill()
        .beginFill(0xc43a20).drawRoundedRect(8, -32, 30, 12, 4).endFill();
      cargo.addChild(pots);
      var lt = lantern(PIXI, 0xe8352a); lt.x = -62; lt.y = -34; cargo.addChild(lt); swing.push({ o: lt, a: 0.1, lantern: true, y: -34 });
      var lt2 = lantern(PIXI, 0xf0a020); lt2.x = 60; lt2.y = -34; cargo.addChild(lt2); swing.push({ o: lt2, a: 0.1, lantern: true });
      c.steam = [];
      for (i = 0; i < 4; i++) { var st = add(PIXI, sprite(PIXI, T_puff(PIXI))); st.tint = 0xffffff; st.x = -22; st.y = -40; st.scale.set(0.3); st.alpha = 0; cargo.addChild(st); c.steam.push({ s: st, ph: i / 4 }); }
    } else { // xuồng nhỏ chở hoa/đèn
      for (i = 0; i < 6; i++) { var fl = new PIXI.Graphics().beginFill([0xff6fa0, 0xffd23a, 0xffffff, 0xff8a3a][i % 4]).drawCircle(0, 0, 8).endFill().beginFill(0xffe7a0).drawCircle(0, 0, 2.5).endFill();
        fl.x = -50 + i * 20; fl.y = -18 - (i % 2) * 7; cargo.addChild(fl); }
      var lt3 = lantern(PIXI, 0xff5a3a); lt3.x = len - 30; lt3.y = -48;
      var post = new PIXI.Graphics().lineStyle(3, 0x6a4a28).moveTo(len - 30, -4).lineTo(len - 30, -56); cargo.addChild(post); cargo.addChild(lt3); swing.push({ o: lt3, a: 0.1, lantern: true });
    }
    c.swing = swing; c.scale.set(scale || 1);
    return c;
  }

  function createSurface(PIXI, o) {
    o = o || {};
    var W = o.width || DEF.width, H = o.height || DEF.height;
    var surfaceY = o.surfaceY !== undefined ? o.surfaceY : DEF.surfaceY;
    var pxX = o.pxPerX || DEF.pxPerX, worldW = o.worldWidth || DEF.worldX * pxX + 200;
    var dockX = o.dockX !== undefined ? o.dockX : 2 * pxX;
    var r = rng(o.seed || 9);
    var root = new PIXI.Container();
    var skyLayer = new PIXI.Container(); root.addChild(skyLayer);
    var sky = new PIXI.Sprite(T_sky(PIXI, surfaceY + 10)); sky.width = W; sky.height = surfaceY + 10; sky.y = -300; sky.height = surfaceY + 310;
    // kéo gradient đến mép trên (phần dư để khi camera đi lên vẫn còn trời)
    skyLayer.addChild(sky);
    var sun = add(PIXI, sprite(PIXI, T_soft(PIXI))); sun.tint = 0xffe2a0; sun.x = W * 0.8; sun.y = surfaceY - 120; sun.scale.set(5); sun.alpha = 0.8; skyLayer.addChild(sun);
    var sun2 = sprite(PIXI, T_soft(PIXI)); sun2.tint = 0xfffbe8; sun2.x = sun.x; sun2.y = sun.y; sun2.scale.set(1.3); skyLayer.addChild(sun2);
    var clouds = [];
    for (var i = 0; i < 5; i++) { var cl = sprite(PIXI, T_cloud(PIXI)); cl.alpha = 0.55 + r() * 0.3; cl.scale.set(1 + r() * 1.2, 1 + r() * 0.6); cl.y = 20 + r() * (surfaceY - 100);
      clouds.push({ s: cl, x: r() * W, sp: 6 + r() * 8 }); skyLayer.addChild(cl); }
    var trees = new PIXI.TilingSprite(T_trees(PIXI), W, 200); trees.y = surfaceY - 200 + 6; skyLayer.addChild(trees);

    var world = new PIXI.Container(); root.addChild(world);
    // dock (bến)
    var dock = new PIXI.Container(); world.addChild(dock);
    var dg = new PIXI.Graphics();
    var dx0 = dockX - 50, dx1 = dockX + 240, dy = surfaceY - 30;
    for (i = 0; i < 6; i++) { var px = dx0 + 12 + i * 52; dg.beginFill(0x4a3220).drawRect(px - 6, dy, 12, 80).endFill(); dg.beginFill(0x6a4a30).drawRect(px - 6, dy, 4, 80).endFill(); }
    dg.beginFill(0x5d3f26).drawRect(dx0, dy - 8, dx1 - dx0, 14).endFill();
    for (i = 0; i < 24; i++) { var bx = dx0 + i * ((dx1 - dx0) / 24); dg.beginFill(i % 2 ? 0x9a6c3e : 0x8a5c32).drawRect(bx + 1, dy - 14, (dx1 - dx0) / 24 - 2, 8).endFill(); }
    dg.beginFill(0xb88556, 0.7).drawRect(dx0, dy - 14, dx1 - dx0, 2).endFill();
    dg.lineStyle(2, 0xd8c8a0, 0.9).moveTo(dx0 + 20, dy - 14).bezierCurveTo(dx0 + 80, dy + 20, dx0 + 140, dy + 20, dx0 + 190, dy - 14);
    dock.addChild(dg);
    // cột đèn + biển
    var lp = new PIXI.Graphics().lineStyle(5, 0x4a3220).moveTo(dx1 - 14, dy - 12).lineTo(dx1 - 14, dy - 110).lineTo(dx1 - 44, dy - 110);
    dock.addChild(lp);
    var dl = lantern(PIXI, 0xe8352a); dl.x = dx1 - 44; dl.y = dy - 100; dock.addChild(dl);
    var sign = new PIXI.Graphics().beginFill(0x5a3a1e).drawRoundedRect(dx0 + 6, dy - 108, 100, 34, 5).endFill().lineStyle(2, 0xf0c060).drawRoundedRect(dx0 + 9, dy - 105, 94, 28, 4);
    dock.addChild(sign);
    var stxt = new PIXI.Text('BẾN CHỢ', { fontFamily: 'Arial, sans-serif', fontSize: 17, fontWeight: '700', fill: 0xffe08a });
    stxt.anchor.set(0.5); stxt.x = dx0 + 56; stxt.y = dy - 91; dock.addChild(stxt);
    var poles = new PIXI.Graphics().lineStyle(4, 0x4a3220).moveTo(dx0 + 6, dy - 12).lineTo(dx0 + 6, dy - 80);
    dock.addChild(poles);
    var boxes = new PIXI.Graphics().beginFill(0x8a5c32).drawRect(dx0 + 130, dy - 40, 40, 26).endFill().lineStyle(2, 0x5a3a1e).drawRect(dx0 + 130, dy - 40, 40, 26).moveTo(dx0 + 130, dy - 27).lineTo(dx0 + 170, dy - 27);
    dock.addChild(boxes);

    // thuyền Chợ Nổi
    var boats = [];
    var kinds = ['goods', 'food', 'flower', 'goods', 'food', 'goods', 'flower'];
    var x = dockX + 420;
    for (i = 0; x < worldW + 200; i++) {
      var k = kinds[i % kinds.length], b = boat(PIXI, k, r, 0.9 + r() * 0.35);
      b.x = x; b.y = surfaceY + 6; if (r() < 0.5) b.scale.x *= -1;
      b.bob = { ph: r() * TAU, sp: 0.8 + r() * 0.5, am: 2 + r() * 2 };
      world.addChild(b); boats.push(b);
      x += 300 + r() * 160;
    }
    var actors = new PIXI.Container(); world.addChild(actors);

    // sóng trước mặt
    var front = new PIXI.Container(); root.addChild(front);
    var waveG = new PIXI.Graphics(); front.addChild(waveG);
    var glints = [];
    for (i = 0; i < 12; i++) { var gl = add(PIXI, sprite(PIXI, T_soft(PIXI))); gl.tint = 0xfff0c8; gl.scale.set(0.5 + r() * 0.4, 0.1); gl.alpha = 0; glints.push({ s: gl, x: r() * W, ph: r() * TAU }); front.addChild(gl); }

    var t = 0, camXc = 0;
    var api = {
      container: root, actors: actors, front: front, width: W, surfaceY: surfaceY, dockX: dockX,
      update: function (dt, camX, camDepthPx) {
        dt = Math.min(dt || 0, 0.1); t += dt; camX = camXc = camX || 0; camDepthPx = camDepthPx || 0;
        root.y = -camDepthPx; root.visible = camDepthPx < surfaceY + 120;
        if (!root.visible) return;
        world.x = -camX;
        trees.tilePosition.x = -camX * 0.12;
        for (var i = 0; i < clouds.length; i++) { var c = clouds[i]; c.s.x = mod(c.x + t * c.sp - camX * 0.04, W + 300) - 150; }
        for (i = 0; i < boats.length; i++) {
          var b = boats[i]; b.visible = b.x - camX > -260 && b.x - camX < W + 260;
          if (!b.visible) continue;
          b.y = surfaceY + 6 + Math.sin(t * b.bob.sp + b.bob.ph) * b.bob.am; b.rotation = Math.sin(t * b.bob.sp * 0.8 + b.bob.ph) * 0.03;
          for (var k = 0; k < b.swing.length; k++) { var s = b.swing[k]; s.o.rotation = Math.sin(t * 1.4 + k + b.bob.ph) * s.a; if (s.lantern) s.o.glow.alpha = 0.45 + 0.15 * Math.sin(t * 7 + k * 3 + b.bob.ph); }
          if (b.steam) for (k = 0; k < b.steam.length; k++) { var st = b.steam[k], p = mod(t * 0.35 + st.ph, 1); st.s.y = -40 - p * 55; st.s.x = -22 + Math.sin(p * 6 + k) * 8; st.s.scale.set(0.25 + p * 0.5); st.s.alpha = (1 - p) * 0.35; }
        }
        dl.glow.alpha = 0.5 + 0.15 * Math.sin(t * 6); dl.rotation = Math.sin(t * 1.5) * 0.06;
        // mặt nước: dải sóng trước + viền sáng
        waveG.clear();
        var pts = [], step = 16, ph = camX * 0.9;
        for (var xx = -step; xx <= W + step; xx += step) {
          var a = xx + ph;
          pts.push(xx, surfaceY - 3 - (Math.sin(a * 0.02 + t * 1.6) * 2.2 + Math.sin(a * 0.047 - t * 2.3) * 1.4 + 2.2));
        }
        waveG.beginFill(0x58d0c4, 1); waveG.moveTo(-step, surfaceY + 3);
        for (i = 0; i < pts.length; i += 2) waveG.lineTo(pts[i], pts[i + 1]);
        waveG.lineTo(W + step, surfaceY + 3); waveG.closePath(); waveG.endFill();
        waveG.lineStyle(2, 0xeafffa, 0.85); waveG.moveTo(pts[0], pts[1]);
        for (i = 2; i < pts.length; i += 2) waveG.lineTo(pts[i], pts[i + 1]);
        waveG.lineStyle(0);
        waveG.beginFill(0x2fa8aa, 0.28).drawRect(0, surfaceY + 3, W, 26).endFill();
        waveG.beginFill(0x2fa8aa, 0.18).drawRect(0, surfaceY + 29, W, 34).endFill();
        for (i = 0; i < glints.length; i++) { var gl = glints[i]; gl.s.x = mod(gl.x - camX * 0.9, W); gl.s.y = surfaceY + 6 + (i % 4) * 5; gl.s.alpha = Math.max(0, Math.sin(t * 1.5 + gl.ph)) * 0.7; }
      },
      destroy: function () { root.destroy({ children: true }); }
    };
    api.update(0, 0, 0);
    return api;
  }

  /* ============================================================
   * Cá
   * ============================================================ */
  var FISH = {
    ca_linh: { L: 36, H: 11, back: 0x8fa6b4, belly: 0xf2f7fa, fin: 0xcfe0e8, stripe: 0x4a5e6c, stripeW: 1.6, tail: 'fork', tl: 10, th: 8, eye: 2.4, shine: true },
    ca_loc: { L: 100, H: 22, back: 0x3a4a2a, belly: 0xb8b084, fin: 0x4a5a30, stripe: 0x1c2412, tail: 'round', tl: 16, th: 11, eye: 3, blotch: true, longDorsal: true, flat: true },
    ca_keo: { L: 66, H: 22, back: 0x8a7a5a, belly: 0xe0d0a0, fin: 0xe08a2a, stripe: 0x4a3a22, tail: 'round', tl: 14, th: 12, eye: 3.4, spots: true, sail: true, topEyes: true }
  };
  function createFish(PIXI, kind) {
    var P = FISH[kind] || { L: 54, H: 18, back: 0x6a8a9a, belly: 0xe8e8d8, fin: 0xa0b8c0, stripe: 0x344a58, tail: 'fork', tl: 12, th: 10, eye: 3 };
    var root = new PIXI.Container(), body = new PIXI.Container(), flip = new PIXI.Container();
    root.addChild(flip); flip.addChild(body);
    var L = P.L, Hh = P.H, nx = L / 2, tx = -L * 0.42;
    // đuôi (xoay quanh gốc đuôi)
    var tail = new PIXI.Container(); tail.x = tx; body.addChild(tail);
    var tg = new PIXI.Graphics();
    tg.beginFill(P.fin, 0.95);
    if (P.tail === 'fork') tg.moveTo(0, 0).bezierCurveTo(-P.tl * 0.5, -P.th * 0.3, -P.tl, -P.th, -P.tl * 1.15, -P.th * 1.05).quadraticCurveTo(-P.tl * 0.6, 0, -P.tl * 1.15, P.th * 1.05).bezierCurveTo(-P.tl, P.th, -P.tl * 0.5, P.th * 0.3, 0, 0);
    else tg.moveTo(0, -Hh * 0.12).bezierCurveTo(-P.tl * 0.6, -P.th * 1.2, -P.tl * 1.3, -P.th * 0.8, -P.tl * 1.3, 0).bezierCurveTo(-P.tl * 1.3, P.th * 0.8, -P.tl * 0.6, P.th * 1.2, 0, Hh * 0.12);
    tg.endFill();
    tg.lineStyle(1, mixC(P.fin, 0x000000, 0.35), 0.55); for (var i = -2; i <= 2; i++) tg.moveTo(0, 0).lineTo(-P.tl * 1.05, i * P.th * 0.33);
    tail.addChild(tg);
    // vây lưng
    var dorsal = new PIXI.Graphics();
    dorsal.beginFill(P.fin, 0.9);
    if (P.sail) dorsal.moveTo(L * 0.2, -Hh * 0.45).bezierCurveTo(L * 0.1, -Hh * 1.3, -L * 0.12, -Hh * 1.4, -L * 0.3, -Hh * 0.3).lineTo(L * 0.2, -Hh * 0.45);
    else if (P.longDorsal) dorsal.moveTo(L * 0.3, -Hh * 0.46).bezierCurveTo(L * 0.2, -Hh * 0.9, -L * 0.2, -Hh * 0.85, -L * 0.4, -Hh * 0.2).lineTo(L * 0.3, -Hh * 0.46);
    else dorsal.moveTo(L * 0.12, -Hh * 0.5).lineTo(-L * 0.05, -Hh * 0.95).lineTo(-L * 0.18, -Hh * 0.38);
    dorsal.endFill(); body.addChild(dorsal);
    // thân
    var g = new PIXI.Graphics();
    function bodyPath(scaleBelly) {
      g.moveTo(nx, 0).bezierCurveTo(nx * 0.65, -Hh * 0.62, -L * 0.1, -Hh * 0.58, tx, -Hh * 0.13).lineTo(tx, Hh * 0.13)
        .bezierCurveTo(-L * 0.1, Hh * 0.58 * scaleBelly, nx * 0.65, Hh * 0.62 * scaleBelly, nx, 0);
    }
    g.beginFill(P.back); bodyPath(1); g.endFill();
    // bụng sáng
    g.beginFill(P.belly, 0.95).moveTo(nx - 1, 1).bezierCurveTo(nx * 0.6, Hh * 0.1, -L * 0.1, Hh * 0.05, tx, Hh * 0.05).lineTo(tx, Hh * 0.13)
      .bezierCurveTo(-L * 0.1, Hh * 0.58, nx * 0.65, Hh * 0.62, nx - 1, 1).endFill();
    if (P.stripe && !P.spots) g.lineStyle(P.stripeW || 2.2, P.stripe, 0.6).moveTo(nx * 0.6, -Hh * 0.05).bezierCurveTo(nx * 0.2, -Hh * 0.08, -L * 0.2, -Hh * 0.04, tx, -Hh * 0.02);
    if (P.blotch) { g.lineStyle(0); for (i = 0; i < 7; i++) g.beginFill(P.stripe, 0.55).drawEllipse(nx * 0.45 - i * L * 0.12, -Hh * 0.15 + (i % 2) * Hh * 0.12, L * 0.05, Hh * 0.13).endFill(); }
    if (P.spots) { g.lineStyle(0); for (i = 0; i < 9; i++) g.beginFill(P.stripe, 0.7).drawCircle(nx * 0.4 - i * L * 0.09, -Hh * 0.2 + ((i * 7) % 5) * Hh * 0.08, 1.6).endFill(); }
    if (P.shine) { g.lineStyle(0).beginFill(0xffffff, 0.55).drawEllipse(L * 0.05, -Hh * 0.25, L * 0.22, Hh * 0.08).endFill(); }
    g.lineStyle(1, 0x000000, 0.22); bodyPath(1);
    body.addChild(g);
    // vây ngực
    var pec = new PIXI.Container(); pec.x = nx * 0.35; pec.y = Hh * 0.18; body.addChild(pec);
    pec.addChild(new PIXI.Graphics().beginFill(P.fin, 0.85).moveTo(0, 0).quadraticCurveTo(-L * 0.14, Hh * 0.15, -L * 0.18, Hh * 0.38).quadraticCurveTo(-L * 0.04, Hh * 0.26, 0, 0).endFill());
    // đầu: mắt, mang
    var eg = new PIXI.Graphics();
    var ex = nx * 0.62, ey = P.topEyes ? -Hh * 0.38 : -Hh * 0.1;
    eg.beginFill(0xffffff).drawCircle(ex, ey, P.eye).endFill().beginFill(0x10151a).drawCircle(ex + 0.5, ey, P.eye * 0.62).endFill().beginFill(0xffffff, 0.9).drawCircle(ex + P.eye * 0.2, ey - P.eye * 0.25, P.eye * 0.2).endFill();
    eg.lineStyle(1.2, 0x000000, 0.28).moveTo(nx * 0.38, -Hh * 0.3).quadraticCurveTo(nx * 0.3, 0, nx * 0.38, Hh * 0.3);
    eg.lineStyle(1.2, 0x000000, 0.3).moveTo(nx * 0.97, Hh * 0.04).lineTo(nx * 0.84, Hh * 0.08);
    body.addChild(eg);
    if (kind === 'ca_loc') { // đầu dẹt, miệng rộng
      var hd = new PIXI.Graphics().lineStyle(1.4, 0x10140a, 0.5).moveTo(nx * 0.98, Hh * 0.12).lineTo(nx * 0.55, Hh * 0.16);
      body.addChild(hd);
    }
    var cf = null; // flash
    var t = Math.random() * 10, speed = 1, facing = 1, curFace = 1, state = 'swim';
    var api = {
      container: root, kind: kind, width: L, height: Hh * 1.2,
      setFacing: function (dir) { facing = dir < 0 ? -1 : 1; return api; },
      setSpeed: function (v) { speed = clamp(v, 0, 4); return api; },
      setState: function (s) { state = s; return api; },
      flash: function (sec) { cf = { t: sec || 0.18, f: new PIXI.filters.ColorMatrixFilter() }; cf.f.brightness(2.4, false); body.filters = [cf.f]; return api; },
      update: function (dt) {
        dt = Math.min(dt || 0, 0.1); t += dt;
        curFace += (facing - curFace) * Math.min(1, dt * 12); flip.scale.x = curFace;
        var f = 5 + speed * 4.2, amp = 0.26 + 0.1 * Math.min(speed, 2);
        tail.rotation = Math.sin(t * f) * amp;
        body.rotation = Math.sin(t * f - 0.8) * 0.045 * (0.5 + speed * 0.5);
        body.y = Math.sin(t * 1.3) * 1.2;
        pec.rotation = Math.sin(t * f * 0.7) * 0.4 - 0.1;
        if (cf) { cf.t -= dt; if (cf.t <= 0) { body.filters = null; cf = null; } }
      },
      destroy: function () { root.destroy({ children: true }); }
    };
    api.update(0);
    return api;
  }

  /* ============================================================
   * Cá Sấu
   * ============================================================ */
  function createCrocodile(PIXI) {
    var root = new PIXI.Container(), flip = new PIXI.Container(), body = new PIXI.Container();
    root.addChild(flip); flip.addChild(body); body.scale.set(0.82);
    var warn = add(PIXI, sprite(PIXI, T_soft(PIXI))); warn.tint = 0xff2a1a; warn.width = 400; warn.height = 220; warn.alpha = 0; flip.addChild(warn);
    var C = { back: 0x4f6a2c, dark: 0x2f4219, belly: 0xc8c07a, scute: 0x3a5020 };
    // đuôi: 4 đốt móc xích
    var segs = [], parent = body, px = -62, sz = [[48, 17], [44, 13], [40, 9], [34, 5]];
    for (var i = 0; i < 4; i++) {
      var sc = new PIXI.Container(); sc.x = px; parent.addChild(sc);
      var w = sz[i][0], h = sz[i][1], h2 = i < 3 ? sz[i + 1][1] : 2;
      var sg = new PIXI.Graphics().beginFill(i % 2 ? C.back : mixC(C.back, 0x000000, 0.08)).moveTo(0, -h).lineTo(-w, -h2).lineTo(-w, h2 * 0.8).lineTo(0, h * 0.9).closePath().endFill();
      sg.beginFill(C.belly, 0.7).moveTo(0, h * 0.5).lineTo(-w, h2 * 0.4).lineTo(-w, h2 * 0.8).lineTo(0, h * 0.9).closePath().endFill();
      sg.beginFill(C.scute); for (var k = 0; k < 3; k++) sg.drawPolygon([-k * w / 3 - 2, -h + k * (h - h2) / 3 + 1, -k * w / 3 - 11, -h + k * (h - h2) / 3 - 9, -k * w / 3 - 18, -h + (k + 0.5) * (h - h2) / 3 + 1]);
      sg.endFill();
      sc.addChild(sg); segs.push(sc); parent = sc; px = -w;
    }
    // 4 chân (vẫy chèo)
    var legs = [];
    function leg(x, y, front) {
      var l = new PIXI.Container(); l.x = x; l.y = y;
      l.addChild(new PIXI.Graphics().beginFill(mixC(C.back, 0x000000, 0.25)).moveTo(-5, 0).lineTo(5, 0).lineTo(9, 22).lineTo(-3, 24).closePath().endFill()
        .beginFill(C.dark).drawPolygon([-3, 24, 9, 22, 16, 30, 8, 30, 5, 34, -2, 30]).endFill());
      body.addChild(l); legs.push({ o: l, ph: front ? 0 : Math.PI, front: front });
    }
    leg(-30, 14, false); leg(58, 14, false);
    // thân
    var bg = new PIXI.Graphics();
    bg.beginFill(C.back).moveTo(-64, -17).bezierCurveTo(-30, -34, 40, -34, 88, -22).lineTo(88, 12).bezierCurveTo(40, 22, -30, 22, -64, 16).closePath().endFill();
    bg.beginFill(C.belly, 0.85).moveTo(-62, 10).bezierCurveTo(-30, 18, 40, 18, 88, 8).lineTo(88, 14).bezierCurveTo(40, 24, -30, 24, -64, 17).closePath().endFill();
    bg.beginFill(mixC(C.back, 0xffffff, 0.12), 0.8).moveTo(-50, -20).bezierCurveTo(-10, -30, 40, -30, 80, -21).bezierCurveTo(40, -25, -10, -24, -50, -16).endFill();
    // sống lưng
    bg.beginFill(C.scute);
    for (i = 0; i < 12; i++) { var sx = -56 + i * 12, sy = -23 - Math.sin(i / 11 * Math.PI) * 9 - 1; bg.drawPolygon([sx - 5, sy + 3, sx, sy - 10, sx + 5, sy + 3]); }
    bg.endFill();
    bg.lineStyle(1.2, 0x1c2a0e, 0.5); for (i = 0; i < 10; i++) bg.moveTo(-52 + i * 13, -14).lineTo(-52 + i * 13 + 4, 6);
    body.addChild(bg);
    leg(-34, 16, true); leg(52, 16, true);
    legs[2].o.scale.set(1.05); legs[3].o.scale.set(1.05);
    // hàm dưới
    var jaw = new PIXI.Container(); jaw.x = 82; jaw.y = 2; body.addChild(jaw);
    var jg = new PIXI.Graphics().beginFill(mixC(C.back, 0x000000, 0.1)).moveTo(0, 0).lineTo(78, -2).quadraticCurveTo(96, 3, 92, 10).lineTo(0, 15).closePath().endFill()
      .beginFill(C.belly, 0.9).moveTo(0, 10).lineTo(92, 8).quadraticCurveTo(94, 11, 90, 12).lineTo(0, 16).closePath().endFill()
      .beginFill(0xf4f0dc);
    for (i = 0; i < 9; i++) jg.drawPolygon([8 + i * 9, -1, 12 + i * 9, -9, 16 + i * 9, -1]);
    jg.endFill(); jaw.addChild(jg);
    // đầu / hàm trên
    var hg = new PIXI.Graphics();
    hg.beginFill(C.back).moveTo(70, -26).bezierCurveTo(100, -24, 130, -20, 172, -14).quadraticCurveTo(184, -10, 178, -2).lineTo(86, 2).lineTo(70, 8).closePath().endFill();
    hg.beginFill(mixC(C.back, 0xffffff, 0.14), 0.7).moveTo(76, -24).bezierCurveTo(110, -24, 140, -18, 170, -13).lineTo(160, -10).bezierCurveTo(130, -14, 105, -18, 76, -18).endFill();
    hg.beginFill(0xf4f0dc); for (i = 0; i < 9; i++) hg.drawPolygon([96 + i * 8.5, -1.5, 100 + i * 8.5, 7, 104 + i * 8.5, -1.5]); hg.endFill();
    hg.beginFill(C.scute).drawEllipse(172, -16, 7, 4).endFill().beginFill(0x10180a).drawCircle(172, -17, 1.8).drawCircle(166, -15, 1.4).endFill();
    // mắt lồi
    hg.beginFill(C.back).drawEllipse(110, -29, 13, 9).endFill();
    body.addChild(hg);
    var eye = new PIXI.Graphics(); body.addChild(eye);
    var eyeGlow = add(PIXI, sprite(PIXI, T_soft(PIXI))); eyeGlow.tint = 0xff3a22; eyeGlow.x = 112; eyeGlow.y = -30; eyeGlow.scale.set(0.9); eyeGlow.alpha = 0; body.addChild(eyeGlow);
    function drawEye(mode) {
      eye.clear();
      if (mode === 'closed') { eye.lineStyle(2.4, 0x10180a).moveTo(103, -30).lineTo(120, -29); eye.moveTo(108, -33).lineTo(112, -26).moveTo(112, -33).lineTo(108, -26); return; }
      eye.beginFill(mode === 'chase' ? 0xff4a22 : 0xf2d23a).drawCircle(112, -30, 6.2).endFill();
      eye.beginFill(0x10180a).drawEllipse(112.8, -30, mode === 'chase' ? 1.6 : 1.9, 5.2).endFill();
      eye.beginFill(0xffffff, 0.7).drawCircle(110.5, -32.5, 1.2).endFill();
      if (mode === 'chase') eye.lineStyle(2.2, 0x10180a).moveTo(103, -37).lineTo(122, -32);
    }
    var t = 0, face = 1, curFace = 1, state = 'patrol', warnOn = false, warnV = 0, recT = 0, flashT = 0, fl = null;
    var api = {
      container: root, width: 260, height: 70, state: 'patrol',
      setFacing: function (dir) { face = dir < 0 ? -1 : 1; return api; },
      setState: function (s) {
        if (s !== 'patrol' && s !== 'chase' && s !== 'recoil') s = 'patrol';
        if (s === 'recoil' && state !== 'recoil') { recT = 0.9; api.flash(0.25); }
        state = api.state = s; drawEye(s === 'recoil' ? 'closed' : s); return api;
      },
      setWarning: function (on) { warnOn = !!on; return api; },
      flash: function (sec) { if (fl) body.filters = null; fl = new PIXI.filters.ColorMatrixFilter(); fl.brightness(2.2, false); body.filters = [fl]; flashT = sec || 0.2; return api; },
      update: function (dt) {
        dt = Math.min(dt || 0, 0.1); t += dt;
        curFace += (face - curFace) * Math.min(1, dt * 7); flip.scale.x = curFace;
        var sp = state === 'chase' ? 7 : state === 'recoil' ? 2.5 : 2.2, am = state === 'chase' ? 0.2 : 0.1;
        for (var i = 0; i < segs.length; i++) segs[i].rotation = Math.sin(t * sp - i * 0.9) * am * (0.6 + i * 0.25);
        var open = state === 'chase' ? 0.34 + 0.12 * Math.sin(t * 9) : state === 'recoil' ? 0 : 0.05 + 0.03 * Math.sin(t * 1.6);
        jaw.rotation += (open - jaw.rotation) * Math.min(1, dt * 14);
        for (i = 0; i < legs.length; i++) { var lg = legs[i]; lg.o.rotation = Math.sin(t * (state === 'chase' ? 8 : 3) + lg.ph) * (state === 'chase' ? 0.7 : 0.4) + 0.2; }
        body.rotation = (state === 'chase' ? 0.04 : Math.sin(t * 0.8) * 0.03);
        body.y = Math.sin(t * 1.2) * 2;
        if (state === 'recoil') { recT -= dt; body.x = Math.sin(t * 60) * 3 * Math.max(0, recT); body.rotation = -0.2 * Math.max(0, recT); if (recT <= 0) api.setState('patrol'); } else body.x = 0;
        warnV += ((warnOn || state === 'chase' ? 1 : 0) - warnV) * Math.min(1, dt * 6);
        warn.alpha = warnV * (state === 'chase' ? 0.45 + 0.25 * Math.sin(t * 10) : 0.22 + 0.1 * Math.sin(t * 4));
        warn.x = 90; warn.y = -4; warn.scale.set(1.05 + 0.12 * Math.sin(t * (state === 'chase' ? 10 : 4)));
        eyeGlow.alpha = state === 'chase' ? 0.8 + 0.2 * Math.sin(t * 10) : warnV * 0.4;
        if (fl) { flashT -= dt; if (flashT <= 0) { body.filters = null; fl = null; } }
      },
      destroy: function () { root.destroy({ children: true }); }
    };
    drawEye('patrol'); api.update(0);
    return api;
  }

  /* ============================================================
   * Nút (cây/bông) - gốc toạ độ = mặt nước, thân thả xuống dưới, hoa nhô lên
   * ============================================================ */
  function createNode(PIXI, kind) {
    var root = new PIXI.Container(), plant = new PIXI.Container(), r = rng(kind.length * 31 + 5);
    root.addChild(plant);
    var glow = add(PIXI, sprite(PIXI, T_soft(PIXI))); glow.tint = 0xfff0a0; glow.scale.set(2.2); glow.alpha = 0; glow.y = -24; root.addChild(glow);
    var sway = [], blooms = new PIXI.Container();
    function stem(x, h, col, ph, w) {
      var s = new PIXI.Container(); s.x = x;
      var g = new PIXI.Graphics().lineStyle(w || 3, col).moveTo(0, 0).quadraticCurveTo(3, -h * 0.5, 0, -h); s.addChild(g);
      sway.push({ o: s, ph: ph, a: 0.08 }); return s;
    }
    // rễ dưới nước dùng chung
    var roots = new PIXI.Graphics().lineStyle(1.6, 0x4a5a3a, 0.8);
    for (var i = 0; i < 6; i++) { var rx = (i - 2.5) * 6; roots.moveTo(rx, 4).bezierCurveTo(rx + 6, 24, rx - 6, 40, rx + (i % 2 ? 7 : -7), 56 + i * 3); }
    plant.addChild(roots); sway.push({ o: roots, ph: 1, a: 0.05, root: true });
    var K = kind;
    if (K === 'sen') {
      var pad = new PIXI.Graphics().beginFill(0x2f8a45).drawEllipse(-24, -3, 28, 7).endFill().beginFill(0x45a85a, 0.7).drawEllipse(-26, -4, 20, 4).endFill()
        .lineStyle(1, 0x1e6a30, 0.6).moveTo(-24, -3).lineTo(-48, -3).moveTo(-24, -3).lineTo(-8, -3).moveTo(-24, -3).lineTo(-40, 0).moveTo(-24, -3).lineTo(-12, 1);
      plant.addChild(pad);
      var st = stem(8, 54, 0x4a8a3a, 0.5, 3.2); plant.addChild(st);
      var fl = new PIXI.Graphics(); var pet = [-0.9, -0.45, 0, 0.45, 0.9];
      pet.forEach(function (a) { fl.beginFill(0xf6a8c8).moveTo(0, 0).bezierCurveTo(-8 + a * 8, -10, a * 18, -22, a * 14, -30).bezierCurveTo(a * 22 + 8, -20, 10 + a * 8, -8, 0, 0).endFill(); });
      fl.beginFill(0xffd8e6, 0.8).moveTo(0, 0).bezierCurveTo(-6, -8, -3, -20, 0, -26).bezierCurveTo(3, -20, 6, -8, 0, 0).endFill();
      fl.beginFill(0xf6d05a).drawEllipse(0, -2, 7, 3).endFill(); fl.y = -54; st.addChild(fl); blooms.addChild(st);
    } else if (K === 'bong_dien_dien') {
      for (i = 0; i < 4; i++) {
        var h = 46 + i * 12 + r() * 10, sx = (i - 1.5) * 12, s = stem(sx, h, 0x5a8a30, i, 2.4);
        s.children[0].lineStyle(0);
        for (var k = 0; k < 6; k++) { var lf = new PIXI.Graphics().beginFill(0x6aa83a).drawEllipse(0, 0, 7, 2.2).endFill(); lf.x = k % 2 ? 4 : -4; lf.y = -h * (0.15 + k * 0.1); lf.rotation = k % 2 ? 0.5 : -0.5 + 3.14; s.addChild(lf); }
        var cl = new PIXI.Graphics();
        for (k = 0; k < 7; k++) { var a = k * 0.9, rr = 3 + (k % 3) * 2.6; cl.beginFill(0xffd62a).drawCircle(Math.cos(a) * rr * 1.1, -Math.abs(Math.sin(a)) * rr * 0.8 - 2, 4.2).endFill(); cl.beginFill(0xfff09a, 0.7).drawCircle(Math.cos(a) * rr * 1.1 - 1, -Math.abs(Math.sin(a)) * rr * 0.8 - 3, 1.5).endFill(); }
        cl.y = -h; s.addChild(cl); plant.addChild(s); blooms.addChild(cl);
      }
    } else if (K === 'keo_neo') {
      for (i = 0; i < 5; i++) {
        var hh = 40 + r() * 34, ss = stem((i - 2) * 7, hh, 0x9a8a4a, i, 2.4);
        ss.children[0].lineStyle(0);
        var pod = new PIXI.Graphics().beginFill(0x8a5a2a).drawEllipse(0, -hh - 3, 4.5, 9).endFill().beginFill(0xc8944a, 0.8).drawEllipse(-1, -hh - 5, 1.5, 5).endFill()
          .lineStyle(1.5, 0x5a3a1a).moveTo(0, -hh + 6).lineTo(0, -hh + 10);
        ss.addChild(pod); plant.addChild(ss); blooms.addChild(pod);
      }
      var lp = new PIXI.Graphics().beginFill(0x7a9a4a).drawEllipse(-18, -2, 22, 5).endFill().drawEllipse(16, -2, 18, 4).endFill(); plant.addChild(lp);
    } else { // bong_sung / mặc định: bông súng
      for (i = 0; i < 3; i++) { var pd = new PIXI.Graphics().beginFill(0x2f8a4a).drawEllipse(0, 0, 22 - i * 3, 5.5).endFill()
        .beginFill(0x4aa862, 0.6).drawEllipse(-3, -1, 14 - i * 2, 3).endFill().lineStyle(1, 0x1e6a30, 0.7).moveTo(0, 0).lineTo(22 - i * 3, -1); pd.x = [-26, 24, -2][i]; pd.y = [-1, 0, 2][i]; pd.rotation = [0.05, -0.04, 0.02][i]; plant.addChild(pd);
        sway.push({ o: pd, ph: i, a: 0.03, bob: true }); }
      var s2 = stem(-4, 26, 0x4a8a50, 0.3, 2.6); plant.addChild(s2);
      var bl = new PIXI.Graphics();
      for (i = -3; i <= 3; i++) bl.beginFill(i % 2 ? 0xb87ae0 : 0xd8a0f0).moveTo(0, 0).bezierCurveTo(-5 + i * 3, -6, i * 8, -14, i * 6.5, -20).bezierCurveTo(i * 10 + 5, -12, 6 + i * 2, -5, 0, 0).endFill();
      bl.beginFill(0xffe36a).drawEllipse(0, -3, 4, 2.2).endFill(); bl.y = -24; s2.addChild(bl); blooms.addChild(s2);
    }
    var hv = false, hl = 0, t = r() * 6, regrow = 1;
    var api = {
      container: root, kind: K,
      setHarvested: function (v) { hv = !!v; return api; },
      setRegrow: function (p) { regrow = clamp(p, 0, 1); return api; },
      setHighlight: function (v) { hl = v ? 1 : 0; return api; },
      update: function (dt) {
        dt = Math.min(dt || 0, 0.1); t += dt;
        for (var i = 0; i < sway.length; i++) { var s = sway[i]; if (s.bob) s.o.y = Math.sin(t * 1.4 + s.ph) * 1.5 + 1; else s.o.rotation = Math.sin(t * 1.2 + s.ph) * s.a; }
        var target = hv ? 0.0 : 1, cur = blooms.alpha;
        for (i = 0; i < blooms.children.length; i++) { var b = blooms.children[i]; var sc = hv ? 0.0001 : lerp(0.2, 1, hv ? 0 : 1); b.visible = !hv || regrow > 0.99; }
        var vis = hv ? 0 : 1; blooms.alpha += (vis - blooms.alpha) * Math.min(1, dt * 8);
        plant.alpha = hv ? 0.85 : 1;
        glow.alpha += (hl * (0.28 + 0.12 * Math.sin(t * 5)) - glow.alpha) * Math.min(1, dt * 10);
      },
      destroy: function () { root.destroy({ children: true }); }
    };
    return api;
  }

  /* ============================================================
   * Sinh vật nhỏ: jellyfish (sứa), pufferfish (cá nóc), crab (cua), shell (sò), starfish
   * ============================================================ */
  function createCreature(PIXI, kind) {
    var root = new PIXI.Container(), flip = new PIXI.Container(); root.addChild(flip);
    var t = Math.random() * 10, face = 1, curFace = 1, speed = 1, tick = null, size = 30;
    var glow = null;
    if (kind === 'jellyfish') {
      glow = add(PIXI, sprite(PIXI, T_soft(PIXI))); glow.tint = 0x40c8ff; glow.scale.set(1.8); glow.alpha = 0.45; flip.addChild(glow);
      var tg = new PIXI.Graphics(), bell = new PIXI.Graphics(); flip.addChild(tg, bell);
      bell.beginFill(0x58c8ff, 0.85).moveTo(-17, 4).bezierCurveTo(-18, -22, 18, -22, 17, 4).bezierCurveTo(10, 8, -10, 8, -17, 4).endFill();
      bell.beginFill(0xb8f0ff, 0.45).drawEllipse(-5, -9, 7, 4.5).endFill();
      bell.lineStyle(1.5, 0x2a7ac8, 0.7).moveTo(-17, 4).bezierCurveTo(-10, 8, 10, 8, 17, 4);
      bell.lineStyle(0).beginFill(0xffffff, 0.6).drawCircle(-6, -2, 2).drawCircle(5, 0, 1.6).drawCircle(0, -6, 1.4).endFill();
      size = 36;
      tick = function () {
        var p = Math.sin(t * 2.4 * speed); bell.scale.set(1 + p * 0.07, 1 - p * 0.09); glow.alpha = 0.38 + 0.12 * Math.sin(t * 2.4);
        tg.clear(); for (var i = -2; i <= 2; i++) { tg.lineStyle(2, i % 2 ? 0x8ae0ff : 0x58c8ff, 0.8).moveTo(i * 5.5, 6);
          for (var k = 1; k <= 5; k++) tg.lineTo(i * 5.5 + Math.sin(t * 3 - k * 0.8 + i) * (2 + k * 0.8), 6 + k * 6 + p * 2); }
        flip.y = Math.sin(t * 0.9) * 3;
      };
    } else if (kind === 'pufferfish') {
      var tail = new PIXI.Container(); tail.x = -15; flip.addChild(tail);
      tail.addChild(new PIXI.Graphics().beginFill(0xf08a20).moveTo(0, 0).lineTo(-11, -8).quadraticCurveTo(-7, 0, -11, 8).closePath().endFill());
      var pg = new PIXI.Graphics();
      pg.beginFill(0xf6a82a).drawEllipse(0, 0, 17, 14).endFill();
      pg.beginFill(0xffe8a8).moveTo(-14, 5).bezierCurveTo(-6, 15, 8, 15, 16, 5).bezierCurveTo(8, 8, -6, 8, -14, 5).endFill();
      pg.lineStyle(2, 0xc8601a, 0.7); for (var i = 0; i < 4; i++) pg.moveTo(-9 + i * 6, -12 + Math.abs(i - 1.5) * 1.6).lineTo(-8 + i * 6, -3);
      pg.lineStyle(1.4, 0xa8501a);
      for (i = 0; i < 9; i++) { var a = -2.4 + i * 0.5, x1 = Math.cos(a) * 16, y1 = Math.sin(a) * 13; pg.moveTo(x1, y1).lineTo(x1 * 1.2, y1 * 1.22); }
      pg.lineStyle(0).beginFill(0xfff3c8, 0.7).drawEllipse(-3, -8, 8, 3).endFill();
      pg.beginFill(0xffffff).drawCircle(8, -4, 4.4).endFill().beginFill(0x10151a).drawCircle(9, -4, 2.6).endFill().beginFill(0xffffff).drawCircle(9.8, -5, 0.9).endFill();
      pg.lineStyle(1.6, 0x8a3a10).moveTo(15, 3).lineTo(12, 3.6);
      flip.addChild(pg);
      var fin = new PIXI.Container(); fin.x = 2; fin.y = 4; flip.addChild(fin); fin.addChild(new PIXI.Graphics().beginFill(0xf08a20, 0.9).drawEllipse(-4, 0, 6, 3).endFill());
      glow = add(PIXI, sprite(PIXI, T_soft(PIXI))); glow.tint = 0xffd060; glow.scale.set(1.6); glow.alpha = 0.28; flip.addChildAt(glow, 0);
      size = 34;
      tick = function () { tail.rotation = Math.sin(t * 9 * speed) * 0.4; fin.rotation = Math.sin(t * 12) * 0.5; flip.y = Math.sin(t * 1.4) * 2; };
    } else if (kind === 'crab') {
      var legs = new PIXI.Graphics(), body = new PIXI.Graphics(), claws = new PIXI.Container(); flip.addChild(legs, body, claws);
      body.beginFill(0xb04a9a).drawEllipse(0, 0, 15, 10).endFill().beginFill(0xd878c0, 0.8).drawEllipse(-2, -3, 10, 5).endFill();
      body.lineStyle(1.4, 0x6a2a60, 0.8).drawEllipse(0, 0, 15, 10);
      body.lineStyle(2, 0x6a2a60).moveTo(-5, -9).lineTo(-6, -15).moveTo(5, -9).lineTo(6, -15);
      body.lineStyle(0).beginFill(0xffffff).drawCircle(-6, -16, 3).drawCircle(6, -16, 3).endFill().beginFill(0x10151a).drawCircle(-6, -16, 1.5).drawCircle(6, -16, 1.5).endFill();
      [-1, 1].forEach(function (sd) { var cl = new PIXI.Container(); cl.x = sd * 14; cl.y = -4; cl.sd = sd;
        cl.addChild(new PIXI.Graphics().lineStyle(3, 0x9a3a8a).moveTo(0, 0).lineTo(sd * 8, -8).lineStyle(0).beginFill(0xd05ab0).drawEllipse(sd * 11, -13, 7, 5.5).endFill().beginFill(0xb04a9a).moveTo(sd * 15, -13).lineTo(sd * 20, -17).lineTo(sd * 18, -10).closePath().endFill());
        claws.addChild(cl); });
      size = 40;
      tick = function () {
        legs.clear(); legs.lineStyle(2.4, 0x8a3a7a);
        for (var s2 = -1; s2 <= 1; s2 += 2) for (var k = 0; k < 3; k++) { var sw = Math.sin(t * 10 * speed + k * 1.7 + (s2 > 0 ? 1 : 0)) * 3 * Math.min(speed, 1.2); legs.moveTo(s2 * 10, 2 + k * 2).lineTo(s2 * (17 + k * 2) + sw, 6 + k * 2).lineTo(s2 * (20 + k * 3) + sw, 12 + k * 1.5); }
        claws.children.forEach(function (cl) { cl.rotation = cl.sd * Math.sin(t * 2.2 + (cl.sd > 0 ? 1.5 : 0)) * 0.18; });
        body.y = Math.sin(t * 10 * speed) * 0.6 * Math.min(speed, 1.2);
      };
    } else if (kind === 'starfish') {
      var sf2 = new PIXI.Graphics(), pts = [], pts2 = [];
      for (i = 0; i < 10; i++) { var rr = i % 2 ? 6 : 17, an = -Math.PI / 2 + i * Math.PI / 5; pts.push(Math.cos(an) * rr, Math.sin(an) * rr); }
      sf2.beginFill(0xf0643a).drawPolygon(pts).endFill().lineStyle(1.5, 0xa83a1a, 0.8).drawPolygon(pts).lineStyle(0).beginFill(0xffb08a, 0.9);
      for (i = 0; i < 5; i++) { var an2 = -Math.PI / 2 + i * TAU / 5; sf2.drawCircle(Math.cos(an2) * 9, Math.sin(an2) * 9, 1.6); }
      sf2.endFill(); flip.addChild(sf2); size = 34; tick = function () { sf2.rotation = Math.sin(t * 0.8) * 0.06; };
    } else { // shell: sò điệp + ngọc trai
      var sh = new PIXI.Graphics();
      sh.beginFill(0xf4a8c4).moveTo(0, 10).bezierCurveTo(-22, 6, -20, -16, 0, -18).bezierCurveTo(20, -16, 22, 6, 0, 10).endFill();
      sh.lineStyle(1.6, 0xc8607e, 0.8); for (i = -3; i <= 3; i++) sh.moveTo(0, 9).quadraticCurveTo(i * 5, -4, i * 6.4, -16 + Math.abs(i) * 2.4);
      sh.lineStyle(2, 0xd87a98).moveTo(0, 10).bezierCurveTo(-22, 6, -20, -16, 0, -18).bezierCurveTo(20, -16, 22, 6, 0, 10);
      sh.lineStyle(0).beginFill(0xe8d0a0).drawRoundedRect(-6, 8, 12, 5, 2).endFill();
      var pearl = new PIXI.Graphics().beginFill(0xffffff).drawCircle(0, -2, 4).endFill().beginFill(0xd8f0ff, 0.8).drawCircle(-1, -3, 2).endFill();
      glow = add(PIXI, sprite(PIXI, T_soft(PIXI))); glow.tint = 0xfff0f8; glow.scale.set(1.3); glow.alpha = 0.3;
      flip.addChild(glow, sh, pearl); size = 34;
      tick = function () { glow.alpha = 0.2 + 0.2 * Math.max(0, Math.sin(t * 2)); pearl.scale.set(1 + 0.06 * Math.sin(t * 2)); };
    }
    var api = {
      container: root, kind: kind, width: size, height: size,
      setFacing: function (d) { face = d < 0 ? -1 : 1; return api; },
      setSpeed: function (v) { speed = clamp(v, 0, 3); return api; },
      update: function (dt) {
        dt = Math.min(dt || 0, 0.1); t += dt; curFace += (face - curFace) * Math.min(1, dt * 12); flip.scale.x = curFace; if (tick) tick();
      },
      destroy: function () { root.destroy({ children: true }); }
    };
    api.update(0);
    return api;
  }

  /* ============================================================
   * FX
   * ============================================================ */
  function createFX(PIXI) {
    var root = new PIXI.Container(), pool = [], live = [], emitters = [], MAX = 420;
    function get() {
      var p = pool.pop();
      if (!p) { if (live.length >= MAX) { p = live.shift(); } else { p = { s: new PIXI.Sprite() }; p.s.anchor.set(0.5); root.addChild(p.s); } }
      p.s.visible = true; return p;
    }
    function spawn(texture, x, y, o) {
      var p = get(), s = p.s; s.texture = texture; s.x = x; s.y = y; s.tint = o.tint === undefined ? 0xffffff : o.tint;
      s.blendMode = o.add ? PIXI.BLEND_MODES.ADD : PIXI.BLEND_MODES.NORMAL; s.rotation = o.rot || 0;
      p.vx = o.vx || 0; p.vy = o.vy || 0; p.ax = o.ax || 0; p.ay = o.ay || 0; p.drag = o.drag || 0; p.life = o.life || 1; p.age = 0;
      p.s0 = o.s0 || 0.5; p.s1 = o.s1 === undefined ? p.s0 : o.s1; p.a = o.a === undefined ? 1 : o.a; p.inT = o.inT === undefined ? 0.15 : o.inT;
      p.wob = o.wob || 0; p.wf = o.wf || 3; p.ph = Math.random() * TAU; p.rs = o.rs || 0; p.stretch = o.stretch || 0; p.bx = x;
      s.scale.set(p.s0); s.alpha = 0; live.push(p); return p;
    }
    function ring(x, y, tint, r0, r1, life, a) { return spawn(T_bubble(PIXI), x, y, { tint: tint, s0: r0, s1: r1, life: life, a: a, inT: 0.05, add: true }); }
    var fx = {
      container: root,
      /* mùi ươn xanh lục: trả handle {x,y,stop(),setPos()} */
      spoiled: function (x, y, opt) {
        opt = opt || {};
        var e = { x: x, y: y, acc: 0, on: true, rate: opt.rate || 16, kind: 'spoiled', lt: 0 };
        if (opt.label !== false) {
          var tx = new PIXI.Text('ƯƠN', { fontFamily: 'Arial, sans-serif', fontSize: 15, fontWeight: '800', fill: 0xb6ff5a, stroke: 0x1d3a0a, strokeThickness: 4 });
          tx.anchor.set(0.5); root.addChild(tx); e.label = tx;
        }
        e.stop = function () { e.on = false; if (e.label) { e.label.destroy(); e.label = null; } var i = emitters.indexOf(e); if (i >= 0) emitters.splice(i, 1); };
        e.setPos = function (nx, ny) { e.x = nx; e.y = ny; };
        emitters.push(e); return e;
      },
      /* khói cháy đen */
      smoke: function (x, y, opt) {
        opt = opt || {};
        var e = { x: x, y: y, acc: 0, on: true, rate: opt.rate || 12, kind: 'smoke' };
        e.stop = function () { e.on = false; var i = emitters.indexOf(e); if (i >= 0) emitters.splice(i, 1); };
        e.setPos = function (nx, ny) { e.x = nx; e.y = ny; };
        emitters.push(e); return e;
      },
      /* bọt vỡ */
      burst: function (x, y, n) {
        n = n || 12;
        ring(x, y, 0xffffff, 0.3, 0.9, 0.35, 0.9);
        for (var i = 0; i < n; i++) { var a = i / n * TAU + Math.random() * 0.4, sp = 40 + Math.random() * 80;
          spawn(T_bubble(PIXI), x, y, { vx: Math.cos(a) * sp, vy: Math.sin(a) * sp - 10, ay: -50, drag: 2.2, s0: 0.1 + Math.random() * 0.14, s1: 0.04, life: 0.5 + Math.random() * 0.4, a: 0.9, inT: 0.05 }); }
      },
      /* chớp trúng đòn (đỏ-trắng) */
      hit: function (x, y, color) {
        color = color === undefined ? 0xff5a3a : color;
        spawn(T_soft(PIXI), x, y, { add: true, tint: 0xffffff, s0: 1.2, s1: 3.2, life: 0.22, a: 1, inT: 0.02 });
        spawn(T_soft(PIXI), x, y, { add: true, tint: color, s0: 2, s1: 4.4, life: 0.32, a: 0.75, inT: 0.02 });
        ring(x, y, color, 0.5, 2.2, 0.3, 1);
        for (var i = 0; i < 9; i++) { var a = i / 9 * TAU + Math.random() * 0.3, sp = 140 + Math.random() * 120;
          spawn(T_soft(PIXI), x, y, { add: true, tint: i % 2 ? 0xfff2a0 : color, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, drag: 5, s0: 0.28, s1: 0.04, life: 0.3, a: 1, inT: 0.02, rot: a, stretch: 1 }); }
      },
      clear: function () { while (live.length) { var p = live.pop(); p.s.visible = false; pool.push(p); } emitters.slice().forEach(function (e) { e.stop(); }); },
      update: function (dt) {
        dt = Math.min(dt || 0, 0.1);
        for (var i = 0; i < emitters.length; i++) {
          var e = emitters[i]; e.acc += dt * e.rate;
          if (e.kind === 'spoiled') {
            e.lt = (e.lt || 0) + dt;
            if (e.label) { e.label.x = e.x; e.label.y = e.y - 44 + Math.sin(e.lt * 3) * 3; e.label.alpha = 0.75 + 0.25 * Math.sin(e.lt * 6); }
            while (e.acc >= 1) { e.acc -= 1;
              spawn(T_puff(PIXI), e.x + (Math.random() - 0.5) * 22, e.y + Math.random() * 6, { tint: Math.random() < 0.5 ? 0x7fdc3a : 0xb6e84a, vy: -22 - Math.random() * 16, vx: (Math.random() - 0.5) * 10, s0: 0.5, s1: 1.5, life: 1.4 + Math.random() * 0.6, a: 0.7, wob: 8, wf: 2 + Math.random() * 2 });
              if (Math.random() < 0.25) spawn(T_bubble(PIXI), e.x + (Math.random() - 0.5) * 18, e.y, { tint: 0xc8ff70, vy: -30, s0: 0.1, s1: 0.16, life: 1.1, a: 0.8, wob: 6 }); }
          } else {
            while (e.acc >= 1) { e.acc -= 1;
              spawn(T_puff(PIXI), e.x + (Math.random() - 0.5) * 14, e.y, { tint: Math.random() < 0.3 ? 0x4a4440 : 0x23201f, vy: -34 - Math.random() * 24, vx: (Math.random() - 0.5) * 14 + 6, s0: 0.25, s1: 1.2, life: 1.6 + Math.random() * 0.8, a: 0.62, wob: 10, wf: 1.5 });
              if (Math.random() < 0.3) spawn(T_soft(PIXI), e.x, e.y + 4, { add: true, tint: 0xff6a20, vy: -50 - Math.random() * 30, vx: (Math.random() - 0.5) * 24, s0: 0.1, s1: 0.02, life: 0.8, a: 0.9 }); }
          }
        }
        for (i = live.length - 1; i >= 0; i--) {
          var p = live[i]; p.age += dt;
          if (p.age >= p.life) { p.s.visible = false; pool.push(p); live.splice(i, 1); continue; }
          var u = p.age / p.life;
          if (p.drag) { var k = Math.max(0, 1 - p.drag * dt); p.vx *= k; p.vy *= k; }
          p.vx += p.ax * dt; p.vy += p.ay * dt; p.s.x += p.vx * dt; p.s.y += p.vy * dt;
          if (p.wob) p.s.x += Math.sin(p.age * p.wf + p.ph) * p.wob * dt;
          p.s.rotation += p.rs * dt;
          var sc = lerp(p.s0, p.s1, u); p.s.scale.set(p.stretch ? sc * 2.4 : sc, sc);
          p.s.alpha = p.a * (u < p.inT ? u / p.inT : 1 - (u - p.inT) / (1 - p.inT));
        }
      },
      destroy: function () { emitters.length = 0; root.destroy({ children: true }); }
    };
    return fx;
  }

  /* ============================================================
   * Quán: nhìn chéo từ trên xuống, thuyền nhà hàng nổi
   * ============================================================ */
  function T_planks(PIXI) {
    return tex(PIXI, 'planks', function () {
      var c = cvs(256, 256), x = c.getContext('2d'), r = rng(88);
      for (var i = 0; i < 8; i++) {
        var y = i * 32, base = [0xa8743c, 0xb07a40, 0x9c6a36, 0xb58246][i % 4];
        x.fillStyle = hex(mixC(base, 0xffffff, r() * 0.08)); x.fillRect(0, y, 256, 32);
        x.strokeStyle = 'rgba(70,40,15,0.22)'; x.lineWidth = 1;
        for (var k = 0; k < 5; k++) { var gy = y + 4 + r() * 24; x.beginPath(); x.moveTo(0, gy); x.bezierCurveTo(70, gy + (r() - 0.5) * 5, 160, gy + (r() - 0.5) * 5, 256, gy); x.stroke(); }
        x.fillStyle = 'rgba(40,22,8,0.55)'; x.fillRect(0, y + 30, 256, 2);
        x.fillStyle = 'rgba(255,230,170,0.18)'; x.fillRect(0, y, 256, 1.5);
        var sx = (i % 2) * 128 + 40 + r() * 20; x.fillStyle = 'rgba(40,22,8,0.45)'; x.fillRect(sx, y, 2, 30);
        x.fillStyle = 'rgba(50,30,12,0.6)'; x.beginPath(); x.arc(sx + 6, y + 6, 1.4, 0, TAU); x.arc(sx + 6, y + 26, 1.4, 0, TAU); x.fill();
      }
      return c;
    }, true);
  }
  function T_water(PIXI, kind) {
    return tex(PIXI, 'water' + kind, function () {
      var c = cvs(512, 512), x = c.getContext('2d'), r = rng(101 + kind);
      if (kind === 0) {
        x.fillStyle = '#2a9ea8'; x.fillRect(0, 0, 512, 512);
        for (var q = 0; q < 26; q++) { var bx = r() * 512, by = r() * 512, br = 40 + r() * 70, bgd = x.createRadialGradient(bx, by, 0, bx, by, br);
          bgd.addColorStop(0, r() < 0.5 ? 'rgba(255,255,255,0.07)' : 'rgba(0,50,70,0.10)'); bgd.addColorStop(1, 'rgba(0,0,0,0)');
          [[0, 0], [512, 0], [-512, 0], [0, 512], [0, -512]].forEach(function (o2) { x.save(); x.translate(o2[0], o2[1]); x.fillStyle = bgd; x.fillRect(bx - br, by - br, br * 2, br * 2); x.restore(); }); }
      }
      x.strokeStyle = kind ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.12)'; x.lineWidth = kind ? 2 : 3; x.lineCap = 'round';
      for (var i = 0; i < (kind ? 40 : 30); i++) {
        var px = r() * 512, py = r() * 512, w = 24 + r() * 50;
        [[0, 0], [512, 0], [-512, 0], [0, 512], [0, -512]].forEach(function (o) { x.beginPath(); x.moveTo(px + o[0], py + o[1]); x.quadraticCurveTo(px + w / 2 + o[0], py - 7 + o[1], px + w + o[0], py + o[1]); x.stroke(); });
      }
      return c;
    }, true);
  }
  function createQuanScene(PIXI, o) {
    o = o || {};
    var W = o.width || DEF.width, H = o.height || DEF.height;
    var ppu = o.pxPerUnit || Math.min(W / 19.2, H / 12.4);
    var ox = o.originX !== undefined ? o.originX : (W - 16 * ppu) / 2 + 0.5 * ppu, oy = o.originY !== undefined ? o.originY : (H - 10 * ppu) / 2 - 0.1 * ppu;
    function sx(x) { return ox + x * ppu; }
    function sy(z) { return oy + z * ppu; }
    var r = rng(o.seed || 17);
    var root = new PIXI.Container();
    var w1 = new PIXI.TilingSprite(T_water(PIXI, 0), W, H), w2 = new PIXI.TilingSprite(T_water(PIXI, 1), W, H), w3 = new PIXI.TilingSprite(T_water(PIXI, 1), W, H);
    w2.alpha = 0.7; w3.alpha = 0.4; w3.tileScale.set(1.6); root.addChild(w1, w2, w3);
    // phù sa/vignette nước
    var vg = new PIXI.Sprite(T_vignette(PIXI)); vg.width = W; vg.height = H; vg.alpha = 0.5; root.addChild(vg);
    // bóng dưới thuyền
    var X0 = -0.7, X1 = 16.7, Z0 = -0.7, Z1 = 10.7, bowX = -2.0;
    var hull = new PIXI.Graphics();
    function hullPath(g, dx, dy, grow) {
      g.moveTo(sx(X0) - grow + dx, sy(Z0) - grow + dy).lineTo(sx(X1) + grow + dx, sy(Z0) - grow + dy).lineTo(sx(X1) + grow + dx, sy(Z1) + grow + dy).lineTo(sx(X0) - grow + dx, sy(Z1) + grow + dy)
        .quadraticCurveTo(sx(bowX + 0.4) + dx, sy(Z1 - 1.6) + dy, sx(bowX) + dx, sy(5) + dy).quadraticCurveTo(sx(bowX + 0.4) + dx, sy(Z0 + 1.6) + dy, sx(X0) - grow + dx, sy(Z0) - grow + dy);
    }
    hull.beginFill(0x00202a, 0.35); hullPath(hull, 8, 14, 6); hull.endFill();
    // mạn thuyền (nhìn chéo: dày hơn ở phía dưới)
    hull.beginFill(0x4a2c14); hullPath(hull, 0, 12, 6); hull.endFill();
    hull.lineStyle(2, 0x2a1608, 0.8); for (var i = 0; i < 10; i++) { var hx = sx(X0 + i * 1.8); hull.moveTo(hx, sy(Z1) + 12).lineTo(hx, sy(Z1) + 20); }
    hull.lineStyle(0).beginFill(0x6b4222); hullPath(hull, 0, 0, 6); hull.endFill();
    root.addChild(hull);
    // sàn gỗ
    var deckG = new PIXI.Graphics(); deckG.beginFill(0xffffff); hullPath(deckG, 0, 0, -2); deckG.endFill();
    var deck = new PIXI.TilingSprite(T_planks(PIXI), W, H); deck.tileScale.set(ppu / 62); deck.mask = deckG; root.addChild(deckG, deck);
    // viền lan can
    var rail = new PIXI.Graphics(); rail.lineStyle(7, 0x5a3718); hullPath(rail, 0, 0, -2); rail.lineStyle(2.5, 0xc8924e, 0.8); hullPath(rail, 0, -2, -4);
    root.addChild(rail);
    // chiếu/thảm khu bàn
    var mat = new PIXI.Graphics().beginFill(0xc85a3a, 0.13).drawRoundedRect(sx(7.2), sy(0.2), ppu * 8.8, ppu * 7.4, 14).endFill()
      .lineStyle(2, 0xf0d090, 0.22).drawRoundedRect(sx(7.35), sy(0.35), ppu * 8.5, ppu * 7.1, 12);
    root.addChild(mat);
    // bếp khu vực
    var kz = new PIXI.Graphics().beginFill(0x3a2210, 0.12).drawRoundedRect(sx(0.2), sy(6.6), ppu * 6.8, ppu * 3.8, 14).endFill(); root.addChild(kz);

    var actors = new PIXI.Container(); actors.sortableChildren = true;
    var fx = createFX(PIXI);
    var tables = {}, stoves = {}, lanterns = [], T = o.tables || { T1: [9, 2], T2: [13, 2], T3: [9, 6], T4: [13, 6] }, S = o.stoves || { B1: [2, 8], B2: [5, 8] };

    function shadowE(px, py, rx, ry) { return new PIXI.Graphics().beginFill(0x000000, 0.25).drawEllipse(px, py, rx, ry).endFill(); }
    // đồ trang trí
    var decor = new PIXI.Container(); root.addChild(decor);
    function crate(x, z, wu) { var g = new PIXI.Container(); g.x = sx(x); g.y = sy(z); var w = ppu * wu;
      g.addChild(shadowE(4, w * 0.5, w * 0.62, w * 0.2));
      g.addChild(new PIXI.Graphics().beginFill(0x7a4a24).drawRect(-w / 2, -w * 0.32, w, w * 0.64).endFill().beginFill(0xa8723a).drawRect(-w / 2, -w * 0.32, w, w * 0.22).endFill().lineStyle(2, 0x4a2a10).drawRect(-w / 2, -w * 0.32, w, w * 0.64).moveTo(-w / 2, -w * 0.1).lineTo(w / 2, -w * 0.1).moveTo(-w / 2, w * 0.12).lineTo(w / 2, w * 0.12));
      decor.addChild(g); }
    function jar(x, z, rr, col) { var g = new PIXI.Container(); g.x = sx(x); g.y = sy(z); g.addChild(shadowE(3, rr * 0.6, rr * 1.05, rr * 0.4));
      g.addChild(new PIXI.Graphics().beginFill(col).drawEllipse(0, 0, rr, rr * 0.82).endFill().beginFill(mixC(col, 0x000000, 0.5)).drawEllipse(0, -rr * 0.15, rr * 0.62, rr * 0.45).endFill().beginFill(0xffffff, 0.25).drawEllipse(-rr * 0.4, -rr * 0.35, rr * 0.25, rr * 0.14).endFill()); decor.addChild(g); }
    crate(0.4, 4.4, 0.9); crate(0.6, 5.4, 0.7); jar(1.3, 5.6, 0.34, 0x8a4a22); jar(0.5, 3.4, 0.28, 0x4a6a8a); jar(6.4, 5.4, 0.3, 0x8a4a22);
    // cuộn dây, nón lá
    var rope = new PIXI.Graphics().lineStyle(3, 0xd8c08a); for (i = 0; i < 4; i++) rope.drawEllipse(sx(15.3), sy(9.4), 14 - i * 3, 8 - i * 1.5); decor.addChild(rope);
    var hat = new PIXI.Container(); hat.x = sx(6.0); hat.y = sy(9.7); hat.addChild(new PIXI.Graphics().beginFill(0xe8d090).drawCircle(0, 0, 17).endFill().lineStyle(1, 0xa8884a, 0.8).drawCircle(0, 0, 12).drawCircle(0, 0, 6).drawCircle(0, 0, 1)); decor.addChild(hat);
    // bảng hiệu
    var sg = new PIXI.Container(); sg.x = sx(8); sg.y = sy(-0.55);
    sg.addChild(new PIXI.Graphics().beginFill(0x4a2a12).drawRoundedRect(-95, -15, 190, 30, 6).endFill().lineStyle(2, 0xf0c060).drawRoundedRect(-91, -11, 182, 22, 4));
    var st = new PIXI.Text('QUÁN CHỢ NỔI', { fontFamily: 'Arial, sans-serif', fontSize: 16, fontWeight: '800', fill: 0xffe08a, letterSpacing: 2 }); st.anchor.set(0.5); sg.addChild(st); decor.addChild(sg);

    function makeTable(id, tx, tz) {
      var c = new PIXI.Container(); c.x = sx(tx); c.y = sy(tz); c.zIndex = tz;
      var R = ppu * 0.78;
      c.addChild(shadowE(5, R * 0.45, R * 1.05, R * 0.55));
      for (var k = 0; k < 4; k++) { // ghế đẩu
        var a = k * Math.PI / 2 + Math.PI / 4, stx = Math.cos(a) * R * 1.12, sty = Math.sin(a) * R * 0.78;
        var sg = new PIXI.Graphics().beginFill(0x000000, 0.2).drawEllipse(stx + 2, sty + 10, 13, 6).endFill().beginFill(0x7a4a24).drawRect(stx - 9, sty, 18, 9).endFill().beginFill(0xd8a458).drawEllipse(stx, sty, 12, 6.5).endFill()
          .lineStyle(1.3, 0x7a4a24, 0.8).drawEllipse(stx, sty, 12, 6.5);
        c.addChild(sg);
      }
      var tg = new PIXI.Graphics().beginFill(0x5a3416).drawEllipse(0, R * 0.34, R, R * 0.58).endFill().beginFill(0x6b4120).drawRect(-R, R * 0.02 - 0, R * 2, R * 0.34).endFill().beginFill(0x5a3416).drawEllipse(0, R * 0.36, R, R * 0.58).endFill();
      var top = new PIXI.Graphics().beginFill(0xc89050).drawEllipse(0, 0, R, R * 0.58).endFill().beginFill(0xdfae6a).drawEllipse(-R * 0.12, -R * 0.1, R * 0.75, R * 0.38).endFill()
        .lineStyle(2, 0x7a4a24).drawEllipse(0, 0, R, R * 0.58).lineStyle(1, 0x8a5a2a, 0.4).drawEllipse(0, 0, R * 0.65, R * 0.37);
      // chai nước mắm + đũa
      var props = new PIXI.Graphics().beginFill(0x6a3a1a).drawRoundedRect(-R * 0.5, -R * 0.2, 7, 11, 2).endFill().beginFill(0xe8352a).drawRect(-R * 0.5 + 1, -R * 0.2 - 3, 5, 3).endFill()
        .lineStyle(1.6, 0xe8d8a8).moveTo(R * 0.25, -R * 0.15).lineTo(R * 0.55, -R * 0.1).moveTo(R * 0.25, -R * 0.08).lineTo(R * 0.55, -R * 0.03);
      var dish = new PIXI.Graphics().beginFill(0xf4f0e4).drawEllipse(0, 0, R * 0.38, R * 0.22).endFill().beginFill(0xd88a3a).drawEllipse(0, -1, R * 0.26, R * 0.14).endFill().beginFill(0x6aa83a).drawCircle(-4, -2, 3).drawCircle(5, 0, 2.5).endFill();
      dish.y = R * 0.04; dish.visible = false;
      var steam = add(PIXI, sprite(PIXI, T_puff(PIXI))); steam.scale.set(0.35); steam.alpha = 0; steam.y = -10;
      var hl = add(PIXI, sprite(PIXI, T_soft(PIXI))); hl.tint = 0xffe27a; hl.width = R * 3.4; hl.height = R * 2; hl.y = 4; hl.alpha = 0;
      var lbl = new PIXI.Text(id, { fontFamily: 'Arial, sans-serif', fontSize: 13, fontWeight: '800', fill: 0xfff2d0, stroke: 0x3a2008, strokeThickness: 3 }); lbl.anchor.set(0.5); lbl.y = R * 0.78 + 6;
      c.addChild(hl, tg, top, props, dish, steam, lbl);
      c.st = { dish: false, dirty: false, hl: 0, steam: steam, dishG: dish, hlS: hl, R: R, dirtyG: null };
      return c;
    }
    Object.keys(T).forEach(function (id) { var t = makeTable(id, T[id][0], T[id][1]); tables[id] = t; actors.addChild(t); });

    function makeStove(id, bx, bz) {
      var c = new PIXI.Container(); c.x = sx(bx); c.y = sy(bz); c.zIndex = bz;
      var w = ppu * 1.35, h = ppu * 0.9;
      c.addChild(shadowE(6, h * 0.55, w * 0.7, h * 0.25));
      var body = new PIXI.Graphics().beginFill(0x7a3a22).drawRoundedRect(-w / 2, -h * 0.1, w, h * 0.6, 6).endFill()
        .beginFill(0x9a4a2a).drawRoundedRect(-w / 2, -h * 0.3, w, h * 0.42, 6).endFill()
        .lineStyle(1.4, 0x4a2010, 0.6); for (var i = 0; i < 4; i++) body.moveTo(-w / 2 + 4, -h * 0.1 + i * 7).lineTo(w / 2 - 4, -h * 0.1 + i * 7);
      body.lineStyle(0).beginFill(0x1a0a04).drawEllipse(0, 4, w * 0.2, h * 0.17).endFill();
      var fire = new PIXI.Container(); fire.y = 2;
      var fl = add(PIXI, sprite(PIXI, T_soft(PIXI))); fl.tint = 0xff7a20; fl.scale.set(1.1); fl.alpha = 0; fire.addChild(fl);
      var flame = new PIXI.Graphics(); fire.addChild(flame);
      var pot = new PIXI.Graphics().beginFill(0x2a2a2e).drawEllipse(0, -h * 0.36, w * 0.4, h * 0.26).endFill().beginFill(0x15151a).drawEllipse(0, -h * 0.4, w * 0.33, h * 0.2).endFill()
        .lineStyle(2, 0x6a6a72).drawEllipse(0, -h * 0.4, w * 0.35, h * 0.22);
      var cont2 = new PIXI.Graphics(); // món bên trong
      var ready = add(PIXI, sprite(PIXI, T_soft(PIXI))); ready.tint = 0x7aff7a; ready.scale.set(1.5); ready.alpha = 0; ready.y = -h * 0.35;
      var lbl = new PIXI.Text(id, { fontFamily: 'Arial, sans-serif', fontSize: 13, fontWeight: '800', fill: 0xfff2d0, stroke: 0x3a2008, strokeThickness: 3 }); lbl.anchor.set(0.5); lbl.y = h * 0.62;
      var steam = add(PIXI, sprite(PIXI, T_puff(PIXI))); steam.scale.set(0.3); steam.alpha = 0; steam.y = -h * 0.5;
      c.addChild(body, fire, pot, cont2, ready, steam, lbl);
      c.st = { state: 'idle', fire: fire, fl: fl, flame: flame, steam: steam, ready: ready, pot: pot, w: w, h: h, smoke: null, ph: r() * 6 };
      return c;
    }
    Object.keys(S).forEach(function (id) { var s = makeStove(id, S[id][0], S[id][1]); stoves[id] = s; actors.addChild(s); });
    root.addChild(actors);

    // cột + đèn lồng
    function lanternPost(x, z) {
      var p = new PIXI.Container(); p.x = sx(x); p.y = sy(z); p.zIndex = z;
      p.addChild(shadowE(3, 6, 11, 5));
      p.addChild(new PIXI.Graphics().beginFill(0x4a2a12).drawRect(-4, -72, 8, 74).endFill().beginFill(0x7a4a24).drawRect(-4, -72, 3, 74).endFill().lineStyle(4, 0x4a2a12).moveTo(0, -70).lineTo(22, -70));
      var l = lantern(PIXI, 0xe8352a); l.x = 22; l.y = -58; l.scale.set(1.3); p.addChild(l); l.base = l.glow.alpha; p.lantern = l;
      actors.addChild(p); lanterns.push(p);
      var pool2 = add(PIXI, sprite(PIXI, T_soft(PIXI))); pool2.tint = 0xffa84a; pool2.x = sx(x) + 22; pool2.y = sy(z) + 10; pool2.width = ppu * 5; pool2.height = ppu * 3.4; pool2.alpha = 0.3; pool2.blendMode = PIXI.BLEND_MODES.ADD; root.addChild(pool2); p.pool = pool2;
    }
    lanternPost(0.1, 0.1); lanternPost(15.9, 0.1); lanternPost(0.1, 9.9); lanternPost(15.9, 9.9); lanternPost(7.6, 4.2);
    var ambient = new PIXI.Sprite(T_vignette(PIXI)); ambient.width = W; ambient.height = H; ambient.alpha = 0.55; root.addChild(fx.container);

    var t = 0;
    var api = {
      container: root, actors: actors, fx: fx, ppu: ppu, width: W, height: H,
      toScreen: function (x, z) { return { x: sx(x), y: sy(z) }; },
      toWorld: function (px, py) { return { x: (px - ox) / ppu, z: (py - oy) / ppu }; },
      setTable: function (id, st) { var tb = tables[id]; if (!tb) return api; for (var k in st) tb.st[k] = st[k]; tb.st.dishG.visible = !!tb.st.dish; return api; },
      setStove: function (id, state) {
        var s = stoves[id]; if (!s) return api; if (s.st.state === state) return api; s.st.state = state;
        if (s.st.smoke) { s.st.smoke.stop(); s.st.smoke = null; }
        if (state === 'burning') s.st.smoke = fx.smoke(s.x, s.y - s.st.h * 0.5, { rate: 14 });
        return api;
      },
      update: function (dt) {
        dt = Math.min(dt || 0, 0.1); t += dt;
        w1.tilePosition.set(t * 6, t * 3); w2.tilePosition.set(-t * 9, t * 5); w3.tilePosition.set(t * 4, -t * 6);
        for (var id in tables) { var tb = tables[id], s = tb.st; s.steam.alpha = s.dish ? 0.28 + 0.1 * Math.sin(t * 3) : 0; s.steam.y = -12 - (t * 20 % 24); s.hlS.alpha += ((s.hl ? 0.45 : 0) - s.hlS.alpha) * Math.min(1, dt * 10); }
        for (id in stoves) {
          var sv = stoves[id], q = sv.st, on = q.state !== 'idle';
          var f = on ? 0.75 + 0.25 * Math.sin(t * 13 + q.ph) + 0.1 * Math.sin(t * 29) : 0;
          q.fl.alpha += ((on ? 0.9 : 0) - q.fl.alpha) * Math.min(1, dt * 8);
          q.flame.clear();
          if (on) { var fh = (q.state === 'burning' ? 22 : 15) * f; var cols = q.state === 'burning' ? [0xff3a14, 0xff8a20, 0xffe060] : [0xff7a1a, 0xffc040, 0xfff2a0];
            for (var k = 0; k < 3; k++) q.flame.beginFill(cols[k], 0.9).moveTo(-9 + k * 2, 2).quadraticCurveTo(-9 + k * 2 + 3 * Math.sin(t * 15 + k), -fh * (1 - k * 0.25), 0, -fh * (1.15 - k * 0.3)).quadraticCurveTo(9 - k * 2 + 3 * Math.cos(t * 17 + k), -fh * (1 - k * 0.25), 9 - k * 2, 2).endFill(); }
          q.steam.alpha = q.state === 'cooking' ? 0.3 + 0.1 * Math.sin(t * 4) : 0; q.steam.y = -q.h * 0.55 - (t * 28 % 30); q.steam.scale.set(0.3 + (t * 28 % 30) / 60);
          q.ready.alpha = q.state === 'ready' ? 0.35 + 0.25 * Math.sin(t * 6) : 0;
          if (q.state === 'burning') q.pot.tint = 0xcc8870; else q.pot.tint = 0xffffff;
        }
        for (var i = 0; i < lanterns.length; i++) { var p = lanterns[i]; p.lantern.glow.alpha = 0.5 + 0.15 * Math.sin(t * 6 + i * 2) + 0.05 * Math.sin(t * 17 + i); p.lantern.rotation = Math.sin(t * 1.6 + i) * 0.07; p.pool.alpha = 0.26 + 0.05 * Math.sin(t * 5 + i); }
        fx.update(dt);
      },
      destroy: function () { fx.destroy(); root.destroy({ children: true }); }
    };
    api.update(0);
    return api;
  }

  G.ChoNoiArt.env = {
    version: '1.0.0', defaults: DEF,
    createUnderwater: createUnderwater, createSurface: createSurface,
    createFish: createFish, createCreature: createCreature, createCrocodile: createCrocodile, createNode: createNode,
    createQuanScene: createQuanScene, createFX: createFX
  };
})();
