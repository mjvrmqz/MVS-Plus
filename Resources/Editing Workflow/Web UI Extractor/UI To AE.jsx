/**
 * UI JSON -> AFTER EFFECTS v25
 * ExtendScript (.jsx)
 *
 * v24 changes — DUAL NULL SYSTEM:
 *   ─── INTERACTION NULL (hover cursor) ────────────────────────────────────
 *   Remains as before: a 2D cursor proxy.
 *     X position (0 → compWidth)  = horizontal cursor position (hover detection)
 *     Y position (0 → compHeight) = vertical cursor position
 *   Moving it left/right activates hover animations on elements beneath it.
 *   Starts at [-100, compHeight/2] (off-screen left, mid-height).
 *
 *   ─── SCROLL NULL (scroll depth) ─────────────────────────────────────────
 *   A NEW dedicated null for scroll-driven animations.
 *     Y position 0          = page scroll top    (page is at the very top)
 *     Y position compHeight = page scroll bottom (page is fully scrolled down)
 *   Moving this null DOWN in the AE comp mimics scrolling the webpage down:
 *   elements below the fold fade in, parallax layers shift, sticky headers
 *   transform, cinematic sections reveal, etc.
 *   Starts at Y=0 (top of page / no scroll).
 *   Label color: Cyan (label 9) to distinguish from the orange INTERACTION NULL.
 *
 *   All trigger:'scroll' expressions now reference "SCROLL NULL" instead of
 *   "INTERACTION NULL". The two nulls are fully independent — you can:
 *     • Scrub SCROLL NULL to simulate page scroll (with or without hover)
 *     • Move INTERACTION NULL to trigger hover states at any scroll position
 *     • Keyframe both to recreate a real user session exactly
 *
 *   ─── GUIDE TEXT LAYER ───────────────────────────────────────────────────
 *   A locked text layer at the top of the comp explains both nulls.
 *
 * v23 changes (retained):
 *   - FULL-PAGE COMP: Comp height = vp.pageHeight.
 *   - FILTER / BLUR ANIMATIONS via Gaussian Blur effect.
 *   - BACKDROP-FILTER BLUR support.
 *
 * v22 changes (retained):
 *   - Auto-animations as direct AE keyframes with loopOut("cycle").
 *   - Video footage import and layer placement.
 *   - SVG path → native AE vector shape layers.
 *   - Gradient layer support (ramp effect or rasterized PNG).
 */

