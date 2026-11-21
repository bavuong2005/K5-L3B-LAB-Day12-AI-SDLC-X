/* Cho Noi - procedural background music (WebAudio only, no files, no network).
 * window.ChoNoiAudio = { init, setScene, setDepth, setIntensity, setMuted, isMuted,
 *   setVolume, stop, scenes, version }.  Client-only: uses its own seeded PRNG,
 * never the gameplay RNG. All compositions are original. */
(function (root) {
  "use strict";

  var SCENES = ["menu", "dive", "quan", "shop", "result", "result_sad", "story"];
  var FADE = 2.0;          // crossfade seconds
  var LOOKAHEAD = 0.45;    // seconds scheduled ahead
  var TICK_MS = 90;

  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function mtof(m) { return 440 * Math.pow(2, (m - 69) / 12); }
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  var PENT = [0, 2, 4, 7, 9];        // major pentatonic
  var MINPENT = [0, 3, 5, 7, 10];    // minor pentatonic
  function degToMidi(base, scale, i) {
    var n = scale.length, o = Math.floor(i / n), k = ((i % n) + n) % n;
    return base + 12 * o + scale[k];
  }
  // random-walk pattern over scale degrees; -1 = rest
  function genPattern(rng, len, density, startIdx, lo, hi, grid) {
    var out = [], idx = startIdx;
    for (var s = 0; s < len; s++) {
      var onGrid = grid ? (s % grid === 0) : true;
      if (onGrid && rng() < density) {
        var r = rng(), d = r < 0.3 ? -1 : r < 0.6 ? 1 : r < 0.75 ? -2 : r < 0.9 ? 2 : 0;
        idx = clamp(idx + d, lo, hi);
        out.push(idx);
      } else out.push(-1);
    }
    return out;
  }

  function createEngine() {
    var E = {};
    var ctx = null, master, comp, shaper, noiseBuf;
    var muted = false, volume = 0.7;
    var depth = 0, intensity = 0, seed = 20241;
    var current = null, fading = [];
    var timer = null, offlineMode = false;

    function noiseSource(c) {
      var s = c.createBufferSource(); s.buffer = noiseBuf; s.loop = true; return s;
    }

    function buildGraph(c) {
      ctx = c;
      master = c.createGain();
      master.gain.value = muted ? 0 : volume * 0.8;
      comp = c.createDynamicsCompressor();
      comp.threshold.value = -16; comp.knee.value = 14; comp.ratio.value = 4;
      comp.attack.value = 0.01; comp.release.value = 0.25;
      shaper = c.createWaveShaper();   // soft limiter: guarantees |y| < 1
      var curve = new Float32Array(1024);
      for (var i = 0; i < 1024; i++) { var x = (i / 1023) * 2 - 1; curve[i] = Math.tanh(x * 1.2) * 0.95; }
      shaper.curve = curve;
      master.connect(comp); comp.connect(shaper); shaper.connect(c.destination);
      var n = Math.floor(c.sampleRate * 2), b = c.createBuffer(1, n, c.sampleRate), d = b.getChannelData(0);
      var r = mulberry32(7);
      for (var j = 0; j < n; j++) d[j] = r() * 2 - 1;
      noiseBuf = b;
    }

    /* ---------- instruments (all connect to scene bus) ---------- */
    function env(g, t, a, peak, dur) {
      g.gain.setValueAtTime(0.0001, t);
      g.gain.linearRampToValueAtTime(peak, t + a);
      g.gain.exponentialRampToValueAtTime(0.0001, t + Math.max(a + 0.02, dur));
    }
    // plucked string (dan tranh-like); opts.glide = dan bau slide, opts.vib = vibrato
    function pluck(sc, t, midi, dur, vol, o) {
      o = o || {};
      var f = mtof(midi), c = ctx;
      var osc = c.createOscillator(), osc2 = c.createOscillator();
      var lp = c.createBiquadFilter(), g = c.createGain();
      osc.type = o.type || "triangle"; osc2.type = "sine";
      var bright = o.bright || 2600;
      lp.type = "lowpass"; lp.Q.value = 0.7;
      lp.frequency.setValueAtTime(bright, t);
      lp.frequency.exponentialRampToValueAtTime(Math.max(300, f * 1.5), t + dur * 0.8);
      if (o.glide) {
        osc.frequency.setValueAtTime(f * Math.pow(2, -o.glide / 12), t);
        osc.frequency.exponentialRampToValueAtTime(f, t + 0.18);
        osc2.frequency.setValueAtTime(f * 2 * Math.pow(2, -o.glide / 12), t);
        osc2.frequency.exponentialRampToValueAtTime(f * 2, t + 0.18);
      } else { osc.frequency.value = f; osc2.frequency.value = f * 2; }
      var g2 = c.createGain(); g2.gain.value = 0.25;
      osc.connect(lp); osc2.connect(g2); g2.connect(lp); lp.connect(g); g.connect(sc.bus);
      env(g, t, 0.006, vol, dur);
      var end = t + dur + 0.05;
      if (o.vib) {
        var lfo = c.createOscillator(), lg = c.createGain();
        lfo.frequency.value = 5.2; lg.gain.value = 12;
        lfo.connect(lg); lg.connect(osc.detune);
        lfo.start(t + 0.2); lfo.stop(end);
      }
      osc.start(t); osc2.start(t); osc.stop(end); osc2.stop(end);
    }
    function noiseHit(sc, t, dur, vol, ftype, freq, q) {
      var s = noiseSource(ctx), f = ctx.createBiquadFilter(), g = ctx.createGain();
      f.type = ftype; f.frequency.value = freq; f.Q.value = q || 0.8;
      s.connect(f); f.connect(g); g.connect(sc.bus);
      env(g, t, 0.003, vol, dur);
      s.start(t, Math.floor(ctx.sampleRate * 0) / ctx.sampleRate); s.stop(t + dur + 0.03);
    }
    function thump(sc, t, f0, f1, dur, vol) {
      var o = ctx.createOscillator(), g = ctx.createGain();
      o.type = "sine";
      o.frequency.setValueAtTime(f0, t);
      o.frequency.exponentialRampToValueAtTime(f1, t + dur * 0.6);
      o.connect(g); g.connect(sc.bus);
      env(g, t, 0.004, vol, dur);
      o.start(t); o.stop(t + dur + 0.03);
    }
    function wood(sc, t, vol) {   // light drum / mo
      var o = ctx.createOscillator(), g = ctx.createGain();
      o.type = "sine";
      o.frequency.setValueAtTime(420, t);
      o.frequency.exponentialRampToValueAtTime(260, t + 0.07);
      o.connect(g); g.connect(sc.bus);
      env(g, t, 0.002, vol, 0.12);
      o.start(t); o.stop(t + 0.15);
    }
    function chime(sc, t, midi, vol) {   // lantern chime: inharmonic partials
      var f = mtof(midi), ratios = [1, 2.76, 5.4], amps = [1, 0.35, 0.12];
      for (var i = 0; i < 3; i++) {
        var o = ctx.createOscillator(), g = ctx.createGain();
        o.type = "sine"; o.frequency.value = f * ratios[i];
        o.connect(g); g.connect(sc.bus);
        env(g, t, 0.003, vol * amps[i], 1.6 / (1 + i * 0.6));
        o.start(t); o.stop(t + 1.7);
      }
    }
    function bubble(sc, t, vol) {
      var o = ctx.createOscillator(), g = ctx.createGain();
      var f = 500 + ((t * 977) % 1) * 700;
      o.type = "sine";
      o.frequency.setValueAtTime(f, t);
      o.frequency.exponentialRampToValueAtTime(f * 1.8, t + 0.09);
      o.connect(g); g.connect(sc.bus);
      env(g, t, 0.01, vol, 0.12);
      o.start(t); o.stop(t + 0.15);
    }

    // sustained pad: 3 saw voices -> lowpass; chord changes glide
    function makePad(sc, cutoff, level) {
      var c = ctx, lp = c.createBiquadFilter(), g = c.createGain(), oscs = [];
      lp.type = "lowpass"; lp.frequency.value = cutoff; lp.Q.value = 0.5;
      g.gain.value = level;
      lp.connect(g); g.connect(sc.bus);
      for (var i = 0; i < 3; i++) {
        var o = c.createOscillator(); o.type = "sawtooth";
        o.detune.value = (i - 1) * 7; o.frequency.value = 110;
        o.connect(lp); o.start(); oscs.push(o); sc.stoppables.push(o);
      }
      sc.pad = { lp: lp, g: g, oscs: oscs, level: level };
    }
    function padChord(sc, t, midis) {
      var p = sc.pad; if (!p) return;
      for (var i = 0; i < 3; i++) p.oscs[i].frequency.setTargetAtTime(mtof(midis[i % midis.length]), t, 0.35);
    }
    function ambientNoise(sc, ftype, freq, q, level, lfoHz, lfoAmt) {
      var c = ctx, s = noiseSource(c), f = c.createBiquadFilter(), g = c.createGain();
      f.type = ftype; f.frequency.value = freq; f.Q.value = q;
      g.gain.value = level;
      s.connect(f); f.connect(g); g.connect(sc.bus); s.start(); sc.stoppables.push(s);
      if (lfoHz) {
        var l = c.createOscillator(), lg = c.createGain();
        l.frequency.value = lfoHz; lg.gain.value = level * lfoAmt;
        l.connect(lg); lg.connect(g.gain); l.start(); sc.stoppables.push(l);
      }
      return { f: f, g: g };
    }

    /* ---------- scene definitions ---------- */
    // each: init(sc), stepDur(), step(sc,t,sib,bar)  (sib = 16th step in bar)
    var DEF = {};

    DEF.menu = {
      init: function (sc) {
        makePad(sc, 900, 0.05);
        ambientNoise(sc, "bandpass", 700, 0.4, 0.012, 0.11, 0.6);   // river
        sc.base = 62; // D4
      },
      stepDur: function () { return 60 / 66 / 4; },
      step: function (sc, t, sib, bar) {
        var roots = [0, 7, 5, 7], b8 = bar % 8, r = roots[b8 % 4];
        if (sib === 0) {
          padChord(sc, t, [50 + r - (r > 5 ? 12 : 0), 57 + r - (r > 5 ? 12 : 0), 62 + r - (r > 5 ? 12 : 0)]);
          var rng = mulberry32(seed + b8 * 101);
          sc.pat = genPattern(rng, 16, 0.5, b8 === 0 ? 5 : sc.last || 5, 2, 10, 2);
          sc.last = 5;
          for (var i = 15; i >= 0; i--) if (sc.pat[i] >= 0) { sc.last = sc.pat[i]; break; }
          sc.bau = (b8 % 4 === 3) ? 8 : -1;   // long dan bau note
        }
        var d = sc.pat[sib];
        if (d >= 0) pluck(sc, t, degToMidi(sc.base, PENT, d), 1.1, 0.16, { bright: 2200 });
        if (sib === 0 && b8 % 2 === 0) pluck(sc, t, 38 + r, 2.2, 0.15, { type: "sine", bright: 700 });
        if (sib === 8 && sc.bau >= 0) pluck(sc, t, degToMidi(sc.base, PENT, 7), 3.2, 0.14, { glide: 2, vib: true, bright: 1800 });
      },
    };

    DEF.dive = {
      init: function (sc) {
        makePad(sc, 1800, 0.05);
        sc.amb = ambientNoise(sc, "lowpass", 400, 0.3, 0.02, 0.07, 0.5);
        sc.drone = ctx.createOscillator(); var dg = ctx.createGain(); dg.gain.value = 0.0;
        sc.drone.type = "sine"; sc.drone.frequency.value = mtof(41.5);   // tritone-ish over 'F#' pad
        sc.drone.connect(dg); dg.connect(sc.bus); sc.drone.start(); sc.stoppables.push(sc.drone); sc.droneG = dg;
        sc.base = 69;
      },
      stepDur: function () { return 60 / (80 - 34 * clamp(depth / 200, 0, 1)) / 4; },
      step: function (sc, t, sib, bar) {
        var dk = clamp(depth / 200, 0, 1), it = intensity, b8 = bar % 8;
        var cut = 1800 - 1450 * dk;
        sc.pad.lp.frequency.setTargetAtTime(cut, t, 0.6);
        sc.amb.f.frequency.setTargetAtTime(500 - 300 * dk, t, 0.6);
        sc.droneG.gain.setTargetAtTime(0.03 + 0.1 * it, t, 0.4);
        sc.drone.frequency.setTargetAtTime(mtof(41 + (it > 0.5 ? 0.6 : 0)), t, 0.4);
        if (sib === 0) {
          var chords = [[57, 64, 69], [55, 62, 67], [53, 60, 65], [55, 62, 67]];   // Am / G / F / G (airy)
          var ch = chords[b8 % 4].map(function (m) { return m - Math.round(dk * 5); });
          padChord(sc, t, ch);
          var rng = mulberry32(seed + 500 + b8 * 37);
          sc.pat = genPattern(rng, 16, 0.75, 4, 0, 9, 2);
        }
        var a = sc.pat[sib];
        if (a >= 0) {
          var m = degToMidi(sc.base - Math.round(dk * 12), MINPENT, a);
          pluck(sc, t, m, 0.9, 0.11 * (1 - 0.5 * dk), { bright: 1500 - 900 * dk });
        }
        if (sib % 4 === 0 && (bar * 4 + sib / 4) % 3 === 0) bubble(sc, t + 0.01, 0.02 * (1 - dk));
        if (it > 0.25) {     // low pulse, faster as tension rises
          var every = it > 0.7 ? 4 : 8;
          if (sib % every === 0) thump(sc, t, 70, 38, 0.45, 0.14 + 0.16 * it);
          if (it > 0.7 && sib % 8 === 4) thump(sc, t, 90, 45, 0.3, 0.1);
        }
      },
    };

    DEF.quan = {
      init: function (sc) {
        makePad(sc, 1400, 0.025);
        sc.base = 67; // G4
        sc.bassBase = 43;
      },
      stepDur: function () { return 60 / (108 + 32 * intensity) / 4; },
      step: function (sc, t, sib, bar) {
        var it = intensity, b8 = bar % 8, roots = [0, 0, 5, 7, 0, 0, 5, 7], r = roots[b8];
        if (sib === 0) {
          padChord(sc, t, [55 + r, 62 + r, 67 + r]);
          var rng = mulberry32(seed + 900 + b8 * 53);
          sc.pat = genPattern(rng, 16, 0.55 + 0.35 * it, b8 === 0 ? 5 : (sc.last || 5), 1, 11, it > 0.5 ? 1 : 2);
          sc.last = 5;
          for (var i = 15; i >= 0; i--) if (sc.pat[i] >= 0) { sc.last = sc.pat[i]; break; }
          sc.pat2 = mulberry32(seed + 77 + b8)();
        }
        var d = sc.pat[sib];
        if (d >= 0) pluck(sc, t, degToMidi(sc.base, PENT, d), 0.45, 0.14, { bright: 3200 });
        // bass groove
        if (sib === 0 || sib === 6 || sib === 8 || (it > 0.5 && sib === 14))
          pluck(sc, t, sc.bassBase + r + (sib === 6 ? 7 : 0), 0.35, 0.2, { type: "sine", bright: 600 });
        // light percussion
        if (sib % 8 === 0) wood(sc, t, 0.12);
        if (sib % 4 === 2) noiseHit(sc, t, 0.05, 0.035, "highpass", 6500, 0.7);
        if (it > 0.4 && sib % 2 === 1) noiseHit(sc, t, 0.03, 0.02 + 0.02 * it, "highpass", 8000, 0.7);
        if (sib === 12) wood(sc, t, 0.07);
        // lantern chime
        if ((sib === 4 || sib === 10) && sc.pat2 > 0.35) chime(sc, t, degToMidi(79, PENT, (b8 + sib) % 5), 0.035);
      },
    };

    DEF.shop = {
      init: function (sc) { makePad(sc, 1100, 0.04); sc.base = 64; },
      stepDur: function () { return 60 / 78 / 4; },
      step: function (sc, t, sib, bar) {
        var b8 = bar % 8, roots = [0, 5, 7, 0], r = roots[b8 % 4];
        if (sib === 0) {
          padChord(sc, t, [52 + r, 59 + r, 64 + r]);
          sc.pat = genPattern(mulberry32(seed + 1300 + b8 * 29), 16, 0.8, 4, 0, 9, 2);
        }
        var d = sc.pat[sib];
        if (d >= 0 && (sib % 4 === 0 || sib % 4 === 2)) pluck(sc, t, degToMidi(sc.base, PENT, d), 0.8, 0.1, { bright: 2000 });
        if (sib === 8 && b8 % 2 === 1) chime(sc, t, 88, 0.025);
      },
    };

    DEF.story = {
      init: function (sc) { makePad(sc, 700, 0.06); sc.base = 57; },
      stepDur: function () { return 60 / 58 / 4; },
      step: function (sc, t, sib, bar) {
        var b8 = bar % 8, ch = [[45, 52, 60], [43, 50, 59], [41, 48, 57], [43, 50, 59]][b8 % 4];
        if (sib === 0) {
          padChord(sc, t, ch);
          sc.pat = genPattern(mulberry32(seed + 1700 + b8 * 41), 16, 0.35, 5, 2, 9, 4);
          pluck(sc, t, ch[0] - 12, 4, 0.14, { type: "sine", bright: 500 });
        }
        var d = sc.pat[sib];
        if (d >= 0) pluck(sc, t, degToMidi(sc.base + 12, MINPENT, d), 2.2, 0.12, { bright: 1500, vib: (b8 % 2 === 1) });
      },
    };

    function sting(notes, chord, bpm, glide) {
      return {
        init: function (sc) { makePad(sc, 1300, 0.0001); sc.base = 62; },
        stepDur: function () { return 60 / bpm / 4; },
        step: function (sc, t, sib, bar) {
          var s = bar * 16 + sib;
          if (s === 0) { sc.pad.g.gain.setValueAtTime(0.0001, t); sc.pad.g.gain.linearRampToValueAtTime(0.06, t + 0.5); }
          for (var i = 0; i < notes.length; i++) if (notes[i][0] === s) pluck(sc, t, notes[i][1], notes[i][2], 0.18, { glide: glide, bright: 2600 });
          if (s === 8) padChord(sc, t, chord);
          if (s === 22) { sc.pad.g.gain.setTargetAtTime(0.0001, t, 0.7); }
        },
      };
    }
    DEF.result = sting([[0, 62, 0.5], [2, 66, 0.5], [4, 69, 0.5], [6, 74, 0.6], [8, 78, 2.4], [8, 69, 2.4], [8, 62, 2.4]], [50, 57, 66], 100, 0);
    DEF.result_sad = sting([[0, 69, 0.8], [4, 67, 0.8], [8, 64, 1.0], [12, 62, 3.0], [12, 50, 3.0]], [50, 57, 62], 62, 0.5);

    /* ---------- scheduler ---------- */
    function startScene(name) {
      var def = DEF[name];
      var bus = ctx.createGain();
      var now = ctx.currentTime;
      bus.gain.setValueAtTime(0.0001, now);
      bus.gain.linearRampToValueAtTime(1, now + FADE);
      bus.connect(master);
      var sc = { name: name, def: def, bus: bus, stoppables: [], step: 0, next: now + 0.08, killAt: 0 };
      def.init(sc);
      return sc;
    }
    function retire(sc) {
      var now = ctx.currentTime;
      sc.bus.gain.cancelScheduledValues(now);
      sc.bus.gain.setValueAtTime(sc.bus.gain.value, now);
      sc.bus.gain.linearRampToValueAtTime(0.0001, now + FADE);
      sc.killAt = now + FADE + 0.1;
      fading.push(sc);
    }
    function kill(sc) {
      for (var i = 0; i < sc.stoppables.length; i++) { try { sc.stoppables[i].stop(); } catch (e) { } }
      try { sc.bus.disconnect(); } catch (e) { }
    }
    function pump(horizon) {
      if (!ctx) return;
      var now = ctx.currentTime;
      var list = current ? [current].concat(fading) : fading;
      for (var k = 0; k < list.length; k++) {
        var sc = list[k];
        if (!offlineMode && sc.next < now - 0.1) sc.next = now + 0.03;   // resync after stall
        var guard = 0;
        while (sc.next < horizon && guard++ < 256) {
          var sib = sc.step % 16, bar = Math.floor(sc.step / 16);
          try { sc.def.step(sc, sc.next, sib, bar); } catch (e) { if (root.console) console.warn("ChoNoiAudio step", e); }
          sc.next += sc.def.stepDur();
          sc.step++;
        }
      }
      for (var j = fading.length - 1; j >= 0; j--) {
        if (now >= fading[j].killAt) { kill(fading[j]); fading.splice(j, 1); }
      }
    }
    function loop() {
      timer = null;
      if (!ctx) return;
      if (ctx.state === "running") pump(ctx.currentTime + LOOKAHEAD);
      if (current || fading.length) timer = setTimeout(loop, TICK_MS);
    }
    function kick() { if (!timer && !offlineMode) timer = setTimeout(loop, 0); }

    /* ---------- public ---------- */
    E.version = 1;
    E.scenes = SCENES.slice();
    E.init = function () {
      try {
        if (!ctx) {
          var AC = root.AudioContext || root.webkitAudioContext;
          if (!AC) return false;
          buildGraph(new AC());
        }
        if (ctx.state === "suspended" && ctx.resume) ctx.resume();
        if (E._pending !== undefined && !current) { var p = E._pending; E._pending = undefined; E.setScene(p); }
        return true;
      } catch (e) { return false; }
    };
    E.setScene = function (name) {
      if (name == null || !DEF[name]) {
        if (name != null) return false;
        E._pending = undefined;
        if (ctx && current) { retire(current); current = null; kick(); }
        return true;
      }
      if (!ctx) { E._pending = name; return true; }   // remembered until init()
      if (current && current.name === name) return true;
      if (current) retire(current);
      current = startScene(name);
      kick();
      return true;
    };
    E.getScene = function () { return current ? current.name : (E._pending || null); };
    E.setDepth = function (m) { m = +m; depth = isFinite(m) ? Math.max(0, m) : 0; };
    E.setIntensity = function (v) { v = +v; intensity = isFinite(v) ? clamp(v, 0, 1) : 0; };
    function applyMaster() {
      if (!ctx) return;
      master.gain.cancelScheduledValues(ctx.currentTime);
      master.gain.setTargetAtTime(muted ? 0 : volume * 0.8, ctx.currentTime, 0.05);
    }
    E.setMuted = function (b) { muted = !!b; applyMaster(); };
    E.isMuted = function () { return muted; };
    E.setVolume = function (v) { v = +v; volume = isFinite(v) ? clamp(v, 0, 1) : volume; applyMaster(); };
    E.setSeed = function (s) { seed = (s | 0) || 1; };
    E.stop = function () { E.setScene(null); };
    E._stats = function () { return { hasCtx: !!ctx, state: ctx && ctx.state, scene: current && current.name, fading: fading.length, timer: !!timer }; };

    // test hook: render a scene offline (deterministic, no real-time scheduling)
    E._renderOffline = function (name, o) {
      o = o || {};
      var OAC = root.OfflineAudioContext || root.webkitOfflineAudioContext;
      var sr = o.sampleRate || 32000, secs = o.seconds || 10;
      var oc = new OAC(2, Math.floor(sr * secs), sr);
      var T = createEngine();
      T._attachOffline(oc, o);
      T.setScene(name);
      T._pumpTo(secs);
      return oc.startRendering();
    };
    E._attachOffline = function (oc, o) {
      offlineMode = true; buildGraph(oc);
      if (o.depth != null) E.setDepth(o.depth);
      if (o.intensity != null) E.setIntensity(o.intensity);
      if (o.seed != null) E.setSeed(o.seed);
    };
    E._pumpTo = function (secs) {
      for (var t = 0.25; t <= secs + 0.25; t += 0.25) pump(t);
    };
    return E;
  }

  root.ChoNoiAudio = createEngine();
})(typeof window !== "undefined" ? window : this);
