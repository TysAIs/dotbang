/* ==========================================================================
   dotBANG · DIR-06 BLACKOUT field engine — v2 (2026-11-05)

   "the floor lights up where you look." Two modes, one file, no dependencies,
   no network requests, no textures, no fonts, no rAF when idle.

   WHY THIS IS BUILT THE WAY IT IS (measured, see DITHER-ENGINE-2026-11-05.md):
   the cost of a full-screen shader is the number of fragments it runs on, so
   this engine never shades a screen pixel. A DIR-06 dither cell is one 4px
   module and every output pixel inside a cell is identical, so the whole field
   is rendered at CELL resolution and upscaled by the CSS rasteriser with
   image-rendering:pixelated. That is 16–64x fewer fragment invocations than a
   device-pixel-resolution pass for a pixel-identical image.

   On top of that the tone field (the topography) is baked ONCE into a small
   texture at mount/resize, and interactive frames only sample it and compare it
   to a Bayer threshold. Nothing per-frame runs the noise function.

   Contract:
     · WebGL2 only, one program for dither (halftone compiled on first use).
     · no WebGL2 / reduced motion -> the CSS tile block is the page. No error.
     · on-demand frames: nothing draws when the pointer rests, offscreen, or
       when the tab is hidden. No permanent animation loop.
     · tone comes only from an 8x8 Bayer threshold, computed arithmetically
       (integer bit interleave) — no array indexing, no threshold texture.
     · 4px module at every size; type is never crossed (band + keep-outs).
     · every knob is exposed so the measurement harness can ablate it:
         data-res="cell|full"    cell = 4px cells (ship), full = device px
         data-prebake="0|1"      procedural per-frame fbm vs baked tone
         data-cell="2|4"         halftone uses 2px cells, dither 4px

   API: DBField.mount(canvas, cfg) / DBField.attach() for [data-field] markup
   ========================================================================== */