(function buildUIComp() {

  if (typeof JSON === 'undefined') {
    JSON = {};
    JSON.parse = function (s) { return eval('(' + s + ')'); };
  }

  var dpr = 1;

  // ── Color helpers ──────────────────────────────────────────────────────────

  function toAEC(c) {
    if (!c) return [0.5, 0.5, 0.5];
    return [c.r / 255, c.g / 255, c.b / 255];
  }

  function parseRadius(radiusStr, w, h) {
    if (!radiusStr || radiusStr === '0px' || radiusStr === '0') return 0;
    var first = radiusStr.split(' ')[0];
    var pct = first.match(/^([\d.]+)%$/);
    if (pct) {
      var shorter = (w && h) ? Math.min(w, h) : 0;
      return parseFloat(pct[1]) / 100 * shorter;
    }
    var px = first.match(/^([\d.]+)px$/);
    return px ? parseFloat(px[1]) : 0;
  }

  // ── Animation value parsers ────────────────────────────────────────────────

  function parseCSSColor(str) {
    if (!str) return null;
    var m = str.match(/rgba?\(\s*([\d.]+)[,\s]\s*([\d.]+)[,\s]\s*([\d.]+)/);
    if (m) return [parseFloat(m[1])/255, parseFloat(m[2])/255, parseFloat(m[3])/255];
    var h = str.match(/^#([0-9a-f]{3,6})$/i);
    if (h) {
      var hex = h[1];
      if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
      return [parseInt(hex.slice(0,2),16)/255, parseInt(hex.slice(2,4),16)/255, parseInt(hex.slice(4,6),16)/255];
    }
    return null;
  }

  function parseCSSOpacity(str) {
    if (!str) return null;
    var v = parseFloat(str);
    return isNaN(v) ? null : v * 100;
  }

  function parseCSSScale(str) {
    // Handles CSS individual transform: scale property (e.g. "1.1" or "1.1 1.1")
    if (!str || str === 'none') return null;
    var parts = str.trim().split(/\s+/);
    var sx = parseFloat(parts[0]);
    var sy = parts[1] !== undefined ? parseFloat(parts[1]) : sx;
    if (isNaN(sx)) return null;
    return { scaleX: sx * 100, scaleY: sy * 100 };
  }

  function parseCSSTransform(str) {
    if (!str || str === 'none') return {};
    var result = {};

    // ── matrix3d(16 values) — used by 3D transforms / CSS perspective animations ──
    var mat3dM = str.match(/matrix3d\(\s*([^)]+)\)/);
    if (mat3dM) {
      var v = mat3dM[1].split(',').map(parseFloat);
      if (v.length >= 16) {
        // Column-major: scale from columns 0-2
        result.scaleX = Math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])  * 100;
        result.scaleY = Math.sqrt(v[4]*v[4] + v[5]*v[5] + v[6]*v[6])  * 100;
        result.rotate = Math.atan2(v[1], v[0]) * 180 / Math.PI;
        result.translateX = v[12];
        result.translateY = v[13];
        return result;
      }
    }

    // ── matrix(a,b,c,d,tx,ty) — standard 2D computed transform ──
    var matM = str.match(/matrix\(\s*([\d.e+-]+)[,\s]+([\d.e+-]+)[,\s]+([\d.e+-]+)[,\s]+([\d.e+-]+)[,\s]+([\d.e+-]+)[,\s]+([\d.e+-]+)\s*\)/);
    if (matM) {
      var a = parseFloat(matM[1]); var b = parseFloat(matM[2]);
      var c = parseFloat(matM[3]); var d = parseFloat(matM[4]);
      var tx = parseFloat(matM[5]); var ty = parseFloat(matM[6]);
      result.scaleX = Math.sqrt(a*a + b*b) * 100;
      result.scaleY = Math.sqrt(c*c + d*d) * 100;
      result.rotate = Math.atan2(b, a) * 180 / Math.PI;
      result.translateX = tx;
      result.translateY = ty;
      return result;
    }

    // ── Individual transform functions ──
    var rotM = str.match(/rotate\(([-\d.]+)deg\)/);
    if (rotM) result.rotate = parseFloat(rotM[1]);
    var scaleM = str.match(/scale\(([-\d.]+)(?:,\s*([-\d.]+))?\)/);
    if (scaleM) {
      result.scaleX = parseFloat(scaleM[1]) * 100;
      result.scaleY = scaleM[2] !== undefined ? parseFloat(scaleM[2]) * 100 : result.scaleX;
    }
    var scaleXM = str.match(/scaleX\(([-\d.]+)\)/);
    if (scaleXM) result.scaleX = parseFloat(scaleXM[1]) * 100;
    var scaleYM = str.match(/scaleY\(([-\d.]+)\)/);
    if (scaleYM) result.scaleY = parseFloat(scaleYM[1]) * 100;
    var transM = str.match(/translate\(([-\d.]+)px,?\s*([-\d.]+)?px?\)/);
    if (transM) {
      result.translateX = parseFloat(transM[1]);
      result.translateY = transM[2] !== undefined ? parseFloat(transM[2]) : 0;
    }
    var trans3M = str.match(/translate3d\(([-\d.]+)px,?\s*([-\d.]+)px,?\s*([-\d.]+)px\)/);
    if (trans3M) {
      result.translateX = parseFloat(trans3M[1]);
      result.translateY = parseFloat(trans3M[2]);
    }
    return result;
  }

  function parseCSSFilter(str) {
    if (!str || str === 'none') return null;
    var result = {};
    var blurM = str.match(/blur\(([\d.]+)px\)/);
    if (blurM) result.blur = parseFloat(blurM[1]);
    var brightnessM = str.match(/brightness\(([\d.]+)\)/);
    if (brightnessM) result.brightness = parseFloat(brightnessM[1]);
    return Object.keys(result).length > 0 ? result : null;
  }

  // ── NULL SETUP ─────────────────────────────────────────────────────────────

  function createInteractionNull(comp) {
    var nullLayer = comp.layers.addNull();
    nullLayer.name  = 'INTERACTION NULL';
    nullLayer.label = 2; // Orange — hover cursor

    var tf = nullLayer.property('ADBE Transform Group');
    var posProp = tf.property('ADBE Position');

    // Start off-screen left, vertical center.
    // No keyframes — the null is freely scrubable/draggable in the timeline.
    var startY = comp.height / 2;
    posProp.setValue([-100, startY]);

    return nullLayer;
  }

  function createScrollNull(comp) {
    var nullLayer = comp.layers.addNull();
    nullLayer.name  = 'SCROLL NULL';
    nullLayer.label = 9; // Cyan — scroll depth

    var tf = nullLayer.property('ADBE Transform Group');
    var posProp = tf.property('ADBE Position');

    // Start at Y=0 (page top / no scroll).
    // No keyframes — scrub this null freely: Y=0 is page top, Y=comp.height is full scroll.
    // X is irrelevant; park it at comp center X for clarity.
    posProp.setValue([comp.width / 2, 0]);

    return nullLayer;
  }

  // ── HOVER EXPRESSION BUILDER ───────────────────────────────────────────────
  // Reads INTERACTION NULL X for hover activation.

  function buildHoverExpression(elCX, elHW, fromExpr, toExpr) {
    var transZone = Math.max(elHW, 1);
    return [
      'var nullPos = thisComp.layer("INTERACTION NULL").transform.position;',
      'var nullX = nullPos[0];',
      'var elCX  = ' + elCX.toFixed(1) + ';',
      'var elHW  = ' + elHW.toFixed(1) + ';',
      'var dist  = Math.abs(nullX - elCX);',
      'var t     = clamp((elHW - dist) / ' + transZone.toFixed(1) + ', 0, 1);',
      'var ease  = t * t * (3 - 2 * t);',
      'linear(ease, 0, 1, ' + fromExpr + ', ' + toExpr + ');'
    ].join('\n');
  }

  // ── SCROLL EXPRESSION BUILDER ─────────────────────────────────────────────
  // Reads SCROLL NULL Y as scroll depth proxy.
  // SCROLL NULL Y range: 0 → compHeight  maps to  scrollY range: 0 → maxScrollY
  // When scroll null Y (converted to scrollY) is within [scrollFrom, scrollTo],
  // the property ramps from `fromExpr` to `toExpr`.

  function buildScrollExpression(compHeight, maxScrollY, scrollFrom, scrollTo, fromExpr, toExpr) {
    if (maxScrollY <= 0) maxScrollY = 1;
    var scrollZone = Math.max(scrollTo - scrollFrom, 1);
    return [
      '// SCROLL NULL drives this — move "SCROLL NULL" down in comp to scroll the page',
      'var scrollNullPos = thisComp.layer("SCROLL NULL").transform.position;',
      'var nullY         = scrollNullPos[1];',
      'var compH         = ' + compHeight.toFixed(1) + ';',
      'var maxScroll     = ' + maxScrollY.toFixed(1) + ';',
      'var scrollY       = (nullY / compH) * maxScroll;',
      'var scrollFrom    = ' + scrollFrom.toFixed(1) + ';',
      'var scrollTo      = ' + scrollTo.toFixed(1) + ';',
      'var scrollZone    = ' + scrollZone.toFixed(1) + ';',
      'var t             = clamp((scrollY - scrollFrom) / scrollZone, 0, 1);',
      'var ease          = t * t * (3 - 2 * t);',
      'linear(ease, 0, 1, ' + fromExpr + ', ' + toExpr + ');'
    ].join('\n');
  }

  // ── APPLY HOVER ANIMATIONS ─────────────────────────────────────────────────

  function applyHoverAnimations(layer, el, animations, comp) {
    if (!animations || animations.length === 0) return;
    var elCX = el.rect.x + el.rect.w / 2;
    var elHW = el.rect.w / 2;

    for (var ai = 0; ai < animations.length; ai++) {
      var anim = animations[ai];
      if (anim.trigger !== 'hover') continue;

      try {
        if (anim.property === 'opacity') {
          var fromOp = parseCSSOpacity(anim.from);
          var toOp   = parseCSSOpacity(anim.to);
          if (fromOp === null || toOp === null) continue;
          var opProp = layer.property('ADBE Transform Group').property('ADBE Opacity');
          opProp.expression = buildHoverExpression(elCX, elHW, fromOp.toFixed(1), toOp.toFixed(1));

        } else if (anim.property === 'backgroundColor' || anim.property === 'color') {
          var fromCol = parseCSSColor(anim.from);
          var toCol   = parseCSSColor(anim.to);
          if (!fromCol || !toCol) continue;

          var fromExprC = '[' + fromCol[0].toFixed(4) + ',' + fromCol[1].toFixed(4) + ',' + fromCol[2].toFixed(4) + ']';
          var toExprC   = '[' + toCol[0].toFixed(4)   + ',' + toCol[1].toFixed(4)   + ',' + toCol[2].toFixed(4) + ']';
          var colorHoverExpr = [
            'var nullPos = thisComp.layer("INTERACTION NULL").transform.position;',
            'var nullX = nullPos[0];',
            'var elCX  = ' + elCX.toFixed(1) + ';',
            'var elHW  = ' + elHW.toFixed(1) + ';',
            'var dist  = Math.abs(nullX - elCX);',
            'var t     = clamp((elHW - dist) / ' + Math.max(elHW,1).toFixed(1) + ', 0, 1);',
            'var ease  = t * t * (3 - 2 * t);',
            'var from  = ' + fromExprC + ';',
            'var to    = ' + toExprC   + ';',
            '[',
            '  linear(ease, 0, 1, from[0], to[0]),',
            '  linear(ease, 0, 1, from[1], to[1]),',
            '  linear(ease, 0, 1, from[2], to[2])',
            '];'
          ].join('\n');

          try {
            var contents = layer.property('ADBE Root Vectors Group');
            if (contents) {
              for (var gi = 1; gi <= contents.numProperties; gi++) {
                try {
                  var grp = contents.property(gi);
                  if (!grp) continue;
                  var gc = grp.property('ADBE Vectors Group');
                  if (!gc) continue;
                  for (var fi = 1; fi <= gc.numProperties; fi++) {
                    try {
                      var fp = gc.property(fi);
                      if (fp && fp.matchName === 'ADBE Vector Graphic - Fill') {
                        fp.property('ADBE Vector Fill Color').expression = colorHoverExpr;
                      }
                    } catch(e) {}
                  }
                } catch(e) {}
              }
            }
          } catch(e) {}
          try { layer.property('Color').expression = colorHoverExpr; } catch(e) {}

        } else if (anim.property === 'scale') {
          var fromSc = parseCSSScale(anim.from);
          var toSc   = parseCSSScale(anim.to);
          if (!fromSc || !toSc) continue;
          try {
            var scalePropS = layer.property('ADBE Transform Group').property('ADBE Scale');
            scalePropS.expression = [
              'var nullPos = thisComp.layer("INTERACTION NULL").transform.position;',
              'var nullX = nullPos[0];',
              'var elCX  = ' + elCX.toFixed(1) + ';',
              'var elHW  = ' + elHW.toFixed(1) + ';',
              'var dist  = Math.abs(nullX - elCX);',
              'var t     = clamp((elHW - dist) / ' + Math.max(elHW,1).toFixed(1) + ', 0, 1);',
              'var ease  = t * t * (3 - 2 * t);',
              '[',
              '  linear(ease, 0, 1, ' + fromSc.scaleX.toFixed(1) + ', ' + toSc.scaleX.toFixed(1) + '),',
              '  linear(ease, 0, 1, ' + fromSc.scaleY.toFixed(1) + ', ' + toSc.scaleY.toFixed(1) + ')',
              '];'
            ].join('\n');
          } catch(e) {}

        } else if (anim.property === 'transform') {
          var fromT = parseCSSTransform(anim.from);
          var toT   = parseCSSTransform(anim.to);
          var tf = layer.property('ADBE Transform Group');

          if (fromT.scaleX !== undefined && toT.scaleX !== undefined) {
            var sFrX = fromT.scaleX || 100;
            var sTX  = toT.scaleX   || 100;
            var sFrY = fromT.scaleY !== undefined ? fromT.scaleY : sFrX;
            var sTY  = toT.scaleY   !== undefined ? toT.scaleY   : sTX;
            try {
              var scaleProp = tf.property('ADBE Scale');
              scaleProp.expression = [
                'var nullPos = thisComp.layer("INTERACTION NULL").transform.position;',
                'var nullX = nullPos[0];',
                'var elCX  = ' + elCX.toFixed(1) + ';',
                'var elHW  = ' + elHW.toFixed(1) + ';',
                'var dist  = Math.abs(nullX - elCX);',
                'var t     = clamp((elHW - dist) / ' + Math.max(elHW,1).toFixed(1) + ', 0, 1);',
                'var ease  = t * t * (3 - 2 * t);',
                '[',
                '  linear(ease, 0, 1, ' + sFrX.toFixed(1) + ', ' + sTX.toFixed(1) + '),',
                '  linear(ease, 0, 1, ' + sFrY.toFixed(1) + ', ' + sTY.toFixed(1) + ')',
                '];'
              ].join('\n');
            } catch(e) {}
          }

          if (fromT.rotate !== undefined && toT.rotate !== undefined) {
            try {
              tf.property('ADBE Rotate Z').expression =
                buildHoverExpression(elCX, elHW, fromT.rotate.toFixed(1), toT.rotate.toFixed(1));
            } catch(e) {}
          }

        } else if (anim.property === 'filter' || anim.property === 'backdropFilter') {
          var fromF = parseCSSFilter(anim.from);
          var toF   = parseCSSFilter(anim.to);
          if (!fromF && !toF) continue;
          var fromBlur = (fromF && fromF.blur !== undefined) ? fromF.blur : 0;
          var toBlur   = (toF   && toF.blur   !== undefined) ? toF.blur   : 0;
          if (fromBlur === toBlur) continue;
          var blurHoverExpr = [
            'var nullPos = thisComp.layer("INTERACTION NULL").transform.position;',
            'var nullX = nullPos[0];',
            'var elCX  = ' + elCX.toFixed(1) + ';',
            'var elHW  = ' + elHW.toFixed(1) + ';',
            'var dist  = Math.abs(nullX - elCX);',
            'var t     = clamp((elHW - dist) / ' + Math.max(elHW,1).toFixed(1) + ', 0, 1);',
            'var ease  = t * t * (3 - 2 * t);',
            'linear(ease, 0, 1, ' + fromBlur.toFixed(2) + ', ' + toBlur.toFixed(2) + ');'
          ].join('\n');
          try {
            var blurFx = layer.property('ADBE Effect Parade').addProperty('ADBE Gaussian Blur 2');
            blurFx.property('ADBE Gaussian Blur 2-0001').expression = blurHoverExpr;
            blurFx.property('ADBE Gaussian Blur 2-0003').setValue(1);
          } catch(e) {}
        }
      } catch(animErr) {}
    }
  }

  // ── APPLY SCROLL ANIMATIONS ────────────────────────────────────────────────
  // All scroll expressions now read from SCROLL NULL instead of INTERACTION NULL.

  function applyScrollAnimations(layer, el, animations, comp, maxScrollY) {
    if (!animations || animations.length === 0) return;
    var compH = comp.height;

    for (var ai = 0; ai < animations.length; ai++) {
      var anim = animations[ai];
      if (anim.trigger !== 'scroll') continue;

      var scrollFrom = anim.scrollFrom || 0;
      var scrollTo   = anim.scrollTo   || (maxScrollY || comp.height);

      try {
        if (anim.property === 'opacity') {
          var fromOp = parseCSSOpacity(anim.from);
          var toOp   = parseCSSOpacity(anim.to);
          if (fromOp === null || toOp === null) continue;
          var opProp = layer.property('ADBE Transform Group').property('ADBE Opacity');
          opProp.expression = buildScrollExpression(compH, maxScrollY, scrollFrom, scrollTo, fromOp.toFixed(1), toOp.toFixed(1));

        } else if (anim.property === 'backgroundColor' || anim.property === 'color') {
          var fromCol = parseCSSColor(anim.from);
          var toCol   = parseCSSColor(anim.to);
          if (!fromCol || !toCol) continue;

          var fromExprC2 = '[' + fromCol[0].toFixed(4) + ',' + fromCol[1].toFixed(4) + ',' + fromCol[2].toFixed(4) + ']';
          var toExprC2   = '[' + toCol[0].toFixed(4)   + ',' + toCol[1].toFixed(4)   + ',' + toCol[2].toFixed(4) + ']';

          var scrollColorExpr = [
            '// SCROLL NULL drives this',
            'var scrollNullPos = thisComp.layer("SCROLL NULL").transform.position;',
            'var nullY         = scrollNullPos[1];',
            'var compH         = ' + compH.toFixed(1) + ';',
            'var maxScroll     = ' + (maxScrollY||1).toFixed(1) + ';',
            'var scrollY       = (nullY / compH) * maxScroll;',
            'var scrollFrom    = ' + scrollFrom.toFixed(1) + ';',
            'var scrollTo      = ' + scrollTo.toFixed(1) + ';',
            'var t             = clamp((scrollY - scrollFrom) / Math.max(scrollTo - scrollFrom, 1), 0, 1);',
            'var ease          = t * t * (3 - 2 * t);',
            'var from          = ' + fromExprC2 + ';',
            'var to            = ' + toExprC2   + ';',
            '[',
            '  linear(ease, 0, 1, from[0], to[0]),',
            '  linear(ease, 0, 1, from[1], to[1]),',
            '  linear(ease, 0, 1, from[2], to[2])',
            '];'
          ].join('\n');

          try {
            var contents2 = layer.property('ADBE Root Vectors Group');
            if (contents2) {
              for (var gi2 = 1; gi2 <= contents2.numProperties; gi2++) {
                try {
                  var grp2 = contents2.property(gi2);
                  if (!grp2) continue;
                  var gc2 = grp2.property('ADBE Vectors Group');
                  if (!gc2) continue;
                  for (var fi2 = 1; fi2 <= gc2.numProperties; fi2++) {
                    try {
                      var fp2 = gc2.property(fi2);
                      if (fp2 && fp2.matchName === 'ADBE Vector Graphic - Fill') {
                        fp2.property('ADBE Vector Fill Color').expression = scrollColorExpr;
                      }
                    } catch(e) {}
                  }
                } catch(e) {}
              }
            }
          } catch(e) {}
          try { layer.property('Color').expression = scrollColorExpr; } catch(e) {}

        } else if (anim.property === 'transform') {
          var fromT2 = parseCSSTransform(anim.from);
          var toT2   = parseCSSTransform(anim.to);
          var tf2 = layer.property('ADBE Transform Group');

          if (fromT2.scaleX !== undefined && toT2.scaleX !== undefined) {
            var sFrX2 = fromT2.scaleX || 100; var sTX2 = toT2.scaleX || 100;
            var sFrY2 = fromT2.scaleY !== undefined ? fromT2.scaleY : sFrX2;
            var sTY2  = toT2.scaleY   !== undefined ? toT2.scaleY   : sTX2;
            try {
              var scaleProp2 = tf2.property('ADBE Scale');
              scaleProp2.expression = [
                '// SCROLL NULL drives this',
                'var scrollNullPos = thisComp.layer("SCROLL NULL").transform.position;',
                'var nullY         = scrollNullPos[1];',
                'var compH         = ' + compH.toFixed(1) + ';',
                'var maxScroll     = ' + (maxScrollY||1).toFixed(1) + ';',
                'var scrollY       = (nullY / compH) * maxScroll;',
                'var t             = clamp((scrollY - ' + scrollFrom.toFixed(1) + ') / ' + Math.max(scrollTo-scrollFrom,1).toFixed(1) + ', 0, 1);',
                'var ease          = t * t * (3 - 2 * t);',
                '[',
                '  linear(ease, 0, 1, ' + sFrX2.toFixed(1) + ', ' + sTX2.toFixed(1) + '),',
                '  linear(ease, 0, 1, ' + sFrY2.toFixed(1) + ', ' + sTY2.toFixed(1) + ')',
                '];'
              ].join('\n');
            } catch(e) {}
          }

          if (fromT2.translateX !== undefined && toT2.translateX !== undefined) {
            try {
              var basePosX = el.rect.x + el.rect.w / 2;
              var basePosY = el.rect.y + el.rect.h / 2;
              var fromPX = basePosX + (fromT2.translateX || 0);
              var fromPY = basePosY + (fromT2.translateY || 0);
              var toPX   = basePosX + (toT2.translateX   || 0);
              var toPY   = basePosY + (toT2.translateY   || 0);
              var posScrollExpr = [
                '// SCROLL NULL drives this (translateY/X reveal)',
                'var scrollNullPos = thisComp.layer("SCROLL NULL").transform.position;',
                'var nullY         = scrollNullPos[1];',
                'var compH         = ' + compH.toFixed(1) + ';',
                'var maxScroll     = ' + (maxScrollY||1).toFixed(1) + ';',
                'var scrollY       = (nullY / compH) * maxScroll;',
                'var t             = clamp((scrollY - ' + scrollFrom.toFixed(1) + ') / ' + Math.max(scrollTo-scrollFrom,1).toFixed(1) + ', 0, 1);',
                'var ease          = t * t * (3 - 2 * t);',
                '[',
                '  linear(ease, 0, 1, ' + fromPX.toFixed(1) + ', ' + toPX.toFixed(1) + '),',
                '  linear(ease, 0, 1, ' + fromPY.toFixed(1) + ', ' + toPY.toFixed(1) + ')',
                '];'
              ].join('\n');
              tf2.property('ADBE Position').expression = posScrollExpr;
            } catch(e) {}
          }

        } else if (anim.property === 'filter' || anim.property === 'backdropFilter') {
          var fromFS = parseCSSFilter(anim.from);
          var toFS   = parseCSSFilter(anim.to);
          if (!fromFS && !toFS) continue;
          var fromBS = (fromFS && fromFS.blur !== undefined) ? fromFS.blur : 0;
          var toBS   = (toFS   && toFS.blur   !== undefined) ? toFS.blur   : 0;
          if (fromBS === toBS) continue;
          var blurScrollExpr = [
            '// SCROLL NULL drives this',
            'var scrollNullPos = thisComp.layer("SCROLL NULL").transform.position;',
            'var nullY         = scrollNullPos[1];',
            'var compH         = ' + compH.toFixed(1) + ';',
            'var maxScroll     = ' + (maxScrollY||1).toFixed(1) + ';',
            'var scrollY       = (nullY / compH) * maxScroll;',
            'var scrollFrom    = ' + scrollFrom.toFixed(1) + ';',
            'var scrollTo      = ' + scrollTo.toFixed(1) + ';',
            'var t             = clamp((scrollY - scrollFrom) / Math.max(scrollTo - scrollFrom, 1), 0, 1);',
            'var ease          = t * t * (3 - 2 * t);',
            'linear(ease, 0, 1, ' + fromBS.toFixed(2) + ', ' + toBS.toFixed(2) + ');'
          ].join('\n');
          try {
            var blurFx2 = layer.property('ADBE Effect Parade').addProperty('ADBE Gaussian Blur 2');
            blurFx2.property('ADBE Gaussian Blur 2-0001').expression = blurScrollExpr;
            blurFx2.property('ADBE Gaussian Blur 2-0003').setValue(1);
          } catch(e) {}
        }
      } catch(animErr2) {}
    }
  }

  // ── AUTO-ANIMATION KEYFRAME APPLIER ───────────────────────────────────────

  function applyAutoAnimations(layer, el, animations, compDuration) {
    if (!animations || animations.length === 0) return;

    for (var ai = 0; ai < animations.length; ai++) {
      var anim = animations[ai];
      if (anim.trigger !== 'auto') continue;

      var dur    = anim.duration || 1;
      var delay  = anim.delay   || 0;
      var iter   = anim.iterationCount;
      var kfs    = anim.keyframes;
      if (!kfs || kfs.length < 2) continue;

      var cycles;
      if (iter === -1 || iter === Infinity) {
        cycles = Math.ceil((compDuration - delay) / dur);
        if (cycles < 1) cycles = 1;
        if (cycles > 60) cycles = 60;
      } else {
        cycles = Math.max(1, iter);
      }

      var tf = layer.property('ADBE Transform Group');

      for (var ci = 0; ci < cycles; ci++) {
        var cycleStart = delay + ci * dur;
        for (var ki = 0; ki < kfs.length; ki++) {
          var kf = kfs[ki];
          var t  = cycleStart + kf.offset * dur;
          if (!kf.props) continue;

          if (kf.props.opacity !== undefined) {
            var opVal = parseFloat(kf.props.opacity);
            if (!isNaN(opVal)) {
              try { tf.property('ADBE Opacity').setValueAtTime(t, opVal * 100); } catch(e) {}
            }
          }

          if (kf.props.transform) {
            var tv = parseCSSTransform(kf.props.transform);
            try {
              if (tv.rotate !== undefined) tf.property('ADBE Rotate Z').setValueAtTime(t, tv.rotate);
              if (tv.scaleX !== undefined) {
                var sy = tv.scaleY !== undefined ? tv.scaleY : tv.scaleX;
                tf.property('ADBE Scale').setValueAtTime(t, [tv.scaleX, sy]);
              }
              if (tv.translateX !== undefined) {
                tf.property('ADBE Position').setValueAtTime(t, [
                  (el.rect.x + el.rect.w / 2) + tv.translateX,
                  (el.rect.y + el.rect.h / 2) + (tv.translateY || 0)
                ]);
              }
            } catch(e) {}
          }

          if (kf.props.backgroundColor || kf.props.color) {
            var colorStr = kf.props.backgroundColor || kf.props.color;
            var col = parseCSSColor(colorStr);
            if (col) {
              try {
                var contents3 = layer.property('ADBE Root Vectors Group');
                if (contents3) {
                  var group3 = contents3.property(1);
                  if (group3) {
                    var gc3 = group3.property('ADBE Vectors Group');
                    if (gc3) {
                      for (var fi3 = 1; fi3 <= gc3.numProperties; fi3++) {
                        try {
                          var gp3 = gc3.property(fi3);
                          if (gp3 && gp3.matchName === 'ADBE Vector Graphic - Fill') {
                            gp3.property('ADBE Vector Fill Color').setValueAtTime(t, col);
                          }
                        } catch(e) {}
                      }
                    }
                  }
                }
              } catch(e) {}
              try { layer.property('ADBE Solid Color').setValueAtTime(t, col); } catch(e) {}
            }
          }
        }
      }

      if ((iter === -1 || iter === Infinity) && cycles > 1) {
        // Apply loopOut("cycle") to ALL animated properties for infinite animations,
        // not just opacity. This is the fix for looping transforms/scale/position.
        var loopProps = [
          tf.property('ADBE Opacity'),
          tf.property('ADBE Scale'),
          tf.property('ADBE Rotate Z'),
          tf.property('ADBE Position')
        ];
        for (var lpi = 0; lpi < loopProps.length; lpi++) {
          try {
            var lp = loopProps[lpi];
            if (lp && lp.numKeys > 1) {
              try { lp.expression = 'loopOut("cycle");'; } catch(e) {}
            }
          } catch(e) {}
        }
      }
    }
  }

  // ── SHAPE LAYER ───────────────────────────────────────────────────────────

  function addRect(comp, el) {
    var layer     = comp.layers.addShape();
    layer.name    = (el.type === 'icon' ? 'ico' : el.type === 'placeholder' ? 'ph' : 'shp') + ':' + (el.tag || 'div');
    var contents  = layer.property("ADBE Root Vectors Group");
    var group     = contents.addProperty("ADBE Vector Group");
    var gc        = group.property("ADBE Vectors Group");
    var rectShape = gc.addProperty("ADBE Vector Shape - Rect");
    rectShape.property("ADBE Vector Rect Size").setValue([el.rect.w, el.rect.h]);
    var radius = parseRadius(el.radius, el.rect.w, el.rect.h);
    if (radius > 0) {
      rectShape.property("ADBE Vector Rect Roundness").setValue(Math.min(radius, Math.min(el.rect.w, el.rect.h) / 2));
    }
    var fillColor = el.bg || el.iconColor || null;
    if (fillColor) {
      var fill = gc.addProperty("ADBE Vector Graphic - Fill");
      fill.property("ADBE Vector Fill Color").setValue(toAEC(fillColor));
      if (fillColor.a !== undefined && fillColor.a < 1) {
        fill.property("ADBE Vector Fill Opacity").setValue(fillColor.a * 100);
      }
    }
    if (el.border && el.border.color) {
      var stroke = gc.addProperty("ADBE Vector Graphic - Stroke");
      stroke.property("ADBE Vector Stroke Color").setValue(toAEC(el.border.color));
      stroke.property("ADBE Vector Stroke Width").setValue(el.border.width || 1);
    }
    var tf = layer.property("ADBE Transform Group");
    tf.property("ADBE Anchor Point").setValue([0, 0]);
    tf.property("ADBE Position").setValue([el.rect.x + el.rect.w / 2, el.rect.y + el.rect.h / 2]);
    tf.property("ADBE Opacity").setValue((el.opacity || 1) * 100);
    return layer;
  }

  // ── TEXT LAYER ────────────────────────────────────────────────────────────
  // For button text (isButtonText=true): create a shape layer with a
  // centered text animator instead of addBoxText, so positioning is exact.
  // For normal text: use addBoxText positioned from rect coords directly.

  function addText(comp, el) {
    var fontSize   = Math.max(el.fontSize || 14, 8);
    var isBold     = el.fontWeight && el.fontWeight >= 600;
    var isButton   = el.isButtonText === true;
    var fontName   = (isBold || isButton) ? 'Arial-BoldMT' : 'ArialMT';
    var textStr    = (el.text || ' ').slice(0, 200);

    var cx = el.rect.x + el.rect.w / 2;
    var cy = el.rect.y + el.rect.h / 2;

    // Use a point text layer anchored at center — avoids all sr.left/sr.top issues
    var layer = comp.layers.addText(textStr);
    layer.name = (isButton ? 'btn:' : 'txt:') + textStr.slice(0, 24);

    var sourceText = layer.property('Source Text');
    var doc = sourceText.value;
    doc.fontSize    = fontSize;
    doc.fillColor   = el.textColor ? toAEC(el.textColor) : [1, 1, 1];
    doc.applyFill   = true;
    doc.applyStroke = false;
    doc.font        = fontName;
    // Always center button text; respect textAlign for normal text
    try {
      if (isButton || el.textAlign === 'center') {
        doc.justification = ParagraphJustification.CENTER_JUSTIFY;
      } else if (el.textAlign === 'right') {
        doc.justification = ParagraphJustification.RIGHT_JUSTIFY;
      } else {
        doc.justification = ParagraphJustification.LEFT_JUSTIFY;
      }
    } catch(e) {}
    sourceText.setValue(doc);

    var tf = layer.property('ADBE Transform Group');
    // Anchor at center of the text layer's own bounding box
    try {
      var sr = layer.sourceRectAtTime(0, false);
      // sr.left/top are relative to anchor, width/height are text bounds
      // Center anchor inside the text bounds
      tf.property('ADBE Anchor Point').setValue([
        sr.left + sr.width  / 2,
        sr.top  + sr.height / 2
      ]);
    } catch(e) {
      tf.property('ADBE Anchor Point').setValue([0, 0]);
    }
    // Place at the visual center of the element's rect
    tf.property('ADBE Position').setValue([cx, cy]);
    tf.property('ADBE Opacity').setValue(Math.round((el.opacity || 1) * 100));
    return layer;
  }

  // ── MASK ─────────────────────────────────────────────────────────────────

  function applyMask(layer, tgtW, tgtH, radius, srcW, srcH, scale) {
    try {
      var sf    = scale / 100;
      var mW    = tgtW / sf;
      var mH    = tgtH / sf;
      var mR    = radius / sf;
      var mMaxR = Math.min(mW, mH) / 2;
      if (mR > mMaxR) mR = mMaxR;
      if (mR < 0) mR = 0;
      var cx = srcW / 2; var cy = srcH / 2;
      var x0 = cx - mW/2; var y0 = cy - mH/2;
      var x1 = cx + mW/2; var y1 = cy + mH/2;
      var k  = mR * 0.5523;
      var topLen  = mW - 2 * mR;
      var sideLen = mH - 2 * mR;
      var verts, inT, outT;
      if (mR <= 0) {
        verts = [[x0,y0],[x1,y0],[x1,y1],[x0,y1]];
        inT   = [[0,0],[0,0],[0,0],[0,0]];
        outT  = [[0,0],[0,0],[0,0],[0,0]];
      } else if (topLen <= 0 && sideLen <= 0) {
        var r = mMaxR; k = r * 0.5523;
        verts = [[cx,y0],[x1,cy],[cx,y1],[x0,cy]];
        inT   = [[-k,0],[0,-k],[k,0],[0,k]];
        outT  = [[k,0],[0,k],[-k,0],[0,-k]];
      } else if (topLen <= 0) {
        verts = [[cx,y0],[x1,y0+mR],[x1,y1-mR],[cx,y1],[x0,y1-mR],[x0,y0+mR]];
        inT   = [[-k,0],[0,-k],[0,0],[k,0],[0,k],[0,0]];
        outT  = [[k,0],[0,0],[0,k],[-k,0],[0,0],[0,-k]];
      } else if (sideLen <= 0) {
        verts = [[x0+mR,y0],[x1-mR,y0],[x1,cy],[x1-mR,y1],[x0+mR,y1],[x0,cy]];
        inT   = [[-k,0],[0,0],[0,-k],[k,0],[0,0],[0,k]];
        outT  = [[0,0],[k,0],[0,k],[0,0],[-k,0],[0,-k]];
      } else {
        verts = [[x0+mR,y0],[x1-mR,y0],[x1,y0+mR],[x1,y1-mR],[x1-mR,y1],[x0+mR,y1],[x0,y1-mR],[x0,y0+mR]];
        inT   = [[-k,0],[-k,0],[0,-k],[0,-k],[k,0],[k,0],[0,k],[0,k]];
        outT  = [[k,0],[k,0],[0,k],[0,k],[-k,0],[-k,0],[0,-k],[0,-k]];
      }
      var masks = layer.property("ADBE Mask Parade");
      if (!masks) return;
      var mask = masks.addProperty("ADBE Mask Atom");
      if (!mask) return;
      try { mask.mode = MaskMode.ADD; } catch(e) {}
      var shape = new Shape();
      shape.vertices    = verts;
      shape.inTangents  = inT;
      shape.outTangents = outT;
      shape.closed      = true;
      mask.property("ADBE Mask Shape").setValue(shape);
    } catch (e) {
      $.writeln('applyMask error: ' + e.toString());
    }
  }

  // ── IMAGE LAYER ───────────────────────────────────────────────────────────

  function addImageLayer(comp, el, filePath, debugLines) {
    try {
      var file = new File(filePath);
      if (!file.exists) { debugLines.push('  NOT_FOUND: ' + filePath); return null; }
      var item = null;
      for (var i = 1; i <= app.project.numItems; i++) {
        var pi2 = app.project.item(i);
        if (pi2 instanceof FootageItem && pi2.file && pi2.file.fsName === file.fsName) {
          item = pi2; break;
        }
      }
      if (!item) {
        var importOpts = new ImportOptions(file);
        item = app.project.importFile(importOpts);
        $.sleep(150);
      }
      var layer = comp.layers.add(item);
      layer.name = (el.type === 'icon' ? 'ico' : 'img') + ':' + (el.imageKey || el.tag || 'image');
      var tgtW = el.rect.w; var tgtH = el.rect.h;
      var srcW = (item.width  > 0) ? item.width  : tgtW;
      var srcH = (item.height > 0) ? item.height : tgtH;
      var scaleX = tgtW / srcW * 100;
      var scaleY = tgtH / srcH * 100;
      var scale  = (scaleX > scaleY) ? scaleX : scaleY;
      if (!isFinite(scale) || scale <= 0) scale = 100;
      var tf = layer.property("ADBE Transform Group");
      tf.property("ADBE Anchor Point").setValue([srcW / 2, srcH / 2]);
      tf.property("ADBE Position").setValue([el.rect.x + tgtW / 2, el.rect.y + tgtH / 2]);
      tf.property("ADBE Scale").setValue([scale, scale]);
      tf.property("ADBE Opacity").setValue((el.opacity || 1) * 100);
      var radius = parseRadius(el.radius || '0px', tgtW, tgtH);
      if (radius > 0) applyMask(layer, tgtW, tgtH, radius, srcW, srcH, scale);
      debugLines.push('  src=' + srcW + 'x' + srcH + ' tgt=' + tgtW + 'x' + tgtH);
      return layer;
    } catch (e) {
      debugLines.push('  EXCEPTION: ' + e.toString());
      return null;
    }
  }

  // ── VIDEO LAYER ───────────────────────────────────────────────────────────

  function addVideoLayer(comp, el, filePath, debugLines) {
    try {
      var file = new File(filePath);
      if (!file.exists) { debugLines.push('  VIDEO_NOT_FOUND: ' + filePath); return null; }
      var item = null;
      for (var i = 1; i <= app.project.numItems; i++) {
        var pi3 = app.project.item(i);
        if (pi3 instanceof FootageItem && pi3.file && pi3.file.fsName === file.fsName) {
          item = pi3; break;
        }
      }
      if (!item) {
        var importOpts2 = new ImportOptions(file);
        item = app.project.importFile(importOpts2);
        $.sleep(150);
      }
      var layer = comp.layers.add(item);
      layer.name = 'vid:' + (el.videoKey || el.tag || 'video');
      var tgtW = el.rect.w; var tgtH = el.rect.h;
      var srcW = (item.width  > 0) ? item.width  : tgtW;
      var srcH = (item.height > 0) ? item.height : tgtH;
      var scaleX2 = tgtW / srcW * 100;
      var scaleY2 = tgtH / srcH * 100;
      var scale2  = (scaleX2 > scaleY2) ? scaleX2 : scaleY2;
      if (!isFinite(scale2) || scale2 <= 0) scale2 = 100;
      var tf = layer.property("ADBE Transform Group");
      tf.property("ADBE Anchor Point").setValue([srcW / 2, srcH / 2]);
      tf.property("ADBE Position").setValue([el.rect.x + tgtW / 2, el.rect.y + tgtH / 2]);
      tf.property("ADBE Scale").setValue([scale2, scale2]);
      tf.property("ADBE Opacity").setValue((el.opacity || 1) * 100);
      var radius2 = parseRadius(el.radius || '0px', tgtW, tgtH);
      if (radius2 > 0) applyMask(layer, tgtW, tgtH, radius2, srcW, srcH, scale2);
      debugLines.push('  VIDEO OK: ' + srcW + 'x' + srcH);
      return layer;
    } catch (e) {
      debugLines.push('  VIDEO_EXCEPTION: ' + e.toString());
      return null;
    }
  }

  // ── SVG PATH PARSER ───────────────────────────────────────────────────────

  function parseSVGPath(d) {
    var subpaths = [];
    if (!d) return subpaths;
    var tokens = [];
    var re = /([MmLlHhVvCcSsQqTtAaZz])|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)/g;
    var m;
    while ((m = re.exec(d)) !== null) tokens.push(m[0]);
    var i = 0;
    var cx2 = 0, cy2 = 0, mx = 0, my = 0, lastCmd = '', lastCPx = 0, lastCPy = 0;
    var verts = [], inT = [], outT = [], closed = false;
    function num() { return parseFloat(tokens[i++]); }
    function isNum(t) { return t !== undefined && /^[+-]?[\d.]/.test(t); }
    function commitSubpath() {
      if (verts.length > 0) subpaths.push({ vertices:verts, inTangents:inT, outTangents:outT, closed:closed });
      verts = []; inT = []; outT = []; closed = false;
    }
    function addPt(x, y, itx, ity, otx, oty) {
      verts.push([x,y]); inT.push([itx,ity]); outT.push([otx,oty]);
    }
    while (i < tokens.length) {
      var cmd = tokens[i];
      if (isNum(cmd)) { cmd = lastCmd === 'M' ? 'L' : lastCmd === 'm' ? 'l' : lastCmd; }
      else i++;
      lastCmd = cmd;
      if (cmd === 'Z' || cmd === 'z') {
        closed = true; commitSubpath(); cx2 = mx; cy2 = my;
      } else if (cmd === 'M' || cmd === 'm') {
        if (verts.length > 0) commitSubpath();
        var absM = cmd === 'M'; var xM = num(); var yM = num();
        if (!absM) { xM += cx2; yM += cy2; }
        cx2 = xM; cy2 = yM; mx = xM; my = yM; addPt(xM, yM, 0, 0, 0, 0);
      } else if (cmd === 'L' || cmd === 'l') {
        var absL = cmd === 'L';
        while (isNum(tokens[i])) { var xL = num(); var yL = num(); if (!absL) { xL += cx2; yL += cy2; } addPt(xL, yL, 0, 0, 0, 0); cx2 = xL; cy2 = yL; }
      } else if (cmd === 'H' || cmd === 'h') {
        var absH = cmd === 'H';
        while (isNum(tokens[i])) { var xH = num(); if (!absH) xH += cx2; addPt(xH, cy2, 0, 0, 0, 0); cx2 = xH; }
      } else if (cmd === 'V' || cmd === 'v') {
        var absV = cmd === 'V';
        while (isNum(tokens[i])) { var yV = num(); if (!absV) yV += cy2; addPt(cx2, yV, 0, 0, 0, 0); cy2 = yV; }
      } else if (cmd === 'C' || cmd === 'c') {
        var absC = (cmd === 'C');
        while (isNum(tokens[i])) {
          var x1c=num(); var y1c=num(); var x2c=num(); var y2c=num(); var xc=num(); var yc=num();
          if (!absC) { x1c+=cx2; y1c+=cy2; x2c+=cx2; y2c+=cy2; xc+=cx2; yc+=cy2; }
          if (verts.length > 0) outT[outT.length-1] = [x1c-cx2, y1c-cy2];
          verts.push([xc,yc]); inT.push([x2c-xc, y2c-yc]); outT.push([0,0]);
          lastCPx=x2c; lastCPy=y2c; cx2=xc; cy2=yc;
        }
      } else if (cmd === 'S' || cmd === 's') {
        var absS = cmd === 'S';
        while (isNum(tokens[i])) {
          var x1s=2*cx2-lastCPx; var y1s=2*cy2-lastCPy;
          var x2s=num(); var y2s=num(); var xs=num(); var ys=num();
          if (!absS) { x2s+=cx2; y2s+=cy2; xs+=cx2; ys+=cy2; }
          if (verts.length > 0) outT[outT.length-1] = [x1s-cx2, y1s-cy2];
          addPt(xs, ys, 0, 0, 0, 0); inT[inT.length-1]=[x2s-xs, y2s-ys];
          lastCPx=x2s; lastCPy=y2s; cx2=xs; cy2=ys;
        }
      } else if (cmd === 'Q' || cmd === 'q') {
        var absQ = cmd === 'Q';
        while (isNum(tokens[i])) {
          var qx1=num(); var qy1=num(); var xq=num(); var yq=num();
          if (!absQ) { qx1+=cx2; qy1+=cy2; xq+=cx2; yq+=cy2; }
          var cpx1=cx2+2/3*(qx1-cx2); var cpy1=cy2+2/3*(qy1-cy2);
          var cpx2=xq+2/3*(qx1-xq);  var cpy2=yq+2/3*(qy1-yq);
          if (verts.length > 0) outT[outT.length-1] = [cpx1-cx2, cpy1-cy2];
          addPt(xq, yq, 0, 0, 0, 0); inT[inT.length-1]=[cpx2-xq, cpy2-yq];
          lastCPx=qx1; lastCPy=qy1; cx2=xq; cy2=yq;
        }
      } else if (cmd === 'T' || cmd === 't') {
        var absT2 = cmd === 'T';
        while (isNum(tokens[i])) {
          var qx1t=2*cx2-lastCPx; var qy1t=2*cy2-lastCPy;
          var xtt=num(); var ytt=num();
          if (!absT2) { xtt+=cx2; ytt+=cy2; }
          var cpx1t=cx2+2/3*(qx1t-cx2); var cpy1t=cy2+2/3*(qy1t-cy2);
          var cpx2t=xtt+2/3*(qx1t-xtt); var cpy2t=ytt+2/3*(qy1t-ytt);
          if (verts.length > 0) outT[outT.length-1]=[cpx1t-cx2, cpy1t-cy2];
          addPt(xtt, ytt, 0, 0, 0, 0); inT[inT.length-1]=[cpx2t-xtt, cpy2t-ytt];
          lastCPx=qx1t; lastCPy=qy1t; cx2=xtt; cy2=ytt;
        }
      } else if (cmd === 'A' || cmd === 'a') {
        var absA = cmd === 'A';
        while (isNum(tokens[i])) {
          num(); num(); num(); num(); num();
          var xa=num(); var ya=num();
          if (!absA) { xa+=cx2; ya+=cy2; }
          addPt(xa, ya, 0, 0, 0, 0); cx2=xa; cy2=ya;
        }
      }
    }
    if (verts.length > 0) commitSubpath();
    return subpaths;
  }

  // ── VECTOR ICON LAYER ─────────────────────────────────────────────────────

  function addVectorIconLayer(comp, el) {
    var paths    = el.svgPaths;
    var iconColor = el.iconColor || { r:255, g:255, b:255 };
    var rw = el.rect.w; var rh = el.rect.h;
    var cx2 = el.rect.x + rw / 2; var cy2 = el.rect.y + rh / 2;
    var vbW = (paths[0] && paths[0].vbW > 0) ? paths[0].vbW : rw;
    var vbH = (paths[0] && paths[0].vbH > 0) ? paths[0].vbH : rh;
    var vbX2 = (paths[0]) ? paths[0].vbX : 0;
    var vbY2 = (paths[0]) ? paths[0].vbY : 0;
    var scaleX3 = rw / vbW; var scaleY3 = rh / vbH;
    var layer = comp.layers.addShape();
    layer.name = 'vec:' + (el.cls || el.id || el.tag || 'icon');
    var contents2 = layer.property('ADBE Root Vectors Group');
    for (var pi4 = 0; pi4 < paths.length; pi4++) {
      var pd = paths[pi4];
      var subpaths = parseSVGPath(pd.d);
      if (!subpaths || subpaths.length === 0) continue;
      var group2 = contents2.addProperty('ADBE Vector Group');
      group2.name = 'path' + (pi4 + 1);
      var gc2 = group2.property('ADBE Vectors Group');
      for (var spi = 0; spi < subpaths.length; spi++) {
        var sp = subpaths[spi];
        if (sp.vertices.length < 2) continue;
        var scaledVerts = []; var scaledIn = []; var scaledOut = []; var validPath = true;
        for (var vi = 0; vi < sp.vertices.length; vi++) {
          var vx = (sp.vertices[vi][0] - vbX2) * scaleX3 - rw / 2;
          var vy = (sp.vertices[vi][1] - vbY2) * scaleY3 - rh / 2;
          var itx = sp.inTangents[vi][0]  * scaleX3; var ity = sp.inTangents[vi][1]  * scaleY3;
          var otx = sp.outTangents[vi][0] * scaleX3; var oty = sp.outTangents[vi][1] * scaleY3;
          if (!isFinite(vx)||!isFinite(vy)||!isFinite(itx)||!isFinite(ity)||!isFinite(otx)||!isFinite(oty)) { validPath=false; break; }
          scaledVerts.push([vx,vy]); scaledIn.push([itx,ity]); scaledOut.push([otx,oty]);
        }
        if (!validPath || scaledVerts.length < 2) continue;
        var pathProp = gc2.addProperty('ADBE Vector Shape - Group');
        var shape2 = new Shape();
        shape2.vertices    = scaledVerts;
        shape2.inTangents  = scaledIn;
        shape2.outTangents = scaledOut;
        shape2.closed      = sp.closed;
        try { pathProp.property('ADBE Vector Shape').setValue(shape2); }
        catch(e) { try { pathProp.property(2).setValue(shape2); } catch(e2) {} }
      }
      var fillColor2 = pd.fill ? toAEC(pd.fill) : toAEC(iconColor);
      var fill2 = gc2.addProperty('ADBE Vector Graphic - Fill');
      fill2.property('ADBE Vector Fill Color').setValue(fillColor2);
      try { fill2.property('ADBE Vector Fill Rule').setValue((pd.fillRule === 'evenodd') ? 2 : 1); } catch(e) {}
      if (pd.stroke && pd.strokeWidth > 0) {
        var stroke2 = gc2.addProperty('ADBE Vector Graphic - Stroke');
        stroke2.property('ADBE Vector Stroke Color').setValue(toAEC(pd.stroke));
        stroke2.property('ADBE Vector Stroke Width').setValue(pd.strokeWidth * scaleX3);
      }
    }
    var tf2 = layer.property('ADBE Transform Group');
    tf2.property('ADBE Anchor Point').setValue([0, 0]);
    tf2.property('ADBE Position').setValue([cx2, cy2]);
    tf2.property('ADBE Opacity').setValue((el.opacity || 1) * 100);
    return layer;
  }

  // ── GRADIENT LAYER ────────────────────────────────────────────────────────

  function addGradientLayer(comp, el, imageMap, debugLines) {
    if (el.imageKey && imageMap[el.imageKey]) {
      debugLines.push('grad-png: ' + el.imageKey);
      var lyr = addImageLayer(comp, el, imageMap[el.imageKey], debugLines);
      if (lyr) { debugLines.push('  -> OK'); return lyr; }
    }
    var grad = el.gradient;
    if (grad && grad.stops && grad.stops.length >= 2) {
      var stops   = grad.stops;
      var color1  = toAEC(stops[0].color);
      var color2  = toAEC(stops[stops.length - 1].color);
      var w = el.rect.w; var h = el.rect.h;
      var cx3 = el.rect.x + w / 2; var cy3 = el.rect.y + h / 2;
      var angleRad = (grad.angle - 90) * Math.PI / 180;
      var halfLen  = Math.sqrt(w*w + h*h) / 2;
      var sx = cx3 - Math.cos(angleRad)*halfLen; var sy2 = cy3 - Math.sin(angleRad)*halfLen;
      var ex = cx3 + Math.cos(angleRad)*halfLen; var ey  = cy3 + Math.sin(angleRad)*halfLen;
      try {
        var solid = comp.layers.addSolid(color1, 'grad:' + (el.tag||'div'), w, h, 1);
        solid.property('ADBE Transform Group').property('ADBE Anchor Point').setValue([w/2, h/2]);
        solid.property('ADBE Transform Group').property('ADBE Position').setValue([cx3, cy3]);
        solid.property('ADBE Transform Group').property('ADBE Opacity').setValue((el.opacity||1)*100);
        var effects = solid.property('ADBE Effect Parade');
        var ramp    = effects.addProperty('ADBE Ramp');
        ramp.property('ADBE Ramp-0001').setValue([sx, sy2]);
        ramp.property('ADBE Ramp-0002').setValue(color1);
        ramp.property('ADBE Ramp-0003').setValue([ex, ey]);
        ramp.property('ADBE Ramp-0004').setValue(color2);
        ramp.property('ADBE Ramp-0005').setValue(1);
        debugLines.push('grad-ramp angle=' + grad.angle);
        return solid;
      } catch(e) { debugLines.push('grad-ramp FAILED: ' + e.toString()); }
    }
    var fallbackColor = (grad && grad.stops && grad.stops.length > 0)
      ? toAEC(grad.stops[0].color) : (el.bg ? toAEC(el.bg) : [0.1, 0.1, 0.1]);
    var w2 = el.rect.w; var h2 = el.rect.h;
    var solid2 = comp.layers.addSolid(fallbackColor, 'grad-fb:' + (el.tag||'div'), w2, h2, 1);
    solid2.property('ADBE Transform Group').property('ADBE Anchor Point').setValue([w2/2, h2/2]);
    solid2.property('ADBE Transform Group').property('ADBE Position').setValue([el.rect.x+w2/2, el.rect.y+h2/2]);
    solid2.property('ADBE Transform Group').property('ADBE Opacity').setValue((el.opacity||1)*100);
    debugLines.push('grad-fallback: ' + (el.imageKey || 'no-key'));
    return solid2;
  }

  // ── GUIDE TEXT LAYER ─────────────────────────────────────────────────────
  // Creates a locked label at the top of comp explaining both nulls.

  function createGuideLabel(comp) {
    try {
      var guideText = [
        'DUAL NULL SYSTEM  |  v24',
        '  INTERACTION NULL (orange) = Hover cursor  |  Move X over elements to trigger hover animations',
        '  SCROLL NULL (cyan)        = Page scroll   |  Move Y down to reveal scroll animations (0=top, ' + comp.height + 'px=bottom)'
      ].join('\n');

      var lyr = comp.layers.addBoxText([comp.width, 60], guideText);
      lyr.name = '-- NULL GUIDE (read only) --';
      lyr.locked = true;
      lyr.label  = 9; // Cyan to match SCROLL NULL

      var sourceText = lyr.property('Source Text');
      var doc = sourceText.value;
      doc.fontSize  = 11;
      doc.fillColor = [0.9, 0.9, 0.9];
      doc.applyFill = true;
      doc.font      = 'ArialMT';
      sourceText.setValue(doc);

      var tf = lyr.property('ADBE Transform Group');
      tf.property('ADBE Anchor Point').setValue([0, 0]);
      tf.property('ADBE Position').setValue([10, 10]);
      tf.property('ADBE Opacity').setValue(60);

      return lyr;
    } catch(e) { return null; }
  }

  // ── MAIN ──────────────────────────────────────────────────────────────────

  var jsonFile = File.openDialog("Select ui_extract.json", "*.json");
  if (!jsonFile) { alert("No file selected."); return; }
  jsonFile.open("r");
  var raw = jsonFile.read();
  jsonFile.close();

  var data     = JSON.parse(raw);
  var vp       = data.viewport;
  var elements = data.elements;
  var meta     = data.meta || {};

  var compDuration = meta.compDuration || 10;
  if (compDuration < 10)  compDuration = 10;
  if (compDuration > 120) compDuration = 120;

  var maxScrollY = meta.maxScrollY || 0;
  if (maxScrollY > 0 && compDuration < 20) compDuration = 20;

  // ── Image map ──────────────────────────────────────────────────────────────
  var imageMap  = {};
  var hasImages = data.imageManifest && data.imageManifest.length > 0;
  if (hasImages) {
    var loadMap = confirm(
      data.imageManifest.length + " images/videos captured.\n\n"
      + "Click OK to select image_map.json.\n"
      + "Click Cancel to use grey placeholders."
    );
    if (loadMap) {
      var mapFile = File.openDialog("Select image_map.json", "*.json");
      if (mapFile) {
        mapFile.open("r"); var mapRaw = mapFile.read(); mapFile.close();
        try { imageMap = JSON.parse(mapRaw); } catch (e) { alert("Could not parse image_map.json:\n" + e.toString()); }
      }
    }
  }

  // ── Video map ──────────────────────────────────────────────────────────────
  var videoMap = {};
  var hasVideos = false;
  for (var vi2 = 0; vi2 < elements.length; vi2++) {
    if (elements[vi2].tag === 'video' && elements[vi2].videoKey) { hasVideos = true; break; }
  }
  if (hasVideos) {
    var loadVid = confirm("Video elements detected.\n\nClick OK to select video_map.json.\nClick Cancel to skip videos.");
    if (loadVid) {
      var vidMapFile = File.openDialog("Select video_map.json", "*.json");
      if (vidMapFile) {
        vidMapFile.open("r"); var vidMapRaw = vidMapFile.read(); vidMapFile.close();
        try { videoMap = JSON.parse(vidMapRaw); } catch(e) { alert("Could not parse video_map.json:\n" + e.toString()); }
      }
    }
  }

  dpr = (vp.dpr && vp.dpr > 0) ? vp.dpr : 1;

  // ── Create comp ────────────────────────────────────────────────────────────
  // AE hard limits: width and height must be 4–30000px.
  var AE_MAX_DIM = 30000;
  var compPageH = (vp.pageHeight && vp.pageHeight > 4 && vp.pageHeight <= AE_MAX_DIM)
                  ? vp.pageHeight
                  : (vp.height && vp.height > 4 ? vp.height : 1080);
  var compWidth = (vp.width && vp.width > 4 && vp.width <= AE_MAX_DIM) ? vp.width : 1920;
  var comp = app.project.items.addComp(
    "UI Import - " + (vp.title || vp.url || "web"),
    compWidth, compPageH, 1, compDuration, 30
  );

  if (data.bodyBg) {
    var bgSolid = comp.layers.addSolid(toAEC(data.bodyBg), "BG", compWidth, compPageH, 1);
    bgSolid.moveToEnd();
  }

  app.beginUndoGroup("Build UI v24");

  // ── Create BOTH nulls ──────────────────────────────────────────────────────
  var scrollNull      = createScrollNull(comp);
  var interactionNull = createInteractionNull(comp);
  var guideLabel      = createGuideLabel(comp);

  var imgLoaded   = 0;
  var imgFallback = 0;
  var vidLoaded   = 0;
  var animApplied = 0;
  var debugLines  = [];

  var typeOrder = { 'gradient':0, 'shape':1, 'placeholder':2, 'icon':3, 'text':4 };
  elements.sort(function(a, b) {
    var za = a.z || 0; var zb = b.z || 0;
    if (za !== zb) return za - zb;
    return (typeOrder[a.type] || 0) - (typeOrder[b.type] || 0);
  });

  for (var i = 0; i < elements.length; i++) {
    var el = elements[i];
    var builtLayer = null;

    try {

      if (el.type === 'text') {
        builtLayer = addText(comp, el);

      } else if (el.type === 'gradient') {
        builtLayer = addGradientLayer(comp, el, imageMap, debugLines);

      } else if (el.type === 'placeholder' || el.type === 'icon') {
        var placed = false;

        if (el.tag === 'video') {
          if (el.videoKey && videoMap[el.videoKey]) {
            builtLayer = addVideoLayer(comp, el, videoMap[el.videoKey], debugLines);
            if (builtLayer) { vidLoaded++; placed = true; }
          }
          if (!placed && el.imageKey && imageMap[el.imageKey]) {
            builtLayer = addImageLayer(comp, el, imageMap[el.imageKey], debugLines);
            if (builtLayer) { imgLoaded++; placed = true; }
          }
          if (!placed) { builtLayer = addRect(comp, el); imgFallback++; placed = true; }

        } else {
          if (el.type === 'icon' && el.svgPaths && el.svgPaths.length > 0) {
            try {
              var vlyr = addVectorIconLayer(comp, el);
              if (vlyr) { builtLayer = vlyr; placed = true; debugLines.push('vec: ' + (el.cls||el.id||'icon')); }
            } catch(ve) { debugLines.push('vec FAILED: ' + ve.toString()); }
          }
          if (!placed && el.imageKey && imageMap[el.imageKey]) {
            var lyr2 = addImageLayer(comp, el, imageMap[el.imageKey], debugLines);
            if (lyr2) { builtLayer = lyr2; imgLoaded++; placed = true; }
          } else if (!placed) {
            debugLines.push((el.imageKey || 'no-key') + ' -> NO_MAP_ENTRY');
          }
          if (!placed) { builtLayer = addRect(comp, el); imgFallback++; }
        }

      } else {
        builtLayer = addRect(comp, el);
      }

      // ── Apply all animations ────────────────────────────────────────────
      if (builtLayer && el.animations && el.animations.length > 0) {
        try { applyHoverAnimations(builtLayer, el, el.animations, comp); }
        catch(ae) { debugLines.push('hoverAnim ERR ' + (el.cls||el.tag) + ': ' + ae.toString()); }

        try { applyScrollAnimations(builtLayer, el, el.animations, comp, maxScrollY); }
        catch(ae2) { debugLines.push('scrollAnim ERR ' + (el.cls||el.tag) + ': ' + ae2.toString()); }

        try { applyAutoAnimations(builtLayer, el, el.animations, compDuration); }
        catch(ae3) { debugLines.push('autoAnim ERR ' + (el.cls||el.tag) + ': ' + ae3.toString()); }

        animApplied++;
      }

    } catch (err) {
      debugLines.push('OUTER_ERR layer ' + i + ': ' + err.toString());
    }
  }

  // ── Stack order: guide → INTERACTION NULL → SCROLL NULL (top of comp) ────
  if (guideLabel)      { try { guideLabel.moveToBeginning();      } catch(e) {} }
  if (interactionNull) { try { interactionNull.moveToBeginning();  } catch(e) {} }
  if (scrollNull)      { try { scrollNull.moveToBeginning();       } catch(e) {} }

  app.endUndoGroup();

  var shown = debugLines.slice(0, 60);
  alert("Done! [v24 — Dual Null System]\n\n"
      + "DUAL NULL SETUP:\n"
      + "  INTERACTION NULL (orange label)\n"
      + "    X = 0 → " + vp.width + "px  →  Move left/right to trigger hover animations\n"
      + "    Starts at X=-100 (off-screen)\n\n"
      + "  SCROLL NULL (cyan label)\n"
      + "    Y = 0           →  Page top    (nothing scrolled)\n"
      + "    Y = " + comp.height + "px  →  Page bottom  (fully scrolled)\n"
      + "    Move Y DOWN to reveal scroll-driven animations!\n"
      + "    Starts at Y=0\n\n"
      + "─────────────────────────────────────\n"
      + elements.length + " elements | Comp: " + compDuration + "s  Size: " + vp.width + "x" + compPageH + "px\n"
      + "Images: " + imgLoaded + "  Videos: " + vidLoaded + "  Fallbacks: " + imgFallback + "\n"
      + "Animations applied: " + animApplied + " layers\n"
      + "Scroll range: 0 → " + maxScrollY + "px\n\n"
      + shown.join("\n"));

})();
