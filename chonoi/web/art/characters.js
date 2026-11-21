/* Chợ Nổi — nhân vật vẽ thủ tục bằng PIXI.Graphics (PixiJS v7). Không tài nguyên ngoài.
 * Phong cách: 2D cartoon chunky, viền tối, tô phẳng (cel) + highlight.
 * API: window.ChoNoiArt.characters.{createDiver, createCustomer, createChef, createWaiter}(PIXI, opts)
 *   -> { container, update(dt), setState(name), setFacing(+1|-1), destroy(), state }
 * Toạ độ gốc: diver = tâm thân (cao ~96px); customer/chef/waiter = giữa chân/ghế (y=0 là mặt bàn/sàn).
 * opts chung: scale (1), x, y, facing (+1). Dựng một lần, update chỉ đổi transform. */
(function () {
  "use strict";
  var OL = 0x1c1522;

  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function shade(c, k) {
    var r = ((c >> 16) & 255) * k, g = ((c >> 8) & 255) * k, b = (c & 255) * k;
    return (clamp(r, 0, 255) << 16) | (clamp(g, 0, 255) << 8) | clamp(b, 0, 255);
  }
  function light(c, k) { // k>1: trộn về trắng
    var t = clamp(k - 1, 0, 1), r = (c >> 16) & 255, g = (c >> 8) & 255, b = c & 255;
    return (Math.round(r + (255 - r) * t) << 16) | (Math.round(g + (255 - g) * t) << 8) | Math.round(b + (255 - b) * t);
  }
  function rng(seed) { // mulberry32
    var a = (seed | 0) + 0x6d2b79f5;
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function pick(r, arr) { return arr[Math.floor(r() * arr.length) % arr.length]; }
  function lerp(a, b, k) { return a + (b - a) * k; }

  // ---- primitives ----
  function blob(g, x, y, w, h, r, fill, lw) {
    lw = lw || 2;
    g.lineStyle(lw, OL, 1, 0.5); g.beginFill(fill); g.drawRoundedRect(x, y, w, h, r); g.endFill(); g.lineStyle(0);
    var sw = w * 0.36;
    g.beginFill(shade(fill, 0.78)); g.drawRoundedRect(x + w - sw - lw * 0.5, y + lw, sw, h - lw * 2, Math.min(r, sw / 2)); g.endFill();
    g.beginFill(light(fill, 1.4), 0.85); g.drawRoundedRect(x + w * 0.16, y + h * 0.1, Math.max(1.5, w * 0.12), Math.max(2, h * 0.28), 1); g.endFill();
  }
  function ell(g, cx, cy, rx, ry, fill) {
    g.lineStyle(2, OL, 1, 0.5); g.beginFill(shade(fill, 0.78)); g.drawEllipse(cx, cy, rx, ry); g.endFill(); g.lineStyle(0);
    g.beginFill(fill); g.drawEllipse(cx - rx * 0.12, cy - ry * 0.08, rx * 0.8, ry * 0.88); g.endFill();
    g.beginFill(0xffffff, 0.35); g.drawEllipse(cx - rx * 0.38, cy - ry * 0.45, rx * 0.2, ry * 0.14); g.endFill();
  }
  function poly(g, pts, fill, lw) {
    g.lineStyle(lw === 0 ? 0 : (lw || 2), OL, 1, 0.5); g.beginFill(fill); g.drawPolygon(pts); g.endFill(); g.lineStyle(0);
  }
  function limb(P, w, len, color) {
    var c = new P.Container(), g = new P.Graphics();
    blob(g, -w / 2, -w / 2, w, len + w, w / 2, color); c.addChild(g); return c;
  }
  function line(g, pts, w, color) {
    g.lineStyle(w, color == null ? OL : color, 1, 0.5, false);
    g.moveTo(pts[0], pts[1]);
    for (var i = 2; i < pts.length; i += 2) g.lineTo(pts[i], pts[i + 1]);
    g.lineStyle(0);
  }
  function curve(g, x0, y0, cx, cy, x1, y1, w, color) {
    g.lineStyle(w, color == null ? OL : color, 1, 0.5); g.moveTo(x0, y0); g.quadraticCurveTo(cx, cy, x1, y1); g.lineStyle(0);
  }

  // ---- hiệu ứng hạt (bong bóng, hơi, khói) dùng pool ----
  function makePuffs(P, parent, n) {
    var list = [], i;
    for (i = 0; i < n; i++) {
      var g = new P.Graphics();
      g.lineStyle(1.5, 0xffffff, 0.9); g.beginFill(0xffffff, 0.25); g.drawCircle(0, 0, 4); g.endFill();
      g.beginFill(0xffffff, 0.8); g.drawCircle(-1.4, -1.4, 1); g.endFill();
      g.visible = false; parent.addChild(g);
      list.push({ g: g, age: 1, life: 1, vx: 0, vy: 0, sz: 1 });
    }
    return {
      list: list, acc: 0,
      emit: function (x, y, vx, vy, life, sz, tint) {
        for (var k = 0; k < list.length; k++) {
          var p = list[k];
          if (p.age >= p.life) {
            p.age = 0; p.life = life; p.vx = vx; p.vy = vy; p.sz = sz;
            p.g.x = x; p.g.y = y; p.g.visible = true; p.g.tint = tint == null ? 0xffffff : tint; return;
          }
        }
      },
      step: function (dt, grow, wob) {
        for (var k = 0; k < list.length; k++) {
          var p = list[k]; if (p.age >= p.life) continue;
          p.age += dt;
          if (p.age >= p.life) { p.g.visible = false; continue; }
          var u = p.age / p.life;
          p.g.x += (p.vx + Math.sin(p.age * 6 + k) * (wob || 0)) * dt; p.g.y += p.vy * dt;
          p.g.scale.set(p.sz * (1 + u * (grow || 0))); p.g.alpha = u < 0.15 ? u / 0.15 : 1 - (u - 0.15) / 0.85;
        }
      },
      clear: function () { for (var k = 0; k < list.length; k++) { list[k].age = list[k].life; list[k].g.visible = false; } }
    };
  }
  function blobPuff(P, parent, n) { // hạt tròn đặc cho khói/lửa
    var pf = makePuffs(P, parent, n);
    pf.list.forEach(function (p) { p.g.clear(); p.g.beginFill(0xffffff, 0.9); p.g.drawCircle(0, 0, 5); p.g.endFill(); });
    return pf;
  }

  // ---- thân thể làm mượt: pose hiện tại -> mục tiêu ----
  function Smoother(keys) { this.cur = {}; for (var k in keys) this.cur[k] = keys[k]; }
  Smoother.prototype.step = function (tgt, dt, rate) {
    var k = 1 - Math.exp(-dt * (rate || 12));
    for (var key in tgt) { if (this.cur[key] === undefined) this.cur[key] = tgt[key]; this.cur[key] = lerp(this.cur[key], tgt[key], k); }
    return this.cur;
  };

  function finish(root, o) {
    o = o || {};
    root.scale.set(o.scale || 1);
    if (o.x != null) root.x = o.x;
    if (o.y != null) root.y = o.y;
  }
  function mkApi(root, o, impl) {
    var facing = (o && o.facing) < 0 ? -1 : 1, sc = (o && o.scale) || 1;
    function applyFacing() { root.scale.x = facing * sc; root.scale.y = sc; }
    var api = {
      container: root, state: impl.initial,
      update: function (dt) { dt = Math.min(dt || 0, 0.1); impl.update(dt); },
      setState: function (s) { if (impl.states.indexOf(s) < 0 && !(impl.alias && impl.alias[s])) return; s = (impl.alias && impl.alias[s]) || s; if (s === api.state) return; api.state = s; impl.enter(s); },
      setFacing: function (f) { facing = f < 0 ? -1 : 1; applyFacing(); },
      destroy: function () { if (impl.onDestroy) impl.onDestroy(); if (root.parent) root.parent.removeChild(root); root.destroy({ children: true }); },
      states: impl.states
    };
    applyFacing();
    if (impl.extra) impl.extra(api);
    impl.enter(impl.initial);
    return api;
  }

  // =====================================================================
  // DIVER — Trường con thợ lặn (gốc = tâm thân, cao ~96px, hướng +x)
  // =====================================================================
  var DIVER_STATES = ["idle", "swim", "catch", "hurt", "faint", "surface"];
  function createDiver(P, o) {
    o = o || {};
    var root = new P.Container(), rig = new P.Container();
    var suit = 0x24456e, suitD = shade(suit, 0.8), stripe = 0x2ec4b6, skin = 0xeab98f, hair = 0x1d1620, fin = 0xf28c28;
    var bubbles = makePuffs(P, root, 7), spark = new P.Graphics();

    // bình dưỡng khí (sau lưng)
    var tank = new P.Graphics();
    blob(tank, -25, -34, 12, 36, 6, 0xf2b134); blob(tank, -22, -40, 6, 8, 2, 0x8c8c96);
    tank.beginFill(0x444455); tank.drawRect(-25, -22, 12, 3); tank.endFill();
    rig.addChild(tank);

    function mkLeg(color, fcolor) {
      var l = limb(P, 9, 30, color), f = new P.Container(), fg = new P.Graphics();
      poly(fg, [-4, -4, 5, -4, 13, 15, -1, 15], fcolor); // chân vịt
      fg.lineStyle(1.5, shade(fcolor, 0.7)); fg.moveTo(1, 0); fg.lineTo(6, 12); fg.lineStyle(0);
      f.addChild(fg); f.y = 29; l.addChild(f); l.fin = f; return l;
    }
    function mkArm(color) {
      var a = limb(P, 8, 23, color), h = new P.Graphics(); ell(h, 0, 0, 5, 5, skin); h.y = 25; a.addChild(h); a.hand = h; return a;
    }
    var legB = mkLeg(suitD, shade(fin, 0.8)); legB.x = -2; legB.y = 0;
    var armB = mkArm(suitD); armB.x = 0; armB.y = -26;
    rig.addChild(legB); rig.addChild(armB);

    var torso = new P.Graphics();
    blob(torso, -11, -34, 22, 40, 9, suit);
    torso.beginFill(stripe); torso.drawRoundedRect(3, -32, 4, 36, 2); torso.endFill();
    torso.beginFill(0xf2b134); torso.drawRoundedRect(-9, -30, 4, 22, 2); torso.endFill(); // dây đai bình
    torso.lineStyle(1.5, OL, 0.8); torso.moveTo(-11, 2); torso.lineTo(11, 2); torso.lineStyle(0);
    rig.addChild(torso);

    var legF = mkLeg(suit, fin); legF.x = 2; legF.y = 0; rig.addChild(legF);

    // đầu
    var head = new P.Container(); head.x = 3; head.y = -42; rig.addChild(head);
    var tail = new P.Container(); tail.x = -9; tail.y = -3; // bím tóc
    var tg = new P.Graphics();
    tg.lineStyle(2, OL, 1, 0.5); tg.beginFill(hair);
    tg.moveTo(-3, -3); tg.bezierCurveTo(-12, 4, -6, 16, -9, 26); tg.lineTo(-3, 28); tg.bezierCurveTo(1, 16, 5, 6, 3, -3); tg.closePath(); tg.endFill();
    tg.lineStyle(0); tg.beginFill(light(hair, 1.4), 0.5); tg.drawEllipse(-4, 8, 1.4, 5); tg.endFill();
    tg.beginFill(0xe53935); tg.drawRoundedRect(-5, -1, 8, 4, 2); tg.endFill();
    tail.addChild(tg); head.addChild(tail);
    var hb = new P.Graphics(); ell(hb, -4, -1, 11, 12, hair); head.addChild(hb);
    var hs = new P.Graphics(); ell(hs, 0, 0, 11, 11.5, skin);
    ell(hs, -3, 3, 3, 3.4, skin); // tai
    head.addChild(hs);
    var fr = new P.Graphics(); // tóc mái
    fr.lineStyle(2, OL, 1, 0.5); fr.beginFill(hair);
    fr.moveTo(-11, 3); fr.bezierCurveTo(-12, -16, 6, -15, 11, -4); fr.lineTo(8, -4); fr.quadraticCurveTo(0, -9, -6, -4); fr.lineTo(-9, 5); fr.closePath(); fr.endFill();
    fr.lineStyle(0); fr.beginFill(0xffffff, 0.25); fr.drawEllipse(-1, -11, 4, 1.4); fr.endFill();
    head.addChild(fr);
    var mask = new P.Graphics(); // kính lặn
    mask.lineStyle(1.5, OL, 0.9); mask.moveTo(-3, -1); mask.lineTo(-12, 0); mask.lineStyle(0);
    mask.lineStyle(2, OL, 1, 0.5); mask.beginFill(0xffd23f); mask.drawRoundedRect(-1, -7, 16, 13, 5); mask.endFill(); mask.lineStyle(0);
    mask.beginFill(0x6fd6ff, 0.9); mask.drawRoundedRect(1, -5, 12, 9, 3.5); mask.endFill();
    mask.beginFill(0xffffff, 0.55); mask.drawRoundedRect(2.5, -4, 3, 4, 1.5); mask.endFill();
    head.addChild(mask);
    var face = new P.Graphics(); head.addChild(face);

    var armF = mkArm(suit); armF.x = 0; armF.y = -26; rig.addChild(armF);
    var fish = new P.Graphics(); // cá bắt được
    poly(fish, [-9, 0, -2, -5, 6, -4, 11, 0, 6, 4, -2, 5], 0xffb74d); poly(fish, [-9, 0, -15, -5, -15, 5], 0xff8a3d);
    fish.beginFill(OL); fish.drawCircle(5, -1, 1.1); fish.endFill();
    fish.beginFill(0xffffff, 0.5); fish.drawEllipse(-1, -2.5, 4, 1); fish.endFill();
    fish.y = 27; fish.rotation = 1.2; fish.visible = false; armF.addChild(fish);
    root.addChild(rig); root.addChild(spark);
    spark.visible = false;
    (function () { // lấp lánh
      for (var i = 0; i < 4; i++) { var a = i * Math.PI / 2; spark.lineStyle(2, 0xfff59d, 1); spark.moveTo(Math.cos(a) * 3, Math.sin(a) * 3); spark.lineTo(Math.cos(a) * 9, Math.sin(a) * 9); }
    })();
    var hurtF = P.ColorMatrixFilter ? new P.ColorMatrixFilter() : null;
    if (hurtF) hurtF.matrix = [1.15,0.1,0,0,0.08, 0,0.7,0,0,0, 0,0,0.7,0,0, 0,0,0,1,0];

    function drawFace(s) {
      face.clear();
      var ex = 7.5, ey = -0.5;
      var dead = s === "faint", ouch = s === "hurt", happy = s === "catch" || s === "surface";
      if (dead) { line(face, [ex - 3, ey - 3, ex + 3, ey + 3], 2); line(face, [ex + 3, ey - 3, ex - 3, ey + 3], 2); }
      else if (ouch) { curve(face, ex - 3, ey + 2, ex, ey - 3, ex + 3, ey + 2, 2); }
      else if (happy) { curve(face, ex - 3.5, ey + 2, ex, ey - 3, ex + 3.5, ey + 2, 2); }
      else { face.beginFill(OL); face.drawEllipse(ex, ey, 2.4, 3.2); face.endFill(); face.beginFill(0xffffff); face.drawCircle(ex - 0.8, ey - 1.2, 1); face.endFill(); }
      // lông mày phía trên kính
      face.lineStyle(2, OL); if (ouch) { face.moveTo(2, -10); face.lineTo(11, -8); } else if (dead) { face.moveTo(3, -9); face.lineTo(11, -9.5); } else { face.moveTo(3, -9.5); face.lineTo(11, happy ? -11 : -9.5); } face.lineStyle(0);
      // miệng
      var mx = 8, my = 9;
      if (ouch) { face.lineStyle(2, OL); face.beginFill(0x8a2d3a); face.drawEllipse(mx, my, 2.6, 3); face.endFill(); face.lineStyle(0); }
      else if (dead) { line(face, [mx - 3, my + 1, mx + 3, my + 1], 2); }
      else if (happy) { face.lineStyle(2, OL); face.beginFill(0x8a2d3a); face.moveTo(mx - 4, my - 1); face.quadraticCurveTo(mx, my + 7, mx + 4, my - 1); face.closePath(); face.endFill(); face.lineStyle(0); }
      else { curve(face, mx - 3, my, mx, my + 3, mx + 3, my, 2); }
      if (happy) { face.beginFill(0xff8a80, 0.55); face.drawEllipse(10, 7, 2.6, 1.6); face.endFill(); }
    }

    var sm = new Smoother({ rot: 0, y: 0, x: 0, aF: -0.2, aB: 0.3, lF: 0.1, lB: 0.1, fF: 0, fB: 0, hair: 0, head: 0 });
    var t = Math.random() * 10, state = "idle", emitAcc = 0;

    function target(s) {
      var S = Math.sin;
      switch (s) {
        case "swim": return { rot: 1.22 + S(t * 5) * 0.05, y: S(t * 5) * 1.5, x: 0, aF: 0.3 + S(t * 5) * 0.6, aB: 0.3 - S(t * 5) * 0.6, lF: 0.12 + S(t * 10) * 0.5, lB: 0.12 - S(t * 10) * 0.5, fF: S(t * 10 - 1) * 0.35, fB: -S(t * 10 - 1) * 0.35, hair: S(t * 7) * 0.22, head: -0.12 };
        case "catch": return { rot: 0.3 + S(t * 6) * 0.04, y: S(t * 4) * 2, x: 0, aF: -2.3 + S(t * 9) * 0.12, aB: 0.9, lF: 0.15 + S(t * 7) * 0.35, lB: 0.1 - S(t * 7) * 0.35, fF: S(t * 7) * 0.3, fB: 0, hair: S(t * 5) * 0.25, head: -0.1 };
        case "hurt": return { rot: -0.3 + S(t * 40) * 0.08, y: 0, x: S(t * 55) * 2.5, aF: -2.7 + S(t * 25) * 0.35, aB: 2.5 - S(t * 25) * 0.35, lF: S(t * 22) * 0.55, lB: -S(t * 22) * 0.55, fF: 0.2, fB: -0.2, hair: S(t * 30) * 0.4, head: 0.25 };
        case "faint": return { rot: 1.8 + S(t * 0.9) * 0.06, y: S(t * 0.9) * 5, x: 0, aF: 0.75 + S(t * 1.1) * 0.2, aB: 1.0 + S(t * 1.3) * 0.2, lF: 0.35 + S(t * 1) * 0.1, lB: 0.55 + S(t * 1.2) * 0.1, fF: 0.3, fB: 0.4, hair: S(t * 1.4) * 0.15 + 0.1, head: 0.3 };
        case "surface": return { rot: 0.05, y: S(t * 2) * 2.5, x: 0, aF: -2.7 + S(t * 6) * 0.35, aB: 0.35, lF: 0.15 + S(t * 3) * 0.12, lB: -S(t * 3) * 0.12, fF: S(t * 3) * 0.2, fB: 0, hair: S(t * 2) * 0.1, head: -0.05 };
        default: return { rot: 0.08 + S(t * 1.5) * 0.05, y: S(t * 1.6) * 2.5, x: 0, aF: -0.2 + S(t * 1.5 + 1) * 0.12, aB: 0.3 + S(t * 1.5) * 0.1, lF: 0.06 + S(t * 1.5) * 0.08, lB: -0.05 - S(t * 1.5) * 0.08, fF: 0.1, fB: -0.1, hair: S(t * 1.5) * 0.1, head: 0 };
      }
    }
    var impl = {
      initial: "idle", states: DIVER_STATES, alias: { float: "faint" },
      enter: function (s) {
        state = s; drawFace(s);
        fish.visible = s === "catch"; spark.visible = s === "catch";
        rig.filters = s === "hurt" && hurtF ? [hurtF] : null;
        if (s === "surface") bubbles.clear();
      },
      update: function (dt) {
        t += dt;
        var p = sm.step(target(state), dt, state === "hurt" ? 25 : 10);
        rig.rotation = p.rot; rig.y = p.y; rig.x = p.x;
        armF.rotation = p.aF; armB.rotation = p.aB; legF.rotation = p.lF; legB.rotation = p.lB;
        legF.fin.rotation = p.fF; legB.fin.rotation = p.fB; tail.rotation = p.hair; head.rotation = p.head;
        if (state === "catch") { spark.x = 22; spark.y = -46 + Math.sin(t * 8) * 2; spark.rotation = t * 3; spark.scale.set(0.8 + Math.sin(t * 10) * 0.2); }
        // bong bóng từ van bình
        var rate = state === "swim" ? 7 : state === "hurt" ? 14 : state === "faint" ? 1.3 : state === "surface" ? 0 : 2.6;
        emitAcc += dt * rate;
        while (emitAcc >= 1) {
          emitAcc -= 1;
          var c = Math.cos(p.rot), sn = Math.sin(p.rot), lx = -19, ly = -42;
          bubbles.emit(rig.x + lx * c - ly * sn, rig.y + lx * sn + ly * c, (Math.random() - 0.5) * 8, -22 - Math.random() * 16, 1.4 + Math.random() * 0.8, 0.5 + Math.random() * 0.7);
        }
        bubbles.step(dt, 0.4, 5);
      }
    };
    finish(root, o);
    return mkApi(root, o, impl);
  }

  // =====================================================================
  // Đầu nhìn thẳng (customer / chef)
  // =====================================================================
  var SKINS = [0xf2cba3, 0xe4b085, 0xcf9467, 0xa9714a, 0x8b573a];
  var HAIRS = [0x1c1620, 0x2c1d17, 0x4a3020, 0xb9b9c4, 0xe9e9ee];
  var CLOTH = [0x7a5a3c, 0x2f5d62, 0x5c8a4d, 0xb5523b, 0x6a4c93, 0x2b2b33, 0xc9a227, 0x3d6aa8];
  var NON = [0xe8d08a, 0xdcc277, 0xf0dc9c];
  var KHAN = [[0x2e7d5b, 0xffffff], [0xc62828, 0xffffff], [0x2e7d5b, 0xf2f2e8]];

  function buildHead(P, sp) {
    var h = new P.Container(), skin = sp.skin, hairC = sp.hair;
    var back = new P.Graphics();
    if (sp.hairStyle === "long") { blob(back, -16, -6, 32, 34, 12, hairC); }
    if (sp.hairStyle === "bun") { ell(back, 0, -17, 7, 6.5, hairC); }
    h.addChild(back);
    var s = new P.Graphics();
    ell(s, -13.5, 2, 3.2, 4, skin); ell(s, 13.5, 2, 3.2, 4, skin);
    ell(s, 0, 0, 14, 14.5, skin);
    s.beginFill(0xff8a80, 0.0); s.endFill();
    h.addChild(s);
    var f = new P.Graphics();
    if (sp.hairStyle !== "bald") {
      var top = sp.hairStyle === "slick" ? -15 : -17;
      f.lineStyle(2, OL, 1, 0.5); f.beginFill(hairC);
      f.moveTo(-14, 2); f.bezierCurveTo(-18, top - 2, 18, top - 2, 14, 2); f.quadraticCurveTo(10, -9, 4, -8.5); f.quadraticCurveTo(-2, -10, -8, -6); f.quadraticCurveTo(-12, -2, -14, 2);
      f.closePath(); f.endFill(); f.lineStyle(0);
      f.beginFill(0xffffff, 0.22); f.drawEllipse(-4, top + 3, 5, 1.6); f.endFill();
    } else {
      f.beginFill(hairC); f.drawEllipse(-13, -3, 2.5, 5); f.drawEllipse(13, -3, 2.5, 5); f.endFill();
    }
    h.addChild(f);
    if (sp.beard) { var b = new P.Graphics(); b.lineStyle(2, OL, 1, 0.5); b.beginFill(hairC); b.moveTo(-13, 3); b.quadraticCurveTo(-12, 20, 0, 21); b.quadraticCurveTo(12, 20, 13, 3); b.quadraticCurveTo(8, 9, 0, 9); b.quadraticCurveTo(-8, 9, -13, 3); b.closePath(); b.endFill(); h.addChild(b); }
    if (sp.hat === "non") {
      var hat = new P.Graphics(), hc = sp.nonColor;
      hat.lineStyle(2, 0xb02a37, 1, 0.5); hat.moveTo(-12, -8); hat.lineTo(-10, 12); hat.moveTo(12, -8); hat.lineTo(10, 12); hat.lineStyle(0);
      h.addChild(hat);
      var cone = new P.Graphics();
      cone.lineStyle(2, OL, 1, 0.5); cone.beginFill(hc); cone.drawPolygon([-32, -9, 0, -36, 32, -9]); cone.endFill();
      cone.beginFill(shade(hc, 0.82)); cone.drawPolygon([2, -34, 31, -10, 8, -10]); cone.endFill();
      cone.lineStyle(0); cone.beginFill(hc); cone.lineStyle(2, OL, 1, 0.5); cone.drawEllipse(0, -9, 32, 5); cone.endFill(); cone.lineStyle(0);
      cone.lineStyle(1, shade(hc, 0.65), 0.8); for (var i = -4; i <= 4; i++) { cone.moveTo(i * 2, -34 + Math.abs(i) * 0.3); cone.lineTo(i * 7, -9); } cone.lineStyle(0);
      cone.beginFill(0xb02a37); cone.drawEllipse(0, -6.5, 30, 1.8); cone.endFill();
      cone.beginFill(0xffffff, 0.35); cone.drawEllipse(-8, -22, 4, 1.4); cone.endFill();
      h.addChild(cone);
    } else if (sp.hat === "khan") {
      var k = sp.khan, kc = new P.Graphics();
      kc.lineStyle(2, OL, 1, 0.5); kc.beginFill(k[1]); kc.moveTo(-15, -2); kc.bezierCurveTo(-16, -22, 16, -22, 15, -2); kc.quadraticCurveTo(0, -11, -15, -2); kc.closePath(); kc.endFill(); kc.lineStyle(0);
      kc.lineStyle(1.5, k[0], 0.85); for (var q = -12; q <= 12; q += 5) { kc.moveTo(q, -17); kc.lineTo(q * 1.05, -4); } for (var r = -16; r <= -6; r += 4) { kc.moveTo(-14, r); kc.lineTo(14, r); } kc.lineStyle(0);
      kc.lineStyle(2, OL, 1, 0.5); kc.beginFill(k[1]); kc.drawPolygon([14, -9, 24, -14, 22, -2, 26, 4, 14, -3]); kc.endFill(); kc.lineStyle(0); // nút khăn
      kc.beginFill(k[0], 0.8); kc.drawRect(18, -8, 3, 3); kc.endFill();
      h.addChild(kc);
    }
    var eyes = new P.Graphics(), mouth = new P.Graphics(), extra = new P.Graphics();
    h.addChild(eyes); h.addChild(mouth); h.addChild(extra);
    if (sp.mustache) { var m = new P.Graphics(); m.beginFill(hairC); m.lineStyle(1.5, OL); m.moveTo(0, 5); m.quadraticCurveTo(-8, 2, -10, 7); m.quadraticCurveTo(-4, 6, 0, 7.5); m.quadraticCurveTo(4, 6, 10, 7); m.quadraticCurveTo(8, 2, 0, 5); m.endFill(); h.addChild(m); }
    if (sp.glasses) { var gl = new P.Graphics(); gl.lineStyle(1.8, 0x333344); gl.drawCircle(-5.5, -1, 4.6); gl.drawCircle(5.5, -1, 4.6); gl.moveTo(-1, -1); gl.lineTo(1, -1); gl.lineStyle(0); gl.beginFill(0xbfe9ff, 0.28); gl.drawCircle(-5.5, -1, 4.4); gl.drawCircle(5.5, -1, 4.4); gl.endFill(); h.addChild(gl); }
    h.eyes = eyes; h.mouth = mouth; h.extra = extra; h.skin = skin;
    return h;
  }
  function eyeDot(g, x, y, r) { g.beginFill(OL); g.drawEllipse(x, y, r, r * 1.3); g.endFill(); g.beginFill(0xffffff); g.drawCircle(x - r * 0.35, y - r * 0.6, r * 0.42); g.endFill(); }
  function brow(g, x0, y0, x1, y1) { line(g, [x0, y0, x1, y1], 2.4, 0x2a1d1a); }
  function drawFaceFront(h, kind) {
    var e = h.eyes, m = h.mouth, x = h.extra; e.clear(); m.clear(); x.clear();
    var ey = -0.5;
    switch (kind) {
      case "angry":
        eyeDot(e, -5.5, ey + 1, 2.1); eyeDot(e, 5.5, ey + 1, 2.1);
        brow(e, -10, -7.5, -2, -3.5); brow(e, 10, -7.5, 2, -3.5);
        m.lineStyle(2, OL); m.beginFill(0x7a1f2b); m.moveTo(-5, 10); m.quadraticCurveTo(0, 4, 5, 10); m.quadraticCurveTo(0, 8, -5, 10); m.closePath(); m.endFill(); m.lineStyle(0);
        m.beginFill(0xffffff); m.drawRect(-3, 8, 6, 1.4); m.endFill();
        x.beginFill(0xff5252, 0.5); x.drawEllipse(-9, 5, 3.4, 2.2); x.drawEllipse(9, 5, 3.4, 2.2); x.endFill();
        break;
      case "impatient":
        eyeDot(e, -5.5, ey, 2); eyeDot(e, 5.5, ey, 2);
        e.beginFill(h.skin); e.drawRect(-9, ey - 4, 7, 3.4); e.drawRect(2, ey - 4, 7, 3.4); e.endFill(); // mí mắt nặng
        line(e, [-9, ey - 0.6, -2, ey - 0.6], 2); line(e, [2, ey - 0.6, 9, ey - 0.6], 2);
        brow(e, -10, -6.5, -2, -6.8); brow(e, 2, -8.5, 10, -7);
        curve(m, -4, 9, -1, 7, 1, 8.5, 2); curve(m, 1, 8.5, 3, 10, 5, 8, 2);
        x.beginFill(0x7fd4ff); x.lineStyle(1.2, OL); x.moveTo(15, -12); x.quadraticCurveTo(19, -5, 15, -3); x.quadraticCurveTo(11, -5, 15, -12); x.endFill(); x.lineStyle(0); // giọt mồ hôi
        break;
      case "happy": case "eating":
        curve(e, -8.5, ey + 1, -5.5, ey - 4, -2.5, ey + 1, 2.2); curve(e, 2.5, ey + 1, 5.5, ey - 4, 8.5, ey + 1, 2.2);
        brow(e, -10, -7, -3, -8); brow(e, 3, -8, 10, -7);
        m.lineStyle(2, OL); m.beginFill(0x8a2d3a); m.moveTo(-6, 6); m.quadraticCurveTo(0, 15, 6, 6); m.closePath(); m.endFill(); m.lineStyle(0);
        m.beginFill(0xff8a8a); m.drawEllipse(0, 9.5, 3, 1.6); m.endFill();
        x.beginFill(0xff8a80, 0.55); x.drawEllipse(-10, 5, 3.6, 2.2); x.drawEllipse(10, 5, 3.6, 2.2); x.endFill();
        break;
      case "panic":
        e.lineStyle(2, OL); e.beginFill(0xffffff); e.drawCircle(-5.5, ey, 4.4); e.drawCircle(5.5, ey, 4.4); e.endFill(); e.lineStyle(0);
        e.beginFill(OL); e.drawCircle(-5.5, ey, 1.6); e.drawCircle(5.5, ey, 1.6); e.endFill();
        brow(e, -10, -8, -2, -10.5); brow(e, 10, -8, 2, -10.5);
        m.lineStyle(2, OL); m.beginFill(0x7a1f2b); m.drawEllipse(0, 9, 4, 5); m.endFill(); m.lineStyle(0);
        x.beginFill(0xff5252, 0.55); x.drawEllipse(-9, 5, 3.6, 2.2); x.drawEllipse(9, 5, 3.6, 2.2); x.endFill();
        break;
      case "cook":
        eyeDot(e, -5.5, ey, 2.1); eyeDot(e, 5.5, ey, 2.1);
        brow(e, -10, -6.5, -2, -7.5); brow(e, 10, -6.5, 2, -7.5);
        curve(m, -4, 8, 0, 11, 4, 8, 2);
        x.beginFill(0x7fd4ff); x.lineStyle(1.2, OL); x.moveTo(-15, -9); x.quadraticCurveTo(-11, -3, -15, -1); x.quadraticCurveTo(-19, -3, -15, -9); x.endFill(); x.lineStyle(0);
        break;
      default: // calm / idle
        eyeDot(e, -5.5, ey, 2.1); eyeDot(e, 5.5, ey, 2.1);
        brow(e, -10, -7, -3, -7.5); brow(e, 3, -7.5, 10, -7);
        curve(m, -4, 8, 0, 11, 4, 8, 2);
    }
  }

  // =====================================================================
  // CUSTOMER — ngồi nhìn trước, gốc = giữa ghế, y=0 là mặt bàn
  // =====================================================================
  var MOODS = ["calm", "impatient", "angry", "happy"];
  var CUST_STATES = ["calm", "impatient", "angry", "happy", "eating"];
  function createCustomer(P, o) {
    o = o || {};
    var r = rng(Math.imul((o.seed == null ? 1 : o.seed) + 1, 2654435761) >>> 0); r(); r(); r();
    var sp = {
      skin: pick(r, SKINS), hair: pick(r, HAIRS), hairStyle: pick(r, ["short", "short", "long", "bun", "bald", "slick"]),
      hat: pick(r, ["non", "none", "khan", "none", "khan"]), nonColor: pick(r, NON), khan: pick(r, KHAN),
      beard: false, mustache: false, glasses: r() < 0.25
    };
    var cloth = pick(r, CLOTH), scarf = r() < 0.4, old = r() < 0.3;
    if (old) sp.hair = r() < 0.5 ? HAIRS[3] : HAIRS[4];
    if (sp.hairStyle === "bald") { sp.beard = r() < 0.6; if (sp.hat !== "none") sp.hat = "none"; }
    if (sp.hairStyle === "long" && sp.hat === "khan") sp.hat = "non";
    if (sp.hairStyle === "bun" && sp.hat !== "none") sp.hat = "none";
    if (sp.hairStyle === "slick" || (sp.hairStyle === "short" && r() < 0.4)) sp.mustache = r() < 0.6;
    if (sp.hairStyle === "long" || sp.hairStyle === "bun") sp.mustache = false;
    var wide = 0.9 + r() * 0.25; // thân to nhỏ khác nhau

    var root = new P.Container(), body = new P.Container(); root.addChild(body);
    var tw = 38 * wide;
    var torso = new P.Graphics();
    blob(torso, -tw / 2, -48, tw, 50, 14, cloth);
    torso.lineStyle(2, OL, 1, 0.5); torso.beginFill(sp.skin); torso.drawPolygon([-7, -48, 7, -48, 0, -34]); torso.endFill(); torso.lineStyle(0); // cổ chữ V áo bà ba
    torso.beginFill(light(cloth, 1.5), 0.9); for (var b = 0; b < 3; b++) torso.drawCircle(0, -30 + b * 9, 1.8); torso.endFill();
    torso.lineStyle(1.5, shade(cloth, 0.6)); torso.moveTo(0, -34); torso.lineTo(0, 0); torso.lineStyle(0);
    torso.lineStyle(1.5, shade(cloth, 0.6)); torso.drawRoundedRect(-tw / 2 + 5, -18, 9, 9, 2); torso.lineStyle(0);
    if (scarf) { var sk = sp.khan; torso.lineStyle(2, OL, 1, 0.5); torso.beginFill(sk[1]); torso.drawPolygon([-10, -50, 10, -50, 8, -42, 0, -35, -8, -42]); torso.endFill(); torso.lineStyle(1.2, sk[0]); for (var s2 = -8; s2 <= 8; s2 += 4) { torso.moveTo(s2, -49); torso.lineTo(s2 * 0.6, -40); } torso.lineStyle(0); }
    body.addChild(torso);

    function mkArm(side) {
      var a = limb(P, 10, 24, cloth), hnd = new P.Graphics(); ell(hnd, 0, 0, 5.6, 5.6, sp.skin); hnd.y = 26; a.addChild(hnd);
      a.x = side * (tw / 2 - 3); a.y = -41; a.baseRot = side * -0.5; a.side = side; a.rotation = a.baseRot; return a;
    }
    var armL = mkArm(-1), armR = mkArm(1);
    body.addChild(armL); body.addChild(armR);
    var head = buildHead(P, sp); head.y = -62; body.addChild(head);
    // hiệu ứng: hơi giận / thở dài
    var fx = makePuffs(P, root, 4), steam = blobPuff(P, root, 5);
    var mood = "calm", eating = false, t = (o.seed || 0) * 0.7, chewT = 0, tap = 0;

    var impl = {
      initial: MOODS.indexOf(o.mood) >= 0 ? o.mood : "calm", states: CUST_STATES,
      alias: { idle: "calm", impatient: "impatient", waiting: "calm", served: "happy", eat: "eating" },
      enter: function (s) {
        eating = s === "eating"; mood = eating ? "happy" : s;
        drawFaceFront(head, s);
        if (s !== "angry") steam.clear();
      },
      update: function (dt) {
        t += dt;
        var breath = Math.sin(t * 2) * 0.8;
        body.scale.y = 1 + breath * 0.008; head.y = -62 + breath * 0.5; head.rotation = 0;
        var ar = armR, al = armL;
        al.rotation = lerp(al.rotation, al.baseRot, 0.2); ar.rotation = lerp(ar.rotation, ar.baseRot, 0.2);
        body.x = 0; body.y = 0;
        if (mood === "impatient") {
          tap += dt * 7; ar.rotation = ar.baseRot + Math.max(0, Math.sin(tap)) * 0.22; head.rotation = Math.sin(t * 1.3) * 0.06;
          if (Math.random() < dt * 0.4) fx.emit(-14, -78, -10, -14, 1.4, 0.9, 0xdddddd); // thở dài
        } else if (mood === "angry") {
          body.x = Math.sin(t * 38) * 0.9; head.rotation = Math.sin(t * 30) * 0.03;
          ar.rotation = ar.baseRot + Math.sin(t * 20) * 0.1; al.rotation = al.baseRot - Math.sin(t * 20) * 0.1;
          if (Math.random() < dt * 4) steam.emit(Math.random() < 0.5 ? -18 : 18, -84, (Math.random() - 0.5) * 10, -30, 0.9, 0.8, 0xffe0e0);
        } else if (mood === "happy") {
          body.y = -Math.abs(Math.sin(t * 5)) * (eating ? 0.8 : 2.2); head.rotation = Math.sin(t * 5) * 0.05;
        }
        if (eating) { // và cơm
          chewT += dt * 6; var up = (Math.sin(chewT) + 1) / 2;
          ar.rotation = ar.baseRot + (1.9 - ar.baseRot) * up * 0.6; head.rotation = Math.sin(chewT * 2) * 0.04;
          var open = Math.sin(chewT * 2) > 0;
          head.mouth.scale.y = open ? 1.0 : 0.55;
          head.mouth.pivot.y = 8; head.mouth.y = 8;
        } else { head.mouth.scale.y = 1; head.mouth.y = 0; head.mouth.pivot.y = 0; }
        fx.step(dt, 0.6, 3); steam.step(dt, 1.1, 2);
      }
    };
    finish(root, o);
    var api = mkApi(root, o, impl);
    api.setMood = function (m) { api.setState(m); };
    api.seedInfo = sp;
    return api;
  }

  // =====================================================================
  // CHEF — đầu bếp, nhìn trước, gốc = giữa chân (y=0 sàn), cao ~96px
  // =====================================================================
  var CHEF_STATES = ["idle", "cook", "burn"];
  function createChef(P, o) {
    o = o || {};
    var r = rng(o.seed == null ? 7 : o.seed);
    var sp = { skin: 0xdfa579, hair: 0x1c1620, hairStyle: "short", hat: "khan", khan: [0xc62828, 0xffffff], mustache: true, glasses: false };
    var root = new P.Container(), body = new P.Container(); root.addChild(body);
    var pants = 0x2b2b3a, shirt = 0xe8dcc0, apron = 0x3d7fb5;
    var legs = new P.Graphics();
    blob(legs, -14, -34, 12, 34, 5, pants); blob(legs, 2, -34, 12, 34, 5, pants);
    blob(legs, -17, -6, 16, 7, 3, 0x4a3a30); blob(legs, 1, -6, 16, 7, 3, 0x4a3a30);
    body.addChild(legs);
    var torso = new P.Graphics();
    blob(torso, -21, -64, 42, 38, 15, shirt);
    torso.lineStyle(2, OL, 1, 0.5); torso.beginFill(apron); torso.drawPolygon([-15, -58, 15, -58, 17, -28, -17, -28]); torso.endFill(); torso.lineStyle(0);
    torso.beginFill(shade(apron, 0.8)); torso.drawPolygon([6, -58, 15, -58, 17, -28, 8, -28]); torso.endFill();
    torso.lineStyle(1.8, OL, 0.9); torso.drawRoundedRect(-9, -46, 18, 11, 3); torso.lineStyle(0);
    torso.beginFill(0xffffff, 0.3); torso.drawRect(-12, -56, 3, 8); torso.endFill();
    torso.lineStyle(2.5, 0xf2f2e8); torso.moveTo(-9, -60); torso.lineTo(-18, -48); torso.moveTo(9, -60); torso.lineTo(18, -48); torso.lineStyle(0); // dây yếm
    // khăn rằn vắt vai
    torso.lineStyle(2, OL, 1, 0.5); torso.beginFill(0xffffff); torso.drawPolygon([-21, -62, -10, -66, 0, -58, -4, -50, -16, -50, -24, -54]); torso.endFill(); torso.lineStyle(0);
    torso.lineStyle(1.3, 0xc62828); torso.moveTo(-17, -64); torso.lineTo(-18, -51); torso.moveTo(-11, -64); torso.lineTo(-9, -52); torso.moveTo(-23, -58); torso.lineTo(-5, -56); torso.lineStyle(0);
    body.addChild(torso);

    function mkArm(side) {
      var a = limb(P, 11, 22, shirt), hnd = new P.Graphics(); ell(hnd, 0, 0, 6, 6, sp.skin); hnd.y = 24; a.addChild(hnd);
      a.x = side * 20; a.y = -58; a.rotation = side * -0.3; return a;
    }
    var armL = mkArm(-1), armR = mkArm(1);
    var ladle = new P.Container(), lg = new P.Graphics();
    lg.lineStyle(3, 0x6b4a2f); lg.moveTo(0, 6); lg.lineTo(0, 38); lg.lineStyle(0);
    ell(lg, 0, 42, 8, 6, 0xb0b4bd); lg.y = 24; ladle.addChild(lg); armR.addChild(ladle);
    body.addChild(armL); body.addChild(armR);
    var head = buildHead(P, sp); head.y = -78; body.addChild(head);
    var fx = blobPuff(P, root, 8);
    var state = "idle", t = 0, smoke = 0;
    var sm = new Smoother({ aL: 0.3, aR: 0.3, lad: 0, lb: 2.9, bx: 0, by: 0 });

    var impl = {
      initial: "idle", states: CHEF_STATES,
      enter: function (s) { state = s; drawFaceFront(head, s === "idle" ? "calm" : s === "cook" ? "cook" : "panic"); fx.clear(); },
      update: function (dt) {
        t += dt;
        var S = Math.sin, tg;
        if (state === "cook") tg = { aL: -0.7 + S(t * 4) * 0.08, aR: -0.9 + S(t * 9) * 0.55, lad: S(t * 9 + 1.5) * 0.35, lb: -2.4, bx: S(t * 9) * 1.2, by: -Math.abs(S(t * 4.5)) * 1.2 };
        else if (state === "burn") tg = { aL: -2.7 + S(t * 14) * 0.3, aR: -2.7 - S(t * 14) * 0.3, lad: S(t * 14) * 0.5, lb: -0.6, bx: S(t * 33) * 1.5, by: -Math.abs(S(t * 8)) * 2.5 };
        else tg = { aL: 0.25 + S(t * 1.6) * 0.04, aR: 0.25 - S(t * 1.6) * 0.04, lad: 0.1, lb: 2.9, bx: 0, by: S(t * 2) * 0.7 };
        var p = sm.step(tg, dt, 14);
        armL.rotation = p.aL; armR.rotation = p.aR; ladle.rotation = p.lb + p.lad;
        body.x = p.bx; body.y = p.by * 0.6; head.rotation = state === "burn" ? S(t * 20) * 0.08 : S(t * 1.6) * 0.02;
        if (state === "cook" && Math.random() < dt * 7) fx.emit(-8 + Math.random() * 16, -102, (Math.random() - 0.5) * 6, -24, 1.1, 0.8, 0xffffff);
        if (state === "burn") {
          smoke += dt * 14;
          while (smoke >= 1) { smoke -= 1; var fire = Math.random() < 0.45; fx.emit(-16 + Math.random() * 32, fire ? -40 : -110, (Math.random() - 0.5) * 14, fire ? -34 : -26, fire ? 0.5 : 1.2, fire ? 0.9 : 1.1, fire ? (Math.random() < 0.5 ? 0xff7a1a : 0xffc233) : 0x34343c); }
        }
        fx.step(dt, state === "burn" ? 1.4 : 0.8, 3);
      }
    };
    finish(root, o);
    return mkApi(root, o, impl);
  }

  // =====================================================================
  // WAITER — Trường con bưng món (nhìn ngang, hướng +x, gốc = giữa chân, cao ~98px)
  // =====================================================================
  var WAIT_STATES = ["idle", "walk", "carry", "carryIdle", "serve"];
  function createWaiter(P, o) {
    o = o || {};
    var root = new P.Container(), body = new P.Container(); root.addChild(body);
    var skin = 0xeab98f, shirt = 0xc99a3c, pants = 0x2b2b33, hair = 0x1d1620;
    function mkLeg(c) { var l = limb(P, 10, 26, c); var f = new P.Graphics(); blob(f, -4, 24, 16, 7, 3.5, c === pants ? 0xe8e0d0 : shade(0xe8e0d0, 0.8)); l.addChild(f); return l; }
    var legB = mkLeg(shade(pants, 0.8)); legB.x = -2; legB.y = -32;
    var armB = limb(P, 8, 20, shade(shirt, 0.8)); armB.x = 0; armB.y = -58;
    body.addChild(legB); body.addChild(armB);
    var torso = new P.Graphics();
    blob(torso, -12, -64, 24, 36, 10, shirt);
    torso.lineStyle(1.5, shade(shirt, 0.6)); torso.moveTo(4, -62); torso.lineTo(4, -30); torso.lineStyle(0);
    torso.beginFill(light(shirt, 1.5)); torso.drawCircle(4, -54, 1.6); torso.drawCircle(4, -45, 1.6); torso.drawCircle(4, -36, 1.6); torso.endFill();
    torso.lineStyle(2, OL, 1, 0.5); torso.beginFill(0xffffff); torso.drawPolygon([-12, -62, -2, -64, 6, -58, 0, -52, -10, -54]); torso.endFill(); torso.lineStyle(0); // khăn rằn
    torso.lineStyle(1.2, 0x2e7d5b); torso.moveTo(-9, -62); torso.lineTo(-8, -54); torso.moveTo(-3, -63); torso.lineTo(-3, -54); torso.moveTo(-11, -58); torso.lineTo(4, -57); torso.lineStyle(0);
    torso.lineStyle(2, OL, 1, 0.5); torso.beginFill(0xf6d365); torso.drawRoundedRect(-13, -36, 26, 8, 3); torso.endFill(); torso.lineStyle(0); // tạp dề ngắn
    body.addChild(torso);
    var legF = mkLeg(pants); legF.x = 2; legF.y = -32; body.addChild(legF);
    var head = new P.Container(); head.x = 2; head.y = -76; body.addChild(head);
    var tail = new P.Container(); tail.x = -9; tail.y = -3; var tg = new P.Graphics();
    tg.lineStyle(2, OL, 1, 0.5); tg.beginFill(hair); tg.moveTo(-3, -3); tg.bezierCurveTo(-12, 6, -7, 20, -9, 34); tg.lineTo(-2, 36); tg.bezierCurveTo(2, 20, 5, 8, 3, -3); tg.closePath(); tg.endFill(); tg.lineStyle(0);
    tg.beginFill(0xe53935); tg.drawRoundedRect(-5, -1, 8, 4, 2); tg.endFill(); tail.addChild(tg); head.addChild(tail);
    var hb = new P.Graphics(); ell(hb, -4, -1, 11, 12, hair); head.addChild(hb);
    var hs = new P.Graphics(); ell(hs, 0, 0, 11, 11.5, skin); ell(hs, -3, 3, 3, 3.4, skin); head.addChild(hs);
    var fr = new P.Graphics(); fr.lineStyle(2, OL, 1, 0.5); fr.beginFill(hair);
    fr.moveTo(-11, 3); fr.bezierCurveTo(-12, -16, 6, -15, 11, -4); fr.lineTo(8, -5); fr.quadraticCurveTo(0, -9, -6, -4); fr.lineTo(-9, 5); fr.closePath(); fr.endFill(); head.addChild(fr);
    var hat = new P.Graphics(), hc = 0xe8d08a;
    hat.lineStyle(2, OL, 1, 0.5); hat.beginFill(hc); hat.drawPolygon([-30, -9, 0, -34, 30, -9]); hat.endFill();
    hat.beginFill(shade(hc, 0.82)); hat.drawPolygon([2, -32, 29, -10, 8, -10]); hat.endFill();
    hat.beginFill(hc); hat.drawEllipse(0, -9, 30, 5); hat.endFill(); hat.lineStyle(0);
    hat.lineStyle(1, shade(hc, 0.65), 0.8); for (var i = -4; i <= 4; i++) { hat.moveTo(i * 2, -32 + Math.abs(i) * 0.3); hat.lineTo(i * 6.5, -9); } hat.lineStyle(0);
    hat.beginFill(0xb02a37); hat.drawEllipse(0, -6.5, 28, 1.8); hat.endFill();
    hat.beginFill(0xffffff, 0.35); hat.drawEllipse(-8, -21, 4, 1.4); hat.endFill();
    head.addChild(hat);
    var face = new P.Graphics(); head.addChild(face);
    function drawFace(s) {
      face.clear();
      var carrying = s === "carry" || s === "carryIdle";
      face.beginFill(OL); face.drawEllipse(5.5, 0, 2.1, 3); face.endFill(); face.beginFill(0xffffff); face.drawCircle(4.8, -1.2, 0.9); face.endFill();
      line(face, [2, carrying ? -7 : -7.5, 10, carrying ? -6.6 : -8], 2);
      if (s === "serve") { face.lineStyle(2, OL); face.beginFill(0x8a2d3a); face.moveTo(3, 6); face.quadraticCurveTo(7, 14, 11, 6); face.closePath(); face.endFill(); face.lineStyle(0); }
      else curve(face, 4, 7, 7.5, 11, 11, 6.5, 2);
      face.beginFill(0xff8a80, 0.5); face.drawEllipse(4, 5, 3, 1.8); face.endFill();
    }
    var armF = limb(P, 9, 21, shirt); armF.x = 0; armF.y = -58;
    var hnd = new P.Graphics(); ell(hnd, 0, 0, 5, 5, skin); hnd.y = 23; armF.addChild(hnd);
    // khay + món (gắn vào thân, không xoay theo tay)
    var tray = new P.Container(), trg = new P.Graphics();
    trg.lineStyle(2, OL, 1, 0.5); trg.beginFill(0x8b5a2b); trg.drawEllipse(0, 0, 21, 4.5); trg.endFill(); trg.lineStyle(0);
    trg.beginFill(0xc58c4a); trg.drawEllipse(-3, -1, 17, 2.4); trg.endFill();
    ell(trg, 0, -7, 11, 6, 0xf4efe6); // tô
    trg.beginFill(0xd2482f); trg.drawEllipse(0, -11, 8, 3.4); trg.endFill(); // nước lẩu
    trg.beginFill(0x7cb342); trg.drawEllipse(-3, -12, 3, 1.6); trg.drawEllipse(3, -11, 2.4, 1.3); trg.endFill();
    trg.lineStyle(1.5, OL, 0.8); trg.moveTo(-11, -7); trg.quadraticCurveTo(0, 2, 11, -7); trg.lineStyle(0);
    tray.addChild(trg); tray.visible = false; body.addChild(tray);
    body.addChild(armF);
    var fx = makePuffs(P, root, 4);
    fx.list.forEach(function (p) { p.g.clear(); p.g.beginFill(0xffffff, 0.8); p.g.drawEllipse(0, 0, 3.2, 4.5); p.g.endFill(); });
    var state = "idle", t = 0, sm = new Smoother({ rot: 0, y: 0, aF: 0.2, aB: -0.2, lF: 0, lB: 0, tilt: 0, trX: 24, trY: -48 });

    var impl = {
      initial: "idle", states: WAIT_STATES, alias: { stand: "idle" },
      enter: function (s) { state = s; drawFace(s); tray.visible = s === "carry" || s === "carryIdle" || s === "serve"; if (!tray.visible) fx.clear(); },
      update: function (dt) {
        t += dt; var S = Math.sin, tg;
        var w = t * 9;
        if (state === "walk") tg = { rot: 0.05, y: -Math.abs(S(w)) * 2, aF: -S(w) * 0.7, aB: S(w) * 0.7, lF: S(w) * 0.6, lB: -S(w) * 0.6, tilt: 0.05, trX: 24, trY: -48 };
        else if (state === "carry") tg = { rot: 0.03, y: -Math.abs(S(w)) * 1.6, aF: -1.35, aB: -1.1, lF: S(w) * 0.55, lB: -S(w) * 0.55, tilt: S(w) * 0.025, trX: 23, trY: -48 - Math.abs(S(w)) * 1.2 };
        else if (state === "carryIdle") tg = { rot: 0, y: S(t * 1.8) * 0.8, aF: -1.35, aB: -1.1, lF: 0.02, lB: -0.02, tilt: 0, trX: 23, trY: -48 + S(t * 1.8) * 0.5 };
        else if (state === "serve") tg = { rot: 0.18 + S(t * 3) * 0.02, y: 0, aF: -1.55, aB: -1.3, lF: 0.1, lB: -0.1, tilt: 0, trX: 29, trY: -45 };
        else tg = { rot: S(t * 1.6) * 0.012, y: S(t * 1.8) * 0.8, aF: 0.12 + S(t * 1.6) * 0.04, aB: -0.1, lF: 0.02, lB: -0.02, tilt: 0, trX: 24, trY: -48 };
        var p = sm.step(tg, dt, 12);
        body.rotation = p.rot; body.y = p.y;
        armF.rotation = p.aF; armB.rotation = p.aB; legF.rotation = p.lF; legB.rotation = p.lB;
        head.rotation = -p.rot * 0.5 + S(t * 1.5) * 0.02; tail.rotation = state === "walk" || state === "carry" ? S(w - 0.8) * 0.18 : S(t * 1.5) * 0.06;
        tray.x = p.trX; tray.y = p.trY; tray.rotation = p.tilt;
        if (tray.visible && Math.random() < dt * 5) fx.emit(p.trX + (Math.random() - 0.5) * 8, p.trY - 14, 0, -18, 1.2, 0.9, 0xffffff);
        fx.step(dt, 0.7, 3);
      }
    };
    finish(root, o);
    return mkApi(root, o, impl);
  }

  window.ChoNoiArt = window.ChoNoiArt || {};
  window.ChoNoiArt.characters = {
    createDiver: createDiver, createCustomer: createCustomer, createChef: createChef, createWaiter: createWaiter,
    states: { diver: DIVER_STATES, customer: CUST_STATES, chef: CHEF_STATES, waiter: WAIT_STATES }, version: 1
  };
})();