(function (root) {
  'use strict';

  var VS = [
    '#version 300 es',
    'void main(){',
    '  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));',
    '  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);',
    '}'
  ].join('\n');

  /* shared noise + geometry. Only the tone pass and the procedural fallback
     use this; interactive frames do not. */
  var LIB = [
    'float h21(vec2 p){',
    '  vec3 p3 = fract(vec3(p.xyx) * 0.1031);',
    '  p3 += dot(p3, p3.yzx + 33.33);',
    '  return fract((p3.x + p3.y) * p3.z);',
    '}',
    'float vn(vec2 p){',
    '  vec2 i = floor(p), f = fract(p);',
    '  f = f * f * (3.0 - 2.0 * f);',
    '  float a = h21(i), b = h21(i + vec2(1.0, 0.0));',
    '  float c = h21(i + vec2(0.0, 1.0)), d = h21(i + vec2(1.0, 1.0));',
    '  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);',
    '}',
    'float fbm(vec2 p){',
    '  return 0.62 * vn(p) + 0.26 * vn(p * 2.07 + 11.3) + 0.12 * vn(p * 4.11 + 7.7);',
    '}',
    'float rectOut(vec2 p, vec4 r){',
    '  vec2 c = 0.5 * (r.xy + r.zw);',
    '  vec2 h = 0.5 * (r.zw - r.xy);',
    '  vec2 d = abs(p - c) - h;',
    '  return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);',
    '}'
  ].join('\n');

  /* ---- pass 1: bake the tone field. Runs once per resize, never per frame.
     r = topographic density (the only source of tone)
     g = iso-ridge mask (contour lines of the same height field)
     b = halftone density (density pushed toward the print mid-tone) */
  var TONE_FS = [
    '#version 300 es',
    'precision highp float;',
    'out vec4 outCol;',
    'uniform vec2 uRes;',
    'uniform float uCellPx;',
    LIB,
    'void main(){',
    '  vec2 p = gl_FragCoord.xy / uRes.y;',
    '  vec2 w = vec2(vn(p * 1.7 + 4.2), vn(p * 1.7 + 19.1)) - 0.5;',
    '  float h = fbm(p * 2.05 + w * 0.42 + 3.1);',
    '  float ridge = 1.0 - smoothstep(0.0, 0.052, abs(fract(h * 5.0 + 0.5) - 0.5));',
    '  float dens = 0.14 + 0.86 * pow(h, 1.25);',
    '  outCol = vec4(dens, ridge, clamp(dens * 1.15 - 0.04, 0.0, 1.0), 1.0);',
    '}'
  ].join('\n');

  /* ---- pass 2: composite. This is the only thing that runs while a finger
     is on the screen, and it is one texelFetch plus integer ops. ---- */
  var COMP_HEAD = [
    '#version 300 es',
    'precision highp float;',
    'precision highp int;',
    'out vec4 outCol;',
    'uniform highp sampler2D uTone;',
    'uniform vec2 uRes;',
    'uniform float uCellPx;',
    'uniform vec2 uPtr;',
    'uniform float uAmp;',
    'uniform float uR;',
    'uniform float uWave;',
    'uniform vec4 uBlock;',
    'uniform vec4 uPanel;',
    'uniform float uFloor;',
    'uniform vec3 uInk;',
    'uniform vec3 uSig;',
    'uniform float uPrebake;',
    'uniform float uHalf;',
    LIB,
    /* 8x8 Bayer, exact, by the recursive construction:
       M8 = 16*Q(x0,y0) + 4*Q(x1,y1) + Q(x2,y2), Q = [[0,2],[3,1]].
       No array, no texture, no dynamic indexing — 12 integer ops. */
    'int Q(int xb, int yb){',
    '  return xb == 0 ? (yb == 0 ? 0 : 3) : (yb == 0 ? 2 : 1);',
    '}',
    'float bayer8(ivec2 c){',
    '  ivec2 i = ivec2(c.x & 7, c.y & 7);',
    '  int v = 16 * Q(i.x & 1, i.y & 1) + 4 * Q((i.x >> 1) & 1, (i.y >> 1) & 1) + Q((i.x >> 2) & 1, (i.y >> 2) & 1);',
    '  return (float(v) + 0.5) / 64.0;',
    '}',
    'float toneAt(vec2 fc, vec2 p){',
    '  if (uPrebake > 0.5) {',
    '    return texelFetch(uTone, ivec2(floor(fc)), 0).r;',
    '  }',
    '  vec2 w = vec2(vn(p * 1.7 + 4.2), vn(p * 1.7 + 19.1)) - 0.5;',
    '  float h = fbm(p * 2.05 + w * 0.42 + 3.1);',
    '  return 0.14 + 0.86 * pow(h, 1.25);',
    '}',
    'float ridgeAt(vec2 fc, vec2 p){',
    '  if (uPrebake > 0.5) {',
    '    return texelFetch(uTone, ivec2(floor(fc)), 0).g;',
    '  }',
    '  vec2 w = vec2(vn(p * 1.7 + 4.2), vn(p * 1.7 + 19.1)) - 0.5;',
    '  float h = fbm(p * 2.05 + w * 0.42 + 3.1);',
    '  return 1.0 - smoothstep(0.0, 0.052, abs(fract(h * 5.0 + 0.5) - 0.5));',
    '}'
  ].join('\n');

  var COMP_BODY = [
    'void main(){',
    '  vec2 fc = gl_FragCoord.xy / uCellPx;',            // fragment in module units
    /* the field is authored on the module grid: tone is defined at the centre
       of the cell, never per screen pixel. That is what makes the cell-res and
       device-res passes produce the SAME image instead of two different ones. */
    '  vec2 p = (floor(fc) + 0.5) * uCellPx / uRes.y;',  // height units, y up
    '  float dens = toneAt(fc, p);',
    '  float ridge = ridgeAt(fc, p);',
    /* the reveal: stepped, never eased. 4 cuts, as DIR-06 does transitions.
       rv0 is the rest state — a sparse field that is already there, so the
       first frame of a still page is a picture, not a void. */
    '  float rv = 0.17;',
    '  if (uAmp > 0.002) {',
    '    float d = length(fc - uPtr);',
    '    float lens = 1.0 - smoothstep(uR * 0.10, uR, d);',
    '    lens = max(lens, 1.0 - smoothstep(0.0, uR * 0.42, d));',
    '    rv = max(rv, floor(lens * uAmp * 4.01) / 4.0);',
    '  }',
    '  if (uWave > 0.0) {',
    '    float d = length(fc - uPtr);',
    '    float ring = 1.0 - smoothstep(0.0, uR * 0.42, abs(d - uWave));',
    '    rv = max(rv, floor(ring * 3.01) / 3.0);',
    '  }',
    /* the horizon: nothing above the band, so type is never crossed. The edge
       itself is 4 stepped rows, not a cut — a plate edge, not a crop. */
    '  float edge = clamp((uFloor - fc.y) / 9.0, 0.0, 1.0);',
    '  rv *= floor(edge * 4.01) / 4.0;',
    /* the panel is a readout, not a surface */
    '  rv *= smoothstep(0.0, 1.5, rectOut(fc, uPanel));',
    /* the rest block is a solid plate of cells, not a surface */
    '  float inBlock = 1.0 - smoothstep(0.0, 1.2, rectOut(fc, uBlock));',
    '  float ink = 0.0, sig = 0.0;',
    '  if (uHalf < 0.5) {',
    /* ---- ordered dither: tone * reveal vs an exact 8x8 Bayer threshold ---- */
    '    float thr = bayer8(ivec2(floor(fc)));',
    '    float mass = rv * (0.22 + 0.78 * dens);',
    '    ink = step(thr, mass);',
    '    float band = step(thr, ridge * rv * 2.4);',
    '    sig = band * step(0.62, rv) * step(0.58, ridge) * step(0.25, uAmp);',
    '    ink = max(ink, band);',
    '    ink = max(ink, inBlock * step(thr, 0.26));',
    '  } else {',
    /* ---- halftone: a 15 deg screen, AM dot coverage. 1 backing px = 1 dot unit. */
    '    vec2 q = fc - uPtr;',
    '    float a = 0.2618;',
    '    vec2 s = mat2(cos(a), -sin(a), sin(a), cos(a)) * fc;',
    '    vec2 g = fract(s / 6.0) - 0.5;',
    '    float cov = clamp(rv * (0.10 + 0.90 * dens), 0.0, 1.0);',
    '    float r = sqrt(cov) * 0.62;',
    '    ink = 1.0 - step(r, length(g));',
    '    float ring = 1.0 - smoothstep(0.0, 1.6, abs(length(q) - uWave));',
    '    sig = step(0.62, cov) * step(0.5, ridge) * max(ring, step(0.55, rv));',
    '    ink = max(ink, inBlock * step(0.42, length(fract(fc / 6.0) - 0.5)));',
    '  }',
    '  vec3 col = mix(vec3(0.0), uInk, ink);',
    '  col = mix(col, uSig, sig);',
    '  outCol = vec4(col, 1.0);',
    '}'
  ].join('\n');

  var COMP_FS = COMP_HEAD + '\n' + COMP_BODY;

  function now() { return (root.performance && root.performance.now()) || Date.now(); }

  function mount(canvas, cfg) {
    cfg = cfg || {};
    if (!canvas || !canvas.getContext) return null;
    if (root.matchMedia && root.matchMedia('(prefers-reduced-motion: reduce)').matches) return null;

    var gl = canvas.getContext('webgl2', {
      alpha: false, antialias: false, depth: false, stencil: false,
      powerPreference: 'high-performance', preserveDrawingBuffer: false,
      desynchronized: true
    });
    if (!gl) return null;

    var t0 = now();

    function compile(type, src) {
      var s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        if (root.console) console.warn('dbfield shader: ' + gl.getShaderInfoLog(s));
        return null;
      }
      return s;
    }
    function program(fs) {
      var vs = compile(gl.VERTEX_SHADER, VS), f = compile(gl.FRAGMENT_SHADER, fs);
      if (!vs || !f) return null;
      var p = gl.createProgram();
      gl.attachShader(p, vs); gl.attachShader(p, f);
      gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
        if (root.console) console.warn('dbfield link: ' + gl.getProgramInfoLog(p));
        return null;
      }
      gl.deleteShader(vs); gl.deleteShader(f);
      return p;
    }

    var progTone = program(TONE_FS);
    var progComp = program(COMP_FS);
    if (!progTone || !progComp) return null;
    var progHalf = null;                      // compiled on first halftone use

    gl.bindVertexArray(gl.createVertexArray());   // no attribute buffers at all

    var U = {};
    function uniforms(p, names) { var o = {}; for (var i = 0; i < names.length; i++) o[names[i]] = gl.getUniformLocation(p, names[i]); return o; }
    var cU = uniforms(progComp, ['uTone', 'uRes', 'uCellPx', 'uPtr', 'uAmp', 'uR', 'uWave',
      'uBlock', 'uPanel', 'uFloor', 'uInk', 'uSig', 'uPrebake', 'uHalf']);
    var tU = uniforms(progTone, ['uRes', 'uCellPx']);

    var ink = cfg.ink || [1, 1, 1];
    var sig = cfg.sig || [0.424, 0.675, 0.894];    // #6CACE4
    var CELL_CSS = cfg.cell || 4;                  // DIR-06 module; halftone uses 2
    var HALF = cfg.model === 'halftone' ? 1 : 0;
    var FULL = cfg.res === 'full';
    var PREBAKE = cfg.prebake === false ? 0 : 1;
    var MAXPX = cfg.maxPixels || 900000;           // hard ceiling, any config

    var W = 0, H = 0, cellPx = 1, b = 0.25;        // b = backing px per css px
    var texTone = null, fbo = null;
    var stats = { draws: 0, buffer: [0, 0], cells: 0, bpx: 0, mode: HALF ? 'halftone' : 'dither',
                  res: FULL ? 'full' : 'cell', prebake: !!PREBAKE, compileMs: 0, drawMs: 0 };

    /* ---- sizing: backing store is in MODULE units, not screen pixels ---- */
    function layout() {
      var r = canvas.getBoundingClientRect();
      if (!r.width || !r.height) return false;
      b = FULL ? Math.min(root.devicePixelRatio || 1, cfg.dprCap || 2) : 1 / CELL_CSS;
      var w = Math.max(1, Math.round(r.width * b)), h = Math.max(1, Math.round(r.height * b));
      if (w * h > MAXPX) {
        var s = Math.sqrt(MAXPX / (w * h));
        w = Math.max(1, Math.round(w * s)); h = Math.max(1, Math.round(h * s)); b *= s;
      }
      cellPx = Math.max(1, 4 * b);                 // backing px per 4px module
      if (w === W && h === H) return true;
      W = w; H = h;
      canvas.width = W; canvas.height = H;
      stats.buffer = [W, H]; stats.bpx = +(b).toFixed(4);
      stats.cells = Math.ceil(W / cellPx) * Math.ceil(H / cellPx);
      gl.viewport(0, 0, W, H);
      return true;
    }

    /* tone texture is at the CELL grid, not the backing store: the field is
       defined at design resolution, so a device-pixel pass samples exactly the
       same tone values a cell pass does — identical image, more fragments. */
    function bakeTone() {
      if (!PREBAKE) return;
      var cw = Math.max(1, Math.ceil(W / cellPx)), ch = Math.max(1, Math.ceil(H / cellPx));
      if (!texTone) {
        texTone = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, texTone);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        fbo = gl.createFramebuffer();
      }
      if (texTone.w !== cw || texTone.h !== ch) {
        gl.bindTexture(gl.TEXTURE_2D, texTone);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, cw, ch, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
        texTone.w = cw; texTone.h = ch;
      }
      gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texTone, 0);
      gl.viewport(0, 0, cw, ch);
      gl.useProgram(progTone);
      gl.uniform2f(tU.uRes, cw, ch);
      gl.uniform1f(tU.uCellPx, cellPx);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.bindTexture(gl.TEXTURE_2D, null);
      gl.viewport(0, 0, W, H);
      stats.cw = cw; stats.ch = ch;
      stats.draws++;
    }

    var state = { ptr: [0.5, 0.4], amp: 0, wave: 0, frames: 0 };
    var raf = 0, idleTimer = 0, waveTimer = 0;

    /* rect in module units (y up) from a DOM element */
    function rectUnits(el) {
      if (!el) return [-9999, -9999, -9999, -9999];
      var c = canvas.getBoundingClientRect();
      var r = el.getBoundingClientRect ? el.getBoundingClientRect() : el;
      return [
        (r.left - c.left) * b / cellPx,
        (c.bottom - (r.top + r.height)) * b / cellPx,
        (r.left + r.width - c.left) * b / cellPx,
        (c.bottom - r.top) * b / cellPx
      ];
    }
    function floorUnits() {
      var el = cfg.floor;
      if (!el) return 9999;
      var c = canvas.getBoundingClientRect();
      var r = el.getBoundingClientRect ? el.getBoundingClientRect() : el;
      return (c.bottom - r.top) * b / cellPx;
    }

    function draw() {
      raf = 0;
      if (!W && !layout()) return;
      var t = now();
      var bb = rectUnits(cfg.block), pp = rectUnits(cfg.panel);
      gl.useProgram(progComp);
      gl.uniform2f(cU.uRes, W, H);
      gl.uniform1f(cU.uCellPx, cellPx);
      gl.uniform4f(cU.uBlock, bb[0], bb[1], bb[2], bb[3]);
      gl.uniform4f(cU.uPanel, pp[0], pp[1], pp[2], pp[3]);
      gl.uniform1f(cU.uFloor, floorUnits());
      gl.uniform2f(cU.uPtr, state.ptr[0], state.ptr[1]);
      /* uR is in MODULE units (the shader's space), never backing pixels —
         mixing the two is what made the first full-res run denser than the
         cell-res one. */
      gl.uniform1f(cU.uR, Math.max(18, (Math.min(W, H) / cellPx) * 0.42));
      gl.uniform1f(cU.uAmp, state.amp);
      gl.uniform1f(cU.uWave, state.wave > 0 ? state.wave : -1);
      gl.uniform3f(cU.uInk, ink[0], ink[1], ink[2]);
      gl.uniform3f(cU.uSig, sig[0], sig[1], sig[2]);
      gl.uniform1f(cU.uPrebake, PREBAKE ? 1 : 0);
      gl.uniform1f(cU.uHalf, HALF);
      if (PREBAKE && texTone) {
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, texTone);
        gl.uniform1i(cU.uTone, 0);
      }
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      state.frames++; stats.draws++;
      stats.drawMs = +(now() - t).toFixed(3);
      stats.lastAmp = +state.amp.toFixed(2);
      if (cfg.onFrame) cfg.onFrame(stats);
    }

    function schedule() { if (!raf) raf = root.requestAnimationFrame(draw); }

    function toPtr(e) {
      var r = canvas.getBoundingClientRect();
      /* module units: y up, origin bottom-left of the canvas */
      state.ptr[0] = (e.clientX - r.left) * b / cellPx;
      state.ptr[1] = (r.height - (e.clientY - r.top)) * b / cellPx;
    }

    function pointer(e) {
      toPtr(e);
      state.amp = Math.min(1, state.amp + 0.5);
      schedule(); armIdle();
    }

    function armIdle() {
      root.clearTimeout(idleTimer);
      idleTimer = root.setTimeout(function () {
        var steps = 4, i = 0;
        var t = root.setInterval(function () {
          if (++i >= steps) {
            root.clearInterval(t); state.wave = 0; state.amp = 0; schedule();
            if (cfg.onIdle) cfg.onIdle(stats);
            return;
          }
          state.amp *= 0.5;
          schedule();
        }, 80);
      }, cfg.idleMs || 1100);
    }

    function stepWave() {
      var n = 0, max = 30;
      state.wave = 2;
      root.clearInterval(waveTimer);
      waveTimer = root.setInterval(function () {
        if (++n > max) { root.clearInterval(waveTimer); state.wave = 0; schedule(); return; }
        state.wave = 2 + n * 9;                 // whole modules, never eased
        schedule();
      }, 26);
    }

    function intro() {
      var pts = [[0.18, 0.22], [0.42, 0.18], [0.66, 0.22], [0.86, 0.18]];
      var i = 0;
      var t = root.setInterval(function () {
        if (i >= pts.length) { root.clearInterval(t); armIdle(); return; }
        var r = canvas.getBoundingClientRect();
        state.ptr = [pts[i][0] * r.width * b / cellPx, pts[i][1] * r.height * b / cellPx];
        state.amp = 1;
        schedule(); i++;
      }, 150);
      state.ptr = [pts[0][0] * canvas.getBoundingClientRect().width * b / cellPx, 0.22 * H];
      state.amp = 1;
      schedule();
    }

    var on = cfg.on || canvas.parentElement || canvas;
    on.addEventListener('pointermove', pointer, { passive: true });
    on.addEventListener('pointerdown', function (e) { toPtr(e); state.amp = 1; state.wave = 2; stepWave(); schedule(); }, { passive: true });
    canvas.addEventListener('webglcontextlost', function (e) {
      e.preventDefault(); root.cancelAnimationFrame(raf); raf = 0; canvas.classList.add('is-dead');
    }, false);
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) { root.cancelAnimationFrame(raf); raf = 0; } else schedule();
    });

    if (!layout()) return null;
    bakeTone();
    stats.compileMs = +(now() - t0).toFixed(2);
    draw();
    if (cfg.intro !== false) root.setTimeout(intro, 260);

    var api = {
      stats: stats, state: state, draw: draw, gl: gl,
      pointerAt: function (x, y) {
        var r = canvas.getBoundingClientRect();
        state.ptr = [(x - r.left) * b / cellPx, (r.height - (y - r.top)) * b / cellPx];
        state.amp = 1; schedule(); armIdle();
      },
      setModel: function (m) {
        cfg.model = m; HALF = m === 'halftone' ? 1 : 0;
        stats.mode = HALF ? 'halftone' : 'dither';
        CELL_CSS = HALF ? 2 : 4;
        if (HALF && !progHalf) { progHalf = progComp; }   // same program, uniform switch
        W = 0; H = 0; layout(); bakeTone(); draw();
      },
      /* cost of producing one frame, GPU work included: draw + gl.finish in a
         tight loop. Used by the measurement harness, not by the page. */
      benchFrames: function (n) {
        n = n || 60;
        var t = now();
        for (var i = 0; i < n; i++) {
          state.amp = (i & 1) ? 1 : 0.75;
          state.wave = (i & 3) ? 0 : 20 + i;
          draw();
          gl.finish();
        }
        return +((now() - t) / n).toFixed(3);
      },
      resize: function () { W = 0; H = 0; layout(); bakeTone(); draw(); },
      dispose: function () {
        root.cancelAnimationFrame(raf);
        var lc = gl.getExtension('WEBGL_lose_context');
        if (lc) lc.loseContext();
      }
    };
    root.DBField.instance = api;
    return api;
  }

  function attach() {
    var c = document.querySelector('canvas[data-field]');
    if (!c) return null;
    var inst = mount(c, {
      floor: document.querySelector('[data-field-floor]'),
      block: document.querySelector('[data-field-block]'),
      panel: document.querySelector('[data-field-clear]'),
      on: c.closest('.hero') || c.parentElement,
      intro: c.dataset.intro !== 'off',
      model: c.dataset.model || 'dither',
      res: c.dataset.res || 'cell',
      prebake: c.dataset.prebake !== '0',
      cell: c.dataset.cell ? +c.dataset.cell : undefined,
      maxPixels: c.dataset.maxPixels ? +c.dataset.maxPixels : undefined
    });
    c.dataset.ready = inst ? '1' : '0';
    /* the CSS plate is the no-JS state; once the field is live it must go, or
       two dither phases sit next to each other and read as a seam */
    if (inst) {
      var wrap = c.parentElement;
      if (wrap && wrap.classList.contains('field-wrap')) wrap.classList.add('is-live');
    }
    return inst;
  }

  root.DBField = { mount: mount, attach: attach, version: '2-2026-11-05' };
  if (document.readyState === 'loading')
    root.addEventListener('DOMContentLoaded', attach);
  else attach();
})(window);
