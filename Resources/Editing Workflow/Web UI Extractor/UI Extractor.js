/**
 * UI EXTRACTOR v18
 * Paste into browser DevTools console. Downloads ui_extract.json.
 *
 * v18 changes:
 *   - CSS ANIMATION SHORTHAND FIX: Chrome does NOT populate rule.style.animationName
 *     for `animation:` shorthand rules. Now reads rule.style.animation directly and
 *     parses the name + duration from the shorthand string. Fixes 0 animations on
 *     sites like nba.2k.com that use shorthand for carousel / slide-in / spinner.
 *   - SELECTOR FALLBACK: State-class selectors (Vue -enter-active, BEM modifiers
 *     like _infinite-loop-carousel) that have no DOM matches at page-load time are
 *     now matched via progressive stripping to find their base elements.
 *   - LAZY IMAGE FORCE-LOAD: Flips all loading="lazy" imgs to eager, then awaits
 *     img.decode() before walking the DOM, so off-screen images are captured.
 *   - PSEUDO-ELEMENT BG IMAGES: ::before / ::after background-image capture.
 *   - SCROLL SNAP COUNT: 20 positions (was 10).
 *
 * v17 changes (retained):
 *   - SCROLL NULL SUPPORT, INTERSECTION OBSERVER STYLE CAPTURE, GTA6 improvements.
 */
(async function () {

  // ── Color helpers ──────────────────────────────────────────────────────────

  function parseRGB(css) {
    if (!css || css === 'transparent' || css === 'none') return null;
    var hex = css.match(/^#([0-9a-f]{3,8})$/i);
    if (hex) {
      var h = hex[1];
      if (h.length === 3) h = h[0]+h[0]+h[1]+h[1]+h[2]+h[2];
      return { r:parseInt(h.slice(0,2),16), g:parseInt(h.slice(2,4),16), b:parseInt(h.slice(4,6),16), a:1 };
    }
    var m = css.match(/rgba?\(\s*([\d.]+)[,\s]\s*([\d.]+)[,\s]\s*([\d.]+)(?:[,/]\s*([\d.]+))?\s*\)/);
    if (!m) return null;
    var a = m[4] !== undefined ? parseFloat(m[4]) : 1;
    if (a < 0.02) return null;
    return { r:Math.round(parseFloat(m[1])), g:Math.round(parseFloat(m[2])), b:Math.round(parseFloat(m[3])), a:parseFloat(a.toFixed(3)) };
  }

  function toHex(c) {
    return '#'
      + ('0' + c.r.toString(16)).slice(-2)
      + ('0' + c.g.toString(16)).slice(-2)
      + ('0' + c.b.toString(16)).slice(-2);
  }

  function resolveIconColor(el) {
    var node = el;
    for (var d = 0; d < 6 && node; d++) {
      try {
        var c = parseRGB(getComputedStyle(node).color);
        if (c && !(c.r === 0 && c.g === 0 && c.b === 0 && d === 0)) return c;
        var f = getComputedStyle(node).fill;
        if (f && f !== 'none' && f !== 'currentColor') { var cf = parseRGB(f); if (cf) return cf; }
      } catch(e) {}
      node = node.parentElement;
    }
    return { r:255, g:255, b:255, a:1 };
  }

  // ── Animation / transition property lists ──────────────────────────────────

  var ANIM_PROPS = [
    'opacity', 'transform', 'scale', 'rotate', 'translate',
    'backgroundColor', 'color', 'borderColor',
    'boxShadow', 'width', 'height', 'borderRadius', 'filter', 'backgroundImage',
    'backdropFilter'
  ];

  var CSS_TO_COMPUTED = {
    'opacity':          'opacity',
    'transform':        'transform',
    'scale':            'scale',
    'rotate':           'rotate',
    'translate':        'translate',
    'background-color': 'backgroundColor',
    'color':            'color',
    'border-color':     'borderColor',
    'box-shadow':       'boxShadow',
    'width':            'width',
    'height':           'height',
    'border-radius':    'borderRadius',
    'filter':           'filter',
    'background-image': 'backgroundImage',
    'backdrop-filter':  'backdropFilter'
  };

  var ANIMATABLE_CSS_PROPS = Object.keys(CSS_TO_COMPUTED);

  // ── Keyframe rule parser ───────────────────────────────────────────────────

  function parseKeyframesRule(animationName) {
    for (var si = 0; si < document.styleSheets.length; si++) {
      try {
        var sheet = document.styleSheets[si];
        var rules;
        try { rules = sheet.cssRules || sheet.rules; } catch(e) { continue; }
        if (!rules) continue;
        for (var ri = 0; ri < rules.length; ri++) {
          var rule = rules[ri];
          if (rule.type === CSSRule.KEYFRAMES_RULE && rule.name === animationName) {
            var kfs = [];
            for (var ki = 0; ki < rule.cssRules.length; ki++) {
              var kr = rule.cssRules[ki];
              var offset = 0;
              var keyText = kr.keyText || '';
              if (keyText === 'from' || keyText === '0%') offset = 0;
              else if (keyText === 'to' || keyText === '100%') offset = 1;
              else offset = parseFloat(keyText) / 100;
              var props = {};
              for (var pi3 = 0; pi3 < ANIMATABLE_CSS_PROPS.length; pi3++) {
                var cssProp = ANIMATABLE_CSS_PROPS[pi3];
                var val = kr.style.getPropertyValue(cssProp);
                if (val) props[CSS_TO_COMPUTED[cssProp]] = val;
              }
              if (Object.keys(props).length > 0) kfs.push({ offset: offset, props: props });
            }
            if (kfs.length > 0) return kfs;
          }
        }
      } catch(e) {}
    }
    return null;
  }

  // ── Auto-animation capture ─────────────────────────────────────────────────

  function captureAutoAnimations(el, style) {
    var anims = [];
    try {
      var names      = style.animationName;
      var durations  = style.animationDuration;
      var iterations = style.animationIterationCount;
      var delays     = style.animationDelay;
      if (names && names !== 'none') {
        var nameList  = names.split(',').map(function(s){ return s.trim(); });
        var durList   = durations.split(',').map(function(s){ return parseFloat(s) || 0; });
        var iterList  = iterations.split(',').map(function(s){ return s.trim() === 'infinite' ? -1 : parseFloat(s) || 1; });
        var delayList = delays.split(',').map(function(s){ return parseFloat(s) || 0; });
        for (var ni = 0; ni < nameList.length; ni++) {
          var name = nameList[ni];
          if (!name || name === 'none') continue;
          var dur   = durList[ni % durList.length];
          var iter  = iterList[ni % iterList.length];
          var delay = delayList[ni % delayList.length];
          if (dur <= 0) continue;
          var kfs = parseKeyframesRule(name);
          if (!kfs || kfs.length === 0) continue;
          anims.push({ name: name, trigger: 'auto', duration: dur, iterationCount: iter, delay: delay, keyframes: kfs });
        }
      }
    } catch(e) {}
    try {
      var wapiAnims = el.getAnimations ? el.getAnimations() : [];
      for (var wai = 0; wai < wapiAnims.length; wai++) {
        try {
          var wa = wapiAnims[wai];
          if (!wa.effect || typeof wa.effect.getKeyframes !== 'function') continue;
          var waKfs = wa.effect.getKeyframes();
          if (!waKfs || waKfs.length < 2) continue;
          var timing = wa.effect.getTiming ? wa.effect.getTiming() : {};
          var waDur  = typeof timing.duration === 'number' ? timing.duration / 1000 : 1;
          if (waDur <= 0) continue;
          var waIter = (timing.iterations === Infinity || timing.iterations === null) ? -1 : (timing.iterations || 1);
          var waDelay = (timing.delay || 0) / 1000;
          var convertedKfs = [];
          for (var ki = 0; ki < waKfs.length; ki++) {
            var wkf = waKfs[ki];
            var offset = typeof wkf.offset === 'number' ? wkf.offset : (ki / (waKfs.length - 1));
            var props = {};
            for (var pi3b = 0; pi3b < ANIM_PROPS.length; pi3b++) {
              var prop = ANIM_PROPS[pi3b];
              if (wkf[prop] !== undefined && wkf[prop] !== '') props[prop] = wkf[prop];
            }
            if (wkf.opacity !== undefined) props.opacity = String(wkf.opacity);
            if (wkf.transform !== undefined) props.transform = wkf.transform;
            if (wkf.backgroundColor !== undefined) props.backgroundColor = wkf.backgroundColor;
            if (Object.keys(props).length > 0) convertedKfs.push({ offset: offset, props: props });
          }
          if (convertedKfs.length >= 2) {
            var waName = (wa.animationName || wa.id || 'waapi_' + wai);
            var alreadyHave = false;
            for (var dai = 0; dai < anims.length; dai++) {
              if (anims[dai].name === waName) { alreadyHave = true; break; }
            }
            if (!alreadyHave) {
              anims.push({ name: waName, trigger: 'auto', duration: waDur, iterationCount: waIter, delay: waDelay, keyframes: convertedKfs, _source: 'waapi' });
            }
          }
        } catch(we) {}
      }
    } catch(e) {}
    return anims;
  }

  // ── Hover transition capture ───────────────────────────────────────────────

  // captureHoverTransitions v19
  // WORKS ON SITES WITH CORS-BLOCKED / NO READABLE STYLESHEETS (Next.js, CSS Modules, etc.)
  // Strategy: dispatch real mouseover/mouseenter events on the element and its
  // ancestors, read getComputedStyle synchronously before and after, diff everything.
  // Browsers apply :hover pseudo-class styles synchronously on dispatchEvent.

  function captureHoverTransitions(el, style) {
    var transitions = [];
    try {
      // Check resting transition-duration first
      var td = style.transitionDuration;
      var durs = td ? td.split(',').map(function(s){ return parseFloat(s)||0; }) : [0];
      var maxDurResting = Math.max.apply(null, durs);

      // CRITICAL: on many sites (including 2K/NBA2K), transition-duration is only
      // declared INSIDE the :hover rule, not on the resting element. So
      // getComputedStyle at rest gives transitionDuration=0s even though a hover
      // animation exists. We must ALWAYS attempt the hover simulation regardless
      // and read the transition duration AFTER entering hover state.

      var transProp   = style.transitionProperty || 'all';
      var transDelays = (style.transitionDelay||'0s').split(',').map(function(s){ return parseFloat(s)||0; });

      // Snapshot resting state
      var fromState = {};
      for (var pi0 = 0; pi0 < ANIM_PROPS.length; pi0++) {
        fromState[ANIM_PROPS[pi0]] = style[ANIM_PROPS[pi0]];
      }

      function readHoveredState(target) {
        target.dispatchEvent(new MouseEvent('mouseover',  { bubbles: true,  cancelable: true, view: window }));
        target.dispatchEvent(new MouseEvent('mouseenter', { bubbles: false, cancelable: true, view: window }));
        var s = getComputedStyle(el);
        var state = {};
        for (var pi = 0; pi < ANIM_PROPS.length; pi++) state[ANIM_PROPS[pi]] = s[ANIM_PROPS[pi]];
        // ALSO read transition duration now (may only exist in hover state)
        state._transitionDuration = s.transitionDuration;
        state._transitionProperty = s.transitionProperty;
        target.dispatchEvent(new MouseEvent('mouseout',   { bubbles: true,  cancelable: true, view: window }));
        target.dispatchEvent(new MouseEvent('mouseleave', { bubbles: false, cancelable: true, view: window }));
        return state;
      }

      function hasChange(a, b) {
        for (var pi = 0; pi < ANIM_PROPS.length; pi++) {
          var p = ANIM_PROPS[pi];
          if (a[p] === b[p]) continue;
          if ((a[p] === 'none' || a[p] === '') && b[p] === 'matrix(1, 0, 0, 1, 0, 0)') continue;
          if ((b[p] === 'none' || b[p] === '') && a[p] === 'matrix(1, 0, 0, 1, 0, 0)') continue;
          return true;
        }
        return false;
      }

      // 1. Try hovering element itself
      var toState = readHoveredState(el);

      // 2. If no change, walk up ancestors (compound hover: parent:hover -> child animates)
      if (!hasChange(fromState, toState)) {
        var anc = el.parentElement;
        for (var depth = 0; depth < 6 && anc; depth++) {
          var ancState = readHoveredState(anc);
          if (hasChange(fromState, ancState)) { toState = ancState; break; }
          anc = anc.parentElement;
        }
      }

      if (!hasChange(fromState, toState)) return transitions;

      // Use transition duration from hovered state if resting had none
      var hoveredTd = toState._transitionDuration || td || '0.25s';
      var transDurs = hoveredTd.split(',').map(function(s){ return parseFloat(s)||0.25; });
      var hoveredTp = toState._transitionProperty || transProp;

      var propList = (hoveredTp === 'all' || hoveredTp === '')
        ? ANIM_PROPS
        : hoveredTp.split(',').map(function(s){ return CSS_TO_COMPUTED[s.trim()] || s.trim(); });

      for (var ti = 0; ti < propList.length; ti++) {
        var prop = propList[ti];
        var fromVal = fromState[prop] || '';
        var toVal   = toState[prop]   || '';
        if (!fromVal && !toVal) continue;
        if (fromVal === toVal) continue;
        if ((fromVal === 'none' || fromVal === '') && toVal === 'matrix(1, 0, 0, 1, 0, 0)') continue;
        if ((toVal   === 'none' || toVal   === '') && fromVal === 'matrix(1, 0, 0, 1, 0, 0)') continue;
        var dur   = transDurs[ti % transDurs.length] || 0.25;
        var delay = transDelays[ti % transDelays.length] || 0;
        transitions.push({ trigger: 'hover', property: prop, from: fromVal, to: toVal, duration: dur, delay: delay });
      }
    } catch(e) {}
    return transitions;
  }

  // ── Scroll animation capture ───────────────────────────────────────────────

  var SCROLL_SNAP_COUNT = 20;

  var SCROLL_WATCH_SELECTORS = [
    'ytd-masthead', '#masthead', '#masthead-container',
    'ytd-watch-flexy', '#player-container', '#above-the-fold',
    'ytd-rich-grid-renderer', '#header', '.ytd-page-manager',
    '[style*="position: sticky"]', '[style*="position:sticky"]',
    '[style*="position:fixed"]',   '[style*="position: fixed"]',
    '.sticky', '.fixed-header', '.navbar', '.nav', 'header', 'nav', 'footer',
    '[data-scroll]', '[data-sticky]',
    '[class*="parallax"]', '[class*="hero"]', '[class*="banner"]',
    '[class*="scroll"]',   '[class*="fade"]',  '[class*="blur"]',
    '[class*="reveal"]',   '[class*="animate"]', '[class*="sticky"]',
    '[class*="section"]', '[class*="scene"]', '[class*="chapter"]',
    '[class*="cinematic"]', '[class*="story"]', '[class*="intro"]',
    '[class*="transition"]', '[class*="slide"]', '[class*="panel"]',
    '[class*="layer"]', '[class*="overlay"]', '[class*="mask"]',
    '[data-scene]', '[data-section]', '[data-chapter]',
    'canvas', 'img', 'video', 'picture',
    'section', 'article', 'aside', 'main'
  ];

  function buildScrollWatchList() {
    var list = [];
    for (var si = 0; si < SCROLL_WATCH_SELECTORS.length; si++) {
      try {
        var matches = document.querySelectorAll(SCROLL_WATCH_SELECTORS[si]);
        for (var mi = 0; mi < matches.length; mi++) {
          var el = matches[mi];
          if (!el._scrollWatchId) {
            el._scrollWatchId = 'sw' + list.length;
            list.push(el);
          }
        }
      } catch(e) {}
    }
    try {
      document.querySelectorAll('*').forEach(function(el) {
        if (el._scrollWatchId) return;
        if (list.length >= 800) return;
        try {
          var cs  = getComputedStyle(el);
          var wc  = cs.willChange;
          var pos = cs.position;
          var tr  = cs.transitionDuration;
          var an  = cs.animationName;
          var flt = cs.filter;
          var bdf = cs.backdropFilter || cs.webkitBackdropFilter || '';
          var animTimeline = cs.animationTimeline || '';
          var shouldWatch =
            (wc  && wc  !== 'auto'  && wc  !== 'unset') ||
            (pos === 'sticky' || pos === 'fixed') ||
            (tr  && tr  !== '0s'    && tr  !== '0.0s') ||
            (an  && an  !== 'none') ||
            (flt && flt !== 'none') ||
            (bdf && bdf !== 'none') ||
            (animTimeline && animTimeline !== 'auto' && animTimeline !== 'none');
          if (shouldWatch) {
            el._scrollWatchId = 'sw' + list.length;
            list.push(el);
          }
        } catch(e) {}
      });
    } catch(e) {}
    return list;
  }

  function snapshotStyles(watchList) {
    var snap = {};
    for (var i = 0; i < watchList.length; i++) {
      var el = watchList[i];
      try {
        var s = getComputedStyle(el);
        var entry = {};
        for (var pi = 0; pi < ANIM_PROPS.length; pi++) {
          entry[ANIM_PROPS[pi]] = s[ANIM_PROPS[pi]];
        }
        snap[el._scrollWatchId] = entry;
      } catch(e) {}
    }
    return snap;
  }

  function computeViewportTriggerY(watchEl) {
    try {
      var rect = watchEl.getBoundingClientRect();
      var pageY = rect.top + window.scrollY;
      return Math.max(0, pageY - window.innerHeight * 0.85);
    } catch(e) { return 0; }
  }

  async function captureScrollAnimations(watchList, elements) {
    if (watchList.length === 0) return {};
    var maxScroll = Math.max(0, document.body.scrollHeight - window.innerHeight);
    if (maxScroll < 50) return {};
    var origScrollY = window.scrollY;
    var snapPositions = [];
    for (var si = 0; si <= SCROLL_SNAP_COUNT; si++) {
      snapPositions.push(Math.round(si * maxScroll / SCROLL_SNAP_COUNT));
    }
    var triggerYMap = {};
    for (var wi = 0; wi < watchList.length; wi++) {
      triggerYMap[watchList[wi]._scrollWatchId] = computeViewportTriggerY(watchList[wi]);
    }
    var snaps = [];
    for (var pi = 0; pi < snapPositions.length; pi++) {
      window.scrollTo(0, snapPositions[pi]);
      await new Promise(function(r){ setTimeout(r, 80); });
      snaps.push({ scrollY: window.scrollY, styles: snapshotStyles(watchList) });
    }
    window.scrollTo(0, origScrollY);
    await new Promise(function(r){ setTimeout(r, 100); });
    var scrollAnimsByElementIndex = {};
    for (var swi = 0; swi < watchList.length; swi++) {
      var watchEl = watchList[swi];
      var wid = watchEl._scrollWatchId;
      var scrollAnims = [];
      for (var si2 = 0; si2 < snaps.length - 1; si2++) {
        var sA = snaps[si2];
        var sB = snaps[si2 + 1];
        if (!sA.styles[wid] || !sB.styles[wid]) continue;
        var a = sA.styles[wid];
        var b = sB.styles[wid];
        for (var pi2 = 0; pi2 < ANIM_PROPS.length; pi2++) {
          var prop = ANIM_PROPS[pi2];
          if (a[prop] !== b[prop]) {
            scrollAnims.push({
              trigger: 'scroll', property: prop,
              scrollFrom: sA.scrollY, scrollTo: sB.scrollY,
              viewportTriggerY: triggerYMap[wid] || 0,
              from: a[prop], to: b[prop]
            });
          }
        }
      }
      if (scrollAnims.length === 0) continue;
      var watchRect;
      try { watchRect = watchEl.getBoundingClientRect(); } catch(e) { continue; }
      var watchX = Math.round(watchRect.x + window.scrollX);
      var watchY = Math.round(watchRect.y + window.scrollY);
      var bestIdx = -1; var bestDist = 999999;
      for (var ei = 0; ei < elements.length; ei++) {
        var er = elements[ei].rect;
        if (!er) continue;
        var dist = Math.abs(er.x - watchX) + Math.abs(er.y - watchY);
        if (dist < bestDist) { bestDist = dist; bestIdx = ei; }
      }
      if (bestIdx >= 0 && bestDist < 120) {
        if (!scrollAnimsByElementIndex[bestIdx]) scrollAnimsByElementIndex[bestIdx] = [];
        var existing = scrollAnimsByElementIndex[bestIdx];
        for (var sai = 0; sai < scrollAnims.length; sai++) { existing.push(scrollAnims[sai]); }
      }
    }
    return scrollAnimsByElementIndex;
  }

  function detectScrollRevealCandidates(elements) {
    var foldY = window.innerHeight;
    var reveals = [];
    for (var i = 0; i < elements.length; i++) {
      var el = elements[i];
      if (!el.rect || el.animations) continue;
      if (el.rect.y < foldY * 0.5) continue;
      var isHidden = false; var revealProp = null; var fromVal = null; var toVal = null;
      if (el.opacity !== undefined && el.opacity < 0.1) {
        isHidden = true; revealProp = 'opacity'; fromVal = String(el.opacity); toVal = '1';
      }
      if (isHidden && revealProp) {
        var triggerY = Math.max(0, el.rect.y - foldY * 0.8);
        if (!elements[i].animations) elements[i].animations = [];
        elements[i].animations.push({
          trigger: 'scroll', property: revealProp,
          scrollFrom: triggerY, scrollTo: triggerY + 200,
          viewportTriggerY: triggerY, from: fromVal, to: toVal, _synthetic: true
        });
        reveals.push(i);
      }
    }
    return reveals;
  }

  // ── Button-text detector ───────────────────────────────────────────────────

  var INTERACTIVE_SELECTORS = [
    'button', '[role="button"]', 'a', '.ytp-button', '.yt-spec-button-shape-next',
    '.ytd-button-renderer', '[aria-label]', '.btn', '.cta', '.purchase', '.buy-btn'
  ];

  function isButtonText(el, text) {
    if (!text || text.length > 32) return false;
    var stripped = text.replace(/[^a-zA-Z0-9 ]/g, '').trim();
    if (stripped.length < 2) return false;
    var isAllCaps = stripped === stripped.toUpperCase() && /[A-Z]/.test(stripped);
    var isTitleCase = stripped.split(' ').every(function(w){
      return w.length === 0 || (w[0] === w[0].toUpperCase() && w.slice(1) === w.slice(1).toLowerCase());
    });
    if (!isAllCaps && !isTitleCase) return false;
    var node = el;
    for (var d = 0; d < 8 && node; d++) {
      for (var si = 0; si < INTERACTIVE_SELECTORS.length; si++) {
        try { if (node.matches && node.matches(INTERACTIVE_SELECTORS[si])) return true; } catch(e) {}
      }
      node = node.parentElement;
    }
    return false;
  }

  // ── SVG rasterizer ─────────────────────────────────────────────────────────

  function rasterizeSVG(svgEl, iconColor, w, h) {
    return new Promise(function(resolve) {
      try {
        if (w < 1 || h < 1) { resolve(null); return; }
        var clone = svgEl.cloneNode(true);
        clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        clone.setAttribute('width',  w);
        clone.setAttribute('height', h);
        if (!clone.getAttribute('viewBox')) clone.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
        var colorHex = toHex(iconColor);
        clone.setAttribute('fill', colorHex);
        var svgStr = new XMLSerializer().serializeToString(clone);
        svgStr = svgStr.replace(/currentColor/g, colorHex);
        var blob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' });
        var blobUrl = URL.createObjectURL(blob);
        var img = new Image();
        img.onload = function() {
          try {
            var dpr    = Math.min(window.devicePixelRatio || 1, 3);
            var canvas = document.createElement('canvas');
            canvas.width  = Math.round(w * dpr);
            canvas.height = Math.round(h * dpr);
            var ctx = canvas.getContext('2d');
            ctx.scale(dpr, dpr);
            ctx.drawImage(img, 0, 0, w, h);
            URL.revokeObjectURL(blobUrl);
            resolve(canvas.toDataURL('image/png'));
          } catch(e) { URL.revokeObjectURL(blobUrl); resolve(null); }
        };
        img.onerror = function() { URL.revokeObjectURL(blobUrl); resolve(null); };
        img.src = blobUrl;
      } catch(e) { resolve(null); }
    });
  }

  // ── Image URL helpers ──────────────────────────────────────────────────────

  function getImgSrc(el) {
    if (el.currentSrc && el.currentSrc !== '' && el.currentSrc.indexOf('data:') !== 0) return el.currentSrc;
    if (el.src && el.src !== '' && el.src.indexOf('data:') !== 0) return el.src;
    if (el.srcset) {
      var entries = el.srcset.split(',').map(function(s){ return s.trim().split(/\s+/)[0]; }).filter(Boolean);
      var nonWebp = entries.filter(function(u){ return u.toLowerCase().indexOf('.webp') === -1; });
      var chosen = (nonWebp.length > 0 ? nonWebp[0] : entries[0]) || null;
      if (chosen) return chosen;
    }
    try {
      var pic = el.parentElement;
      if (pic && pic.tagName && pic.tagName.toLowerCase() === 'picture') {
        var sources = pic.querySelectorAll('source');
        for (var si2 = 0; si2 < sources.length; si2++) {
          var src2 = sources[si2];
          var type = (src2.getAttribute('type') || '').toLowerCase();
          if (type === 'image/webp') continue;
          var ss = src2.srcset || src2.getAttribute('srcset') || '';
          if (ss) {
            var first = ss.split(',')[0].trim().split(/\s+/)[0];
            if (first) return first;
          }
        }
        var firstSrc = pic.querySelector('source');
        if (firstSrc) {
          var fss = firstSrc.srcset || firstSrc.getAttribute('srcset') || '';
          if (fss) return fss.split(',')[0].trim().split(/\s+/)[0];
        }
      }
    } catch(e) {}
    return el.getAttribute('data-src')
        || el.getAttribute('data-lazy-src')
        || el.getAttribute('data-lazy')
        || el.getAttribute('data-defer-src')
        || el.getAttribute('data-echo')
        || el.getAttribute('data-lazyload')
        || el.getAttribute('data-img-src')
        || el.getAttribute('data-original')
        || el.getAttribute('data-original-src')
        || el.getAttribute('data-url')
        || el.getAttribute('data-image')
        || el.getAttribute('data-bg')
        || null;
  }

  function getBgImageUrl(cssValue) {
    if (!cssValue || cssValue === 'none') return null;
    if (cssValue.indexOf('gradient') !== -1) return null;
    var m = cssValue.match(/url\(["']?([^"')]+)["']?\)/);
    return m ? m[1] : null;
  }

  // ── Video URL helpers ──────────────────────────────────────────────────────

  function getVideoSrcs(el) {
    var srcs = [];
    if (el.currentSrc && el.currentSrc !== '') srcs.push(el.currentSrc);
    if (el.src && el.src !== '' && srcs.indexOf(el.src) === -1) srcs.push(el.src);
    var sourceEls = el.querySelectorAll('source');
    for (var si2 = 0; si2 < sourceEls.length; si2++) {
      var s = sourceEls[si2].src || sourceEls[si2].getAttribute('src') || '';
      if (s && srcs.indexOf(s) === -1) srcs.push(s);
    }
    var ds = el.getAttribute('data-src') || el.getAttribute('data-video-src') || '';
    if (ds && srcs.indexOf(ds) === -1) srcs.push(ds);
    return { src: srcs[0] || null, poster: el.poster || null, sources: srcs };
  }

  function detectYtDlpHint(el) {
    var src = el.currentSrc || el.src || '';
    var ytIdSrc = src.match(/(?:youtube\.com|youtu\.be).*[?&v=]([a-zA-Z0-9_-]{11})/);
    if (ytIdSrc) return { pageUrl: window.location.href, videoId: ytIdSrc[1] };
    var ytIdPage = window.location.href.match(/[?&v=]([a-zA-Z0-9_-]{11})/);
    if (ytIdPage && window.location.hostname.indexOf('youtube') !== -1) {
      return { pageUrl: window.location.href, videoId: ytIdPage[1] };
    }
    var node = el;
    for (var d = 0; d < 12 && node; d++) {
      if (node.tagName && node.tagName.toLowerCase() === 'ytd-watch-flexy') {
        var vid = node.getAttribute('video-id');
        if (vid) return { pageUrl: window.location.href, videoId: vid };
      }
      node = node.parentElement;
    }
    return null;
  }

  // ── Gradient parser ────────────────────────────────────────────────────────

  function parseGradient(cssValue) {
    if (!cssValue || cssValue === 'none') return null;
    var isLinear = cssValue.indexOf('linear-gradient') !== -1;
    var isRadial = cssValue.indexOf('radial-gradient') !== -1;
    if (!isLinear && !isRadial) return null;
    var inner = cssValue.match(/(?:linear|radial)-gradient\(([\s\S]+?)\)(?:,\s*(?:linear|radial)|$)/);
    if (!inner) return null;
    var body = inner[1];
    function tokenize(s) {
      var tokens = []; var cur = ''; var depth = 0;
      for (var ci = 0; ci < s.length; ci++) {
        var ch = s[ci];
        if (ch === '(') { depth++; cur += ch; }
        else if (ch === ')') { depth--; cur += ch; }
        else if (ch === ',' && depth === 0) { tokens.push(cur.trim()); cur = ''; }
        else { cur += ch; }
      }
      if (cur.trim()) tokens.push(cur.trim());
      return tokens;
    }
    var parts = tokenize(body);
    var angle = 180; var stopsRaw = parts;
    if (isLinear) {
      var first = parts[0] || '';
      var degM = first.match(/^(-?[\d.]+)deg$/);
      if (degM) { angle = parseFloat(degM[1]); stopsRaw = parts.slice(1); }
      else if (first.indexOf('to ') === 0) {
        var dir = first.toLowerCase();
        if      (dir === 'to bottom')       angle = 180;
        else if (dir === 'to top')          angle = 0;
        else if (dir === 'to right')        angle = 90;
        else if (dir === 'to left')         angle = 270;
        else if (dir === 'to bottom right') angle = 135;
        else if (dir === 'to bottom left')  angle = 225;
        else if (dir === 'to top right')    angle = 45;
        else if (dir === 'to top left')     angle = 315;
        stopsRaw = parts.slice(1);
      }
    }
    var stops = [];
    for (var si3 = 0; si3 < stopsRaw.length; si3++) {
      var tok = stopsRaw[si3].trim();
      var posPct = tok.match(/([\d.]+)%\s*$/);
      var colorStr = tok.replace(/\s+[-\d.]+(?:px|%)\s*$/, '').trim();
      var c = parseRGB(colorStr);
      if (!c) continue;
      var pos = posPct ? parseFloat(posPct[1]) / 100 : null;
      stops.push({ color: c, pos: pos });
    }
    if (stops.length < 2) return null;
    for (var si4 = 0; si4 < stops.length; si4++) {
      if (stops[si4].pos === null) stops[si4].pos = si4 / (stops.length - 1);
    }
    return { type: isLinear ? 'linear' : 'radial', angle: angle, stops: stops };
  }

  function rasterizeElement(el, w, h) {
    return new Promise(function(resolve) {
      try {
        if (w < 1 || h < 1) { resolve(null); return; }
        var style = getComputedStyle(el);
        var div = document.createElement('div');
        div.style.cssText = [
          'width:' + w + 'px', 'height:' + h + 'px',
          'background:' + style.background,
          'background-color:' + style.backgroundColor,
          'background-image:' + style.backgroundImage,
          'background-size:cover', 'margin:0', 'padding:0', 'border:none', 'box-shadow:none'
        ].join(';');
        var svgStr = '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '">'
          + '<foreignObject width="' + w + '" height="' + h + '">'
          + '<html xmlns="http://www.w3.org/1999/xhtml"><body style="margin:0;padding:0;">'
          + div.outerHTML + '</body></html></foreignObject></svg>';
        var blob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' });
        var blobUrl = URL.createObjectURL(blob);
        var img = new Image();
        img.onload = function() {
          try {
            var canvas = document.createElement('canvas');
            canvas.width = w; canvas.height = h;
            canvas.getContext('2d').drawImage(img, 0, 0, w, h);
            URL.revokeObjectURL(blobUrl);
            resolve(canvas.toDataURL('image/png'));
          } catch(e) { URL.revokeObjectURL(blobUrl); resolve(null); }
        };
        img.onerror = function() { URL.revokeObjectURL(blobUrl); resolve(null); };
        img.src = blobUrl;
      } catch(e) { resolve(null); }
    });
  }

  // ── SVG path serializer ────────────────────────────────────────────────────

  function extractSVGPaths(svgEl) {
    var paths = [];
    try {
      var vb = svgEl.getAttribute('viewBox');
      var vbX = 0, vbY = 0, vbW = 0, vbH = 0;
      if (vb) {
        var vbParts = vb.trim().split(/[\s,]+/);
        vbX = parseFloat(vbParts[0]) || 0; vbY = parseFloat(vbParts[1]) || 0;
        vbW = parseFloat(vbParts[2]) || 0; vbH = parseFloat(vbParts[3]) || 0;
      }
      if (vbW <= 0) vbW = parseFloat(svgEl.getAttribute('width'))  || 24;
      if (vbH <= 0) vbH = parseFloat(svgEl.getAttribute('height')) || 24;
      function nodeColor(node, attr) {
        var v = node.getAttribute(attr);
        if (!v || v === 'none') return null;
        if (v === 'currentColor') return null;
        return parseRGB(v);
      }
      function circleTod(cx, cy, r) {
        var k = r * 0.5523;
        return 'M '+(cx-r)+' '+cy+' C '+(cx-r)+' '+(cy-k)+' '+(cx-k)+' '+(cy-r)+' '+cx+' '+(cy-r)
          +' C '+(cx+k)+' '+(cy-r)+' '+(cx+r)+' '+(cy-k)+' '+(cx+r)+' '+cy
          +' C '+(cx+r)+' '+(cy+k)+' '+(cx+k)+' '+(cy+r)+' '+cx+' '+(cy+r)
          +' C '+(cx-k)+' '+(cy+r)+' '+(cx-r)+' '+(cy+k)+' '+(cx-r)+' '+cy+' Z';
      }
      function rectTod(x, y, w, h) { return 'M '+x+' '+y+' L '+(x+w)+' '+y+' L '+(x+w)+' '+(y+h)+' L '+x+' '+(y+h)+' Z'; }
      var nodes = svgEl.querySelectorAll('path, circle, rect, ellipse, line, polyline, polygon');
      for (var ni = 0; ni < nodes.length; ni++) {
        var node = nodes[ni];
        var nodeName = node.tagName.toLowerCase();
        var d = null;
        if (nodeName === 'path') {
          d = node.getAttribute('d');
        } else if (nodeName === 'circle') {
          var cx2 = parseFloat(node.getAttribute('cx') || '0');
          var cy2 = parseFloat(node.getAttribute('cy') || '0');
          var r2  = parseFloat(node.getAttribute('r')  || '0');
          if (r2 > 0) d = circleTod(cx2, cy2, r2);
        } else if (nodeName === 'ellipse') {
          var ecx = parseFloat(node.getAttribute('cx') || '0');
          var ecy = parseFloat(node.getAttribute('cy') || '0');
          var rx  = parseFloat(node.getAttribute('rx') || '0');
          var ry  = parseFloat(node.getAttribute('ry') || '0');
          if (rx > 0 && ry > 0) {
            var kx = rx * 0.5523; var ky = ry * 0.5523;
            d = 'M '+(ecx-rx)+' '+ecy+' C '+(ecx-rx)+' '+(ecy-ky)+' '+(ecx-kx)+' '+(ecy-ry)+' '+ecx+' '+(ecy-ry)
              +' C '+(ecx+kx)+' '+(ecy-ry)+' '+(ecx+rx)+' '+(ecy-ky)+' '+(ecx+rx)+' '+ecy
              +' C '+(ecx+rx)+' '+(ecy+ky)+' '+(ecx+kx)+' '+(ecy+ry)+' '+ecx+' '+(ecy+ry)
              +' C '+(ecx-kx)+' '+(ecy+ry)+' '+(ecx-rx)+' '+(ecy+ky)+' '+(ecx-rx)+' '+ecy+' Z';
          }
        } else if (nodeName === 'rect') {
          var rx3 = parseFloat(node.getAttribute('x') || '0');
          var ry3 = parseFloat(node.getAttribute('y') || '0');
          var rw  = parseFloat(node.getAttribute('width')  || '0');
          var rh  = parseFloat(node.getAttribute('height') || '0');
          if (rw > 0 && rh > 0) d = rectTod(rx3, ry3, rw, rh);
        } else if (nodeName === 'line') {
          d = 'M '+parseFloat(node.getAttribute('x1')||'0')+' '+parseFloat(node.getAttribute('y1')||'0')
            +' L '+parseFloat(node.getAttribute('x2')||'0')+' '+parseFloat(node.getAttribute('y2')||'0');
        } else if (nodeName === 'polyline' || nodeName === 'polygon') {
          var pts = (node.getAttribute('points') || '').trim().split(/[\s,]+/);
          if (pts.length >= 4) {
            d = 'M '+pts[0]+' '+pts[1];
            for (var pi5 = 2; pi5 < pts.length - 1; pi5 += 2) d += ' L '+pts[pi5]+' '+pts[pi5+1];
            if (nodeName === 'polygon') d += ' Z';
          }
        }
        if (!d) continue;
        var cs = getComputedStyle(node);
        var fillC   = nodeColor(node, 'fill')   || parseRGB(cs.fill)   || null;
        var strokeC = nodeColor(node, 'stroke') || parseRGB(cs.stroke) || null;
        var sw = parseFloat(node.getAttribute('stroke-width') || cs.strokeWidth || '0') || 0;
        paths.push({ d: d, fill: fillC, stroke: strokeC, strokeWidth: sw, fillRule: node.getAttribute('fill-rule') || 'nonzero', vbX: vbX, vbY: vbY, vbW: vbW, vbH: vbH });
      }
    } catch(e) {}
    return paths;
  }

  var _imgCounter = 0;
  function makeImageKey(url, tag) {
    _imgCounter++;
    try {
      var clean = url.split('?')[0].split('#')[0];
      if (url.indexOf('data:') === 0) return _imgCounter + '_' + tag + '_raster';
      var parts = clean.split('/');
      var name  = parts[parts.length - 1] || 'image';
      name = name.replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 40);
      if (!name || name === '_') name = tag + '_img';
      return _imgCounter + '_' + name;
    } catch(e) { return _imgCounter + '_' + tag + '_img'; }
  }

  // ── Text helpers ───────────────────────────────────────────────────────────

  function getDirectText(el) {
    var t = '';
    for (var i = 0; i < el.childNodes.length; i++) {
      if (el.childNodes[i].nodeType === 3) t += el.childNodes[i].textContent;
    }
    return t.trim();
  }

  function truncateText(text, elWidth, fontSize) {
    var charsPerLine = Math.floor(elWidth / (fontSize * 0.52));
    if (charsPerLine < 4) return text;
    if (text.length <= charsPerLine) return text;
    return text.slice(0, charsPerLine - 3) + '...';
  }

  // ── Geometry / radius helpers ──────────────────────────────────────────────

  function resolveRadius(el, style) {
    var r = style.borderRadius;
    if (r && r !== '0px' && r !== '0%' && r !== '0') return r;
    var p = el.parentElement;
    for (var d = 0; d < 8 && p; d++) {
      try { var pr = getComputedStyle(p).borderRadius; if (pr && pr !== '0px' && pr !== '0%' && pr !== '0') return pr; } catch(e) {}
      p = p.parentElement;
    }
    try {
      var root = el.getRootNode();
      if (root && root.nodeType === 11) {
        var host = root.host;
        if (host) {
          var hr = getComputedStyle(host).borderRadius;
          if (hr && hr !== '0px' && hr !== '0%' && hr !== '0') return hr;
          var hp = host.parentElement;
          for (var hd = 0; hd < 8 && hp; hd++) {
            var hpr = getComputedStyle(hp).borderRadius;
            if (hpr && hpr !== '0px' && hpr !== '0%' && hpr !== '0') return hpr;
            hp = hp.parentElement;
          }
        }
      }
    } catch(e) {}
    return '0px';
  }

  // ── Globals ────────────────────────────────────────────────────────────────

  var bodyBg = parseRGB(getComputedStyle(document.body).backgroundColor)
            || parseRGB(getComputedStyle(document.documentElement).backgroundColor)
            || { r:15, g:15, b:15, a:1 };

  var vp = {
    width:      Math.round(window.innerWidth),
    height:     Math.round(window.innerHeight),
    pageWidth:  Math.round(Math.max(document.documentElement.scrollWidth,  document.body.scrollWidth,  window.innerWidth)),
    pageHeight: Math.round(Math.max(document.documentElement.scrollHeight, document.body.scrollHeight, window.innerHeight)),
    scrollX:    Math.round(window.scrollX),
    scrollY:    Math.round(window.scrollY),
    dpr:        window.devicePixelRatio || 1,
    url:        window.location.href,
    title:      document.title
  };

  var elements       = [];
  var svgElRefs      = [];
  var gradElRefs     = [];
  var iconFontElRefs = [];
  var counts     = { shapes:0, text:0, images:0, icons:0, gradients:0, videos:0, skipped:0 };
  var rectSet    = {};

  function isDuplicate(r) {
    var key = Math.round(r.x/2)*2 + ',' + Math.round(r.y/2)*2 + ',' + Math.round(r.w/2)*2 + ',' + Math.round(r.h/2)*2;
    if (rectSet[key]) return true;
    rectSet[key] = true;
    return false;
  }

  // ── Icon font detection ────────────────────────────────────────────────────

  var ICON_FONT_MARKERS = [
    'font awesome', 'fontawesome', 'material icons', 'material symbols',
    'icomoon', 'themify', 'ionicons', 'bootstrap icons', 'remix icon',
    'boxicons', 'feather icons', 'dripicons', 'simple-line-icons',
    'typicons', 'linearicons', 'nucleo', 'nerd fonts'
  ];

  var ICON_FONT_CLASS_RE = /(?:^|\s)(?:fa[brsld]?|material-icons?|bi|ri-|bx|tf-|ti-|si-|ion-|nf-|fi |ph |ls-[a-z])(?:\s|$)|(?:^|\s)fa-[a-z]/;

  function isIconFontEl(el, style) {
    var ff = (style.fontFamily || '').toLowerCase();
    for (var _ii = 0; _ii < ICON_FONT_MARKERS.length; _ii++) {
      if (ff.indexOf(ICON_FONT_MARKERS[_ii]) !== -1) return true;
    }
    var cls = typeof el.className === 'string'
      ? el.className
      : (el.className && el.className.baseVal ? el.className.baseVal : '');
    return ICON_FONT_CLASS_RE.test(cls);
  }

  // ── Core element capture ───────────────────────────────────────────────────

  function captureElement(el) {
    try {
      var rect  = el.getBoundingClientRect();
      var style = getComputedStyle(el);
      var tag   = el.tagName.toLowerCase();

      if (rect.width < 3 || rect.height < 3)                          return;
      if (style.display === 'none' || style.visibility === 'hidden')   return;
      if (parseFloat(style.opacity) < 0.05)                           return;
      if (tag !== 'img' && tag !== 'video' && tag !== 'svg' &&
          (!style.backgroundImage || style.backgroundImage === 'none') &&
          rect.width >= vp.width * 0.95 && rect.height >= vp.pageHeight * 0.4) return;

      // ── CAROUSEL CLIP CHECK ──────────────────────────────────────────────
      // Skip elements that are clipped/hidden inside a scrolling carousel.
      // Walk up the ancestor chain: if any ancestor has overflow:hidden/clip
      // AND is narrower/shorter than the page (i.e. it's a carousel track,
      // not just the body), check if this element's rect is fully outside
      // that ancestor's visible rect. If so, it's a hidden slide — skip it.
      var clippedOut = false;
      var anc2 = el.parentElement;
      for (var ci = 0; ci < 8 && anc2 && anc2 !== document.body; ci++) {
        try {
          var ancStyle = getComputedStyle(anc2);
          var ov = ancStyle.overflow + ' ' + ancStyle.overflowX + ' ' + ancStyle.overflowY;
          if (ov.indexOf('hidden') !== -1 || ov.indexOf('clip') !== -1) {
            var ancRect = anc2.getBoundingClientRect();
            // Only treat as a carousel clip if ancestor is smaller than full page width
            if (ancRect.width < vp.width * 0.98 || ancRect.height < vp.pageHeight * 0.5) {
              // Is this element's rect completely outside the ancestor's visible rect?
              var fullyOutside =
                rect.right  <= ancRect.left   ||
                rect.left   >= ancRect.right  ||
                rect.bottom <= ancRect.top    ||
                rect.top    >= ancRect.bottom;
              if (fullyOutside) { clippedOut = true; break; }
            }
          }
        } catch(e) {}
        anc2 = anc2.parentElement;
      }
      if (clippedOut) return;

      var r = {
        x: Math.round(rect.x + window.scrollX),
        y: Math.round(rect.y + window.scrollY),
        w: Math.round(rect.width),
        h: Math.round(rect.height)
      };
      var z  = style.zIndex === 'auto' ? 0 : (parseInt(style.zIndex) || 0);
      var op = parseFloat(parseFloat(style.opacity).toFixed(3)) || 1;

      if (tag === 'svg') {
        var svgPctW = rect.width  / vp.width;
        var svgPctH = rect.height / vp.height;
        if (svgPctW > 0.30 && svgPctH > 0.30) return;
        if (isDuplicate(r)) return;
        var iconColor  = resolveIconColor(el);
        var svgPaths   = extractSVGPaths(el);
        var autoAnims  = captureAutoAnimations(el, style);
        var hoverAnims = captureHoverTransitions(el, style);
        var elementIndex = elements.length;
        elements.push({
          type: 'icon', tag: 'svg', id: el.id || '',
          cls: (typeof el.className === 'string' ? el.className : (el.className && el.className.baseVal ? el.className.baseVal : '')).split(' ')[0],
          rect: r, z: z, opacity: op, iconColor: iconColor,
          svgPaths: svgPaths.length > 0 ? svgPaths : null,
          animations: autoAnims.concat(hoverAnims).length > 0 ? autoAnims.concat(hoverAnims) : null
        });
        svgElRefs.push({ domEl: el, iconColor: iconColor, idx: elementIndex });
        counts.icons++;
        return;
      }

      if (tag === 'use') {
        if (isDuplicate(r)) return;
        elements.push({ type: 'icon', tag: 'use', id: el.id || '', cls: '', rect: r, z: z, opacity: op, iconColor: resolveIconColor(el) });
        counts.icons++;
        return;
      }

      if (tag === 'video') {
        if (isDuplicate(r)) return;
        var vSrcs      = getVideoSrcs(el);
        var ytHint     = (!vSrcs.src || vSrcs.src === '') ? detectYtDlpHint(el) : null;
        var vKey       = vSrcs.src ? makeImageKey(vSrcs.src, 'video') : (ytHint ? makeImageKey('yt_' + ytHint.videoId, 'video') : null);
        var pKey       = vSrcs.poster ? makeImageKey(vSrcs.poster, 'vposter') : null;
        var autoAnims2 = captureAutoAnimations(el, style);
        var hoverAnims2 = captureHoverTransitions(el, style);
        elements.push({
          type: 'placeholder', tag: tag, id: el.id || '', cls: '', rect: r, z: z, opacity: op,
          bg: { r:40, g:40, b:40, a:1 }, radius: resolveRadius(el, style), isPlaceholder: true,
          videoUrl: vSrcs.src, videoSources: vSrcs.sources, videoPoster: vSrcs.poster,
          imageUrl: vSrcs.poster || null, imageType: 'video', imageKey: pKey, videoKey: vKey,
          ytDlpHint: ytHint,
          animations: autoAnims2.concat(hoverAnims2).length > 0 ? autoAnims2.concat(hoverAnims2) : null
        });
        counts.videos++;
        return;
      }

      if (tag === 'img') {
        if (isDuplicate(r)) return;
        var imgUrl  = getImgSrc(el);
        var imgKey  = imgUrl ? makeImageKey(imgUrl, 'img') : null;
        var autoAnims3  = captureAutoAnimations(el, style);
        var hoverAnims3 = captureHoverTransitions(el, style);
        elements.push({
          type: 'placeholder', tag: tag, id: el.id || '',
          cls: typeof el.className === 'string' ? el.className.split(' ')[0] : '',
          alt: el.alt || '', rect: r, z: z, opacity: op,
          bg: { r:40, g:40, b:40, a:1 }, radius: resolveRadius(el, style), isPlaceholder: true,
          imageUrl: imgUrl, imageType: 'img', imageKey: imgKey,
          animations: autoAnims3.concat(hoverAnims3).length > 0 ? autoAnims3.concat(hoverAnims3) : null
        });
        counts.images++;
        return;
      }

      if (style.backgroundImage && style.backgroundImage !== 'none') {
        if (rect.width < 20 || rect.height < 20) return;
        if (isDuplicate(r)) return;
        var isGradient = style.backgroundImage.indexOf('gradient') !== -1;
        if (isGradient) {
          var grad = parseGradient(style.backgroundImage);
          var solidBg = parseRGB(style.backgroundColor);
          var autoAnims4  = captureAutoAnimations(el, style);
          var hoverAnims4 = captureHoverTransitions(el, style);
          var elementIndex2 = elements.length;
          elements.push({
            type: 'gradient', tag: tag, id: el.id || '',
            cls: typeof el.className === 'string' ? el.className.split(' ')[0] : '',
            rect: r, z: z, opacity: op, bg: solidBg, gradient: grad, radius: resolveRadius(el, style),
            animations: autoAnims4.concat(hoverAnims4).length > 0 ? autoAnims4.concat(hoverAnims4) : null
          });
          gradElRefs.push({ domEl: el, idx: elementIndex2 });
          counts.gradients++;
          return;
        }
        var bgUrl = getBgImageUrl(style.backgroundImage);
        var bgKey = bgUrl ? makeImageKey(bgUrl, tag) : null;
        var autoAnims5  = captureAutoAnimations(el, style);
        var hoverAnims5 = captureHoverTransitions(el, style);
        elements.push({
          type: 'placeholder', tag: tag, id: el.id || '',
          cls: typeof el.className === 'string' ? el.className.split(' ')[0] : '',
          rect: r, z: z, opacity: op, bg: { r:40, g:40, b:40, a:1 },
          radius: resolveRadius(el, style), isPlaceholder: true,
          imageUrl: bgUrl, imageType: 'bg', imageKey: bgKey,
          animations: autoAnims5.concat(hoverAnims5).length > 0 ? autoAnims5.concat(hoverAnims5) : null
        });
        counts.images++;
        return;
      }

      if (isIconFontEl(el, style)) {
        if (isDuplicate(r)) return;
        var ifColor = resolveIconColor(el);
        var ifIdx   = elements.length;
        elements.push({
          type: 'icon', tag: tag, id: el.id || '',
          cls:  typeof el.className === 'string' ? el.className.split(' ')[0] : '',
          rect: r, z: z, opacity: op, iconColor: ifColor, svgPaths: null
        });
        iconFontElRefs.push({ domEl: el, idx: ifIdx });
        counts.icons++;
        return;
      }

      var bg     = parseRGB(style.backgroundColor);
      var bw     = parseInt(style.borderWidth) || 0;
      var border = null;
      if (bw > 0 && style.borderStyle !== 'none') {
        var bc = parseRGB(style.borderColor);
        if (bc) border = { width: bw, color: bc };
      }

      var rawText = getDirectText(el);
      var hasText = rawText.length > 0;
      var text    = rawText;
      if (hasText && style.textOverflow === 'ellipsis' && style.overflow === 'hidden') {
        text = truncateText(rawText, rect.width, parseInt(style.fontSize) || 14);
      } else if (hasText) {
        text = rawText.slice(0, 200);
      }

      var textColor = hasText ? parseRGB(style.color) : null;
      if (!bg && !border && !hasText) { counts.skipped++; return; }
      if ((bg || border) && !hasText && isDuplicate(r)) { counts.skipped++; return; }

      var fwRaw = style.fontWeight || '400';
      var fwNum = parseInt(fwRaw);
      if (isNaN(fwNum)) fwNum = (fwRaw === 'bold' || fwRaw === 'bolder') ? 700 : 400;

      var autoAnims6  = captureAutoAnimations(el, style);
      var hoverAnims6 = captureHoverTransitions(el, style);
      var btnText = hasText ? isButtonText(el, text) : false;

      elements.push({
        type:         hasText && !bg && !border ? 'text' : 'shape',
        tag:          tag,
        id:           el.id  || '',
        cls:          typeof el.className === 'string' ? el.className.split(' ')[0] : '',
        rect:         r,
        z:            z,
        opacity:      op,
        bg:           bg,
        border:       border,
        radius:       resolveRadius(el, style),
        text:         text,
        textColor:    textColor,
        fontSize:     hasText ? (parseInt(style.fontSize) || 14) : 0,
        fontWeight:   fwNum,
        fontFamily:   hasText ? style.fontFamily.split(',')[0].replace(/['"]/g,'').trim() : 'Arial',
        textAlign:    hasText ? style.textAlign : 'left',
        isButtonText: btnText || undefined,
        animations:   autoAnims6.concat(hoverAnims6).length > 0 ? autoAnims6.concat(hoverAnims6) : null
      });

      if (hasText && !bg && !border) counts.text++;
      else counts.shapes++;

    } catch(e) { counts.skipped++; }
  }

  // ── Recursive shadow DOM walker ────────────────────────────────────────────

  function walkShadowDOM(shadowRoot) {
    try {
      shadowRoot.querySelectorAll('svg, use, img, video').forEach(captureElement);
      shadowRoot.querySelectorAll('*').forEach(function(child) {
        try { if (child.shadowRoot) walkShadowDOM(child.shadowRoot); } catch(e) {}
      });
    } catch(e) {}
  }

  // ── Pre-scroll ─────────────────────────────────────────────────────────────
  console.log('%c⏳ Pre-scrolling to load lazy content…', 'color:#f80;font-weight:bold');
  var _preH    = document.body.scrollHeight;
  var _preStep = Math.max(Math.round(window.innerHeight * 0.7), 300);
  for (var _psi = 0; _psi < _preH; _psi += _preStep) {
    window.scrollTo(0, _psi);
    await new Promise(function(r){ setTimeout(r, 220); });
  }
  // Second pass at half-step offsets
  for (var _psi2 = _preStep/2; _psi2 < _preH; _psi2 += _preStep) {
    window.scrollTo(0, _psi2);
    await new Promise(function(r){ setTimeout(r, 100); });
  }
  window.scrollTo(0, 0);
  await new Promise(function(r){ setTimeout(r, 600); });
  console.log('%c✓ Pre-scroll done — DOM height: ' + document.body.scrollHeight + 'px', 'color:#0f0');

  // ── v18: Force-load lazy images BEFORE DOM walk ───────────────────────────
  // Native loading="lazy" keeps imgs at 0x0 until viewport. Flip to eager,
  // then await img.decode() so every image has real dimensions before capture.
  console.log('%c⏳ Force-loading lazy images…', 'color:#f80;font-weight:bold');
  var _lazyImgs = document.querySelectorAll('img[loading="lazy"]');
  for (var _li = 0; _li < _lazyImgs.length; _li++) { _lazyImgs[_li].loading = 'eager'; }
  document.querySelectorAll('img[data-src]').forEach(function(img) {
    if (!img.src && img.getAttribute('data-src')) img.src = img.getAttribute('data-src');
  });
  var _decodePromises = [];
  document.querySelectorAll('img').forEach(function(img) {
    if (!img.complete && img.src && img.src.indexOf('data:') !== 0) {
      _decodePromises.push(img.decode().catch(function(){}));
    }
  });
  if (_decodePromises.length > 0) await Promise.all(_decodePromises);
  await new Promise(function(r){ setTimeout(r, 500); });
  console.log('%c✓ Lazy images forced: ' + _lazyImgs.length + ' / decodes awaited: ' + _decodePromises.length, 'color:#0f0');

  // ── Walk DOM ───────────────────────────────────────────────────────────────
  document.querySelectorAll('*').forEach(captureElement);
  document.querySelectorAll('*').forEach(function(host) {
    try { if (host.shadowRoot) walkShadowDOM(host.shadowRoot); } catch(e) {}
  });

  // ── v18: ::before / ::after pseudo-element background images ─────────────
  (function capturePseudoElements() {
    var pseudos = ['::before', '::after'];
    document.querySelectorAll('*').forEach(function(el) {
      for (var pi6 = 0; pi6 < pseudos.length; pi6++) {
        try {
          var ps = getComputedStyle(el, pseudos[pi6]);
          var bgImg = ps.backgroundImage;
          if (!bgImg || bgImg === 'none') continue;
          var rect = el.getBoundingClientRect();
          if (rect.width < 4 || rect.height < 4) continue;
          if (bgImg.indexOf('gradient') !== -1) continue;
          var bgUrl2 = getBgImageUrl(bgImg);
          if (!bgUrl2) continue;
          var r2 = {
            x: Math.round(rect.x + window.scrollX),
            y: Math.round(rect.y + window.scrollY),
            w: Math.round(rect.width),
            h: Math.round(rect.height)
          };
          var key2 = makeImageKey(bgUrl2, 'pseudo');
          elements.push({
            type: 'placeholder', tag: pseudos[pi6], id: el.id || '', cls: '',
            rect: r2, z: (parseInt(ps.zIndex) || 0), opacity: parseFloat(ps.opacity) || 1,
            bg: { r:40, g:40, b:40, a:1 }, radius: '0px', isPlaceholder: true,
            imageUrl: bgUrl2, imageType: 'pseudo-bg', imageKey: key2
          });
          counts.images++;
        } catch(e) {}
      }
    });
  })();

  // ── Rasterize SVGs ─────────────────────────────────────────────────────────
  console.log('%c⏳ Rasterizing ' + svgElRefs.length + ' SVG icons…', 'color:#fa0;font-weight:bold');
  var rasterOk = 0; var rasterFail = 0;
  for (var si5 = 0; si5 < svgElRefs.length; si5++) {
    var ref  = svgElRefs[si5];
    var item = elements[ref.idx];
    try {
      var png = await rasterizeSVG(ref.domEl, ref.iconColor, item.rect.w, item.rect.h);
      if (png) { item.imageUrl = png; item.imageKey = makeImageKey(png, 'svg'); item.imageType = 'svg'; rasterOk++; }
      else rasterFail++;
    } catch(e) { rasterFail++; }
  }
  console.log('SVG icons: ' + rasterOk + ' ok / ' + rasterFail + ' failed');

  // ── Rasterize gradients ────────────────────────────────────────────────────
  var gradOk = 0; var gradFail = 0;
  for (var gi = 0; gi < gradElRefs.length; gi++) {
    var gref  = gradElRefs[gi];
    var gitem = elements[gref.idx];
    try {
      var gpng = await rasterizeElement(gref.domEl, gitem.rect.w, gitem.rect.h);
      if (gpng) { gitem.imageUrl = gpng; gitem.imageKey = makeImageKey(gpng, 'grad'); gitem.imageType = 'gradient'; gradOk++; }
      else gradFail++;
    } catch(e) { gradFail++; }
  }
  console.log('Gradients: ' + gradOk + ' rasterized / ' + gradFail + ' parse-only');

  // ── Rasterize icon font elements ───────────────────────────────────────────
  if (iconFontElRefs.length > 0) {
    console.log('%c⏳ Rasterizing ' + iconFontElRefs.length + ' icon-font elements…', 'color:#0af;font-weight:bold');
  }
  var ifOk = 0; var ifFail = 0;
  for (var ifi = 0; ifi < iconFontElRefs.length; ifi++) {
    var ifref  = iconFontElRefs[ifi];
    var ifitem = elements[ifref.idx];
    try {
      var ifpng = await rasterizeElement(ifref.domEl, ifitem.rect.w, ifitem.rect.h);
      if (ifpng) { ifitem.imageUrl = ifpng; ifitem.imageKey = makeImageKey(ifpng, 'iconfont'); ifitem.imageType = 'iconfont'; ifOk++; }
      else { ifFail++; }
    } catch(e) { ifFail++; }
  }
  if (iconFontElRefs.length > 0) { console.log('Icon fonts: ' + ifOk + ' rasterized / ' + ifFail + ' failed'); }

  // ── Scroll animation pass ──────────────────────────────────────────────────
  console.log('%c⏳ Capturing scroll animations…', 'color:#0af;font-weight:bold');
  var scrollWatchList = buildScrollWatchList();
  console.log('  Watching ' + scrollWatchList.length + ' scroll-reactive elements');
  var scrollAnimMap = {};
  try { scrollAnimMap = await captureScrollAnimations(scrollWatchList, elements); }
  catch(e) { console.warn('Scroll animation capture failed: ' + e.message); }
  var scrollAnimCount = 0;
  for (var sek in scrollAnimMap) {
    var idx2 = parseInt(sek);
    if (isNaN(idx2) || !elements[idx2]) continue;
    var scrollAnims = scrollAnimMap[sek];
    if (!elements[idx2].animations) elements[idx2].animations = [];
    for (var sai2 = 0; sai2 < scrollAnims.length; sai2++) {
      elements[idx2].animations.push(scrollAnims[sai2]);
      scrollAnimCount++;
    }
  }
  console.log('Scroll animations: ' + scrollAnimCount + ' deltas across ' + Object.keys(scrollAnimMap).length + ' elements');

  var revealCount = detectScrollRevealCandidates(elements).length;
  console.log('Scroll-reveal candidates synthesized: ' + revealCount);

  // ── v18: CSS rule animation scanner ───────────────────────────────────────
  // ROOT FIX: Chrome does NOT set rule.style.animationName for `animation:`
  // shorthand rules. Must read rule.style.animation and parse the name from it.
  // Also falls back on state-class selectors that are absent at page-load.
  (function cssRuleAnimationScan() {

    var TIMING_KWS = /^(ease|linear|ease-in|ease-out|ease-in-out|step-start|step-end|none|normal|reverse|alternate|alternate-reverse|forwards|backwards|both|running|paused|infinite|unset|initial|inherit)$/i;

    function parseAnimShorthand(sh) {
      if (!sh) return null;
      // var(--x, fallback) wrapping the whole value — extract the fallback
      var wv = sh.match(/^var\([^,]+,\s*(.+)\)$/);
      if (wv) sh = wv[1].trim();
      // Tokenise respecting nested parens
      var tokens = []; var cur = ''; var depth = 0;
      for (var ci = 0; ci < sh.length; ci++) {
        var ch = sh[ci];
        if (ch === '(') { depth++; cur += ch; }
        else if (ch === ')') { depth--; cur += ch; }
        else if (ch === ' ' && depth === 0) { if (cur) { tokens.push(cur); cur = ''; } }
        else { cur += ch; }
      }
      if (cur) tokens.push(cur);
      var animName = null; var duration = 1; var seenDur = false;
      for (var ti = 0; ti < tokens.length; ti++) {
        var t = tokens[ti];
        if (!t) continue;
        if (/^[\d.]+m?s$/.test(t)) {
          if (!seenDur) { duration = parseFloat(t) * (t.indexOf('ms') !== -1 ? 0.001 : 1); seenDur = true; }
          continue;
        }
        if (t.indexOf('var(') === 0) {
          if (!seenDur) {
            var fb = t.match(/,\s*([\d.]+m?s)\s*\)$/);
            if (fb) { duration = parseFloat(fb[1]) * (fb[1].indexOf('ms') !== -1 ? 0.001 : 1); seenDur = true; }
          }
          continue;
        }
        if (/^[\d.]+$/.test(t)) continue;
        if (t.indexOf('cubic-bezier(') === 0 || t.indexOf('steps(') === 0) continue;
        if (TIMING_KWS.test(t)) continue;
        if (animName === null) animName = t;
      }
      return animName ? { name: animName, duration: duration } : null;
    }

    // Fallback-aware selector matching for state classes absent at page-load
    function findDOMMatches(selector) {
      var m;
      try { m = Array.from(document.querySelectorAll(selector)); } catch(e) { m = []; }
      if (m.length > 0) return m;
      // Strip Vue / IO state suffixes
      var s2 = selector
        .replace(/-enter-active\b/g, '').replace(/-leave-active\b/g, '')
        .replace(/-enter-from\b/g,   '').replace(/-leave-from\b/g,   '')
        .replace(/-enter-to\b/g,     '').replace(/-leave-to\b/g,     '')
        .replace(/\.aos-animate\b/g, '').replace(/\.is-visible\b/g,  '')
        .replace(/\.in-view\b/g,     '').replace(/\.revealed\b/g,    '').trim();
      if (s2 && s2 !== selector) {
        try { m = Array.from(document.querySelectorAll(s2)); } catch(e) { m = []; }
        if (m.length > 0) return m;
      }
      // Strip BEM modifier classes (e.g. .block.block_modifier -> .block)
      var parts3 = selector.split(',').map(function(p) { return p.trim(); });
      var clean3 = [];
      for (var pi3 = 0; pi3 < parts3.length; pi3++) {
        var c3 = parts3[pi3].replace(/\.[a-zA-Z][\w-]*(?:_[\w-]+|--[\w-]+)+/g, '').replace(/\s+/g, ' ').trim();
        if (c3 && c3 !== parts3[pi3]) clean3.push(c3);
      }
      if (clean3.length > 0) {
        try { m = Array.from(document.querySelectorAll(clean3.join(', '))); } catch(e) { m = []; }
        if (m.length > 0) return m;
      }
      // Last resort: first class from each comma-part
      var firstCls = selector.split(',').map(function(p) {
        var mc = p.match(/\.([-\w]+)/); return mc ? '.' + mc[1] : null;
      }).filter(Boolean);
      if (firstCls.length > 0) {
        try { m = Array.from(document.querySelectorAll(firstCls.join(', '))); } catch(e) { m = []; }
        if (m.length > 0) return m;
      }
      return [];
    }

    var ruleAnims = [];
    for (var si6 = 0; si6 < document.styleSheets.length; si6++) {
      try {
        var sheet6 = document.styleSheets[si6];
        var rules6; try { rules6 = sheet6.cssRules || sheet6.rules; } catch(e) { continue; }
        if (!rules6) continue;
        for (var ri6 = 0; ri6 < rules6.length; ri6++) {
          var rule6 = rules6[ri6];
          if (!rule6.style || !rule6.selectorText) continue;

          // animationName is EMPTY for shorthand `animation:` rules — parse shorthand directly
          var an6 = rule6.style.animationName;
          var sp6 = null;
          if (!an6 || an6 === 'none' || an6 === 'unset' || an6 === '') {
            sp6 = parseAnimShorthand(rule6.style.animation);
            if (!sp6) continue;
            an6 = sp6.name;
          }
          if (!an6 || an6 === 'none' || an6.indexOf('var(') !== -1) continue;

          var animNames6 = an6.split(',').map(function(s){ return s.trim(); }).filter(Boolean);
          var dur6raw    = rule6.style.animationDuration || '';
          var delay6     = rule6.style.animationDelay || '0s';
          var iter6      = rule6.style.animationIterationCount || '1';
          var durList6   = dur6raw ? dur6raw.split(',').map(function(s){ return parseFloat(s) || 1; }) : null;
          var delayList6 = delay6.split(',').map(function(s){ return parseFloat(s) || 0; });

          for (var ani6 = 0; ani6 < animNames6.length; ani6++) {
            var iterVal6 = (iter6.split(',')[ani6] || iter6).trim();
            var dur6val  = durList6
              ? (durList6[ani6 % durList6.length] || 1)
              : (sp6 ? sp6.duration : 1);
            ruleAnims.push({
              selector: rule6.selectorText,
              animName: animNames6[ani6],
              duration: dur6val,
              delay:    delayList6[ani6 % delayList6.length] || 0,
              iter:     iterVal6 === 'infinite' ? -1 : (parseFloat(iterVal6) || 1)
            });
          }
        }
      } catch(e) {}
    }

    var cssAnimCount = 0;
    for (var rai = 0; rai < ruleAnims.length; rai++) {
      var ra = ruleAnims[rai];
      var kfs6 = parseKeyframesRule(ra.animName);
      if (!kfs6 || kfs6.length === 0) continue;

      var domMatches6 = findDOMMatches(ra.selector);
      if (domMatches6.length === 0) continue;

      var animData6 = { name: ra.animName, trigger: 'auto', duration: ra.duration,
        iterationCount: ra.iter, delay: ra.delay, keyframes: kfs6, _source: 'css-rule-scan' };

      for (var mi6 = 0; mi6 < domMatches6.length; mi6++) {
        try {
          var domEl6 = domMatches6[mi6];
          var rect6  = domEl6.getBoundingClientRect();
          var elX6   = Math.round(rect6.left + window.scrollX);
          var elY6   = Math.round(rect6.top  + window.scrollY);
          var bestIdx6 = -1; var bestDist6 = 120;
          for (var ei6 = 0; ei6 < elements.length; ei6++) {
            var er6 = elements[ei6].rect; if (!er6) continue;
            var dist6 = Math.abs(er6.x - elX6) + Math.abs(er6.y - elY6);
            if (dist6 < bestDist6) { bestDist6 = dist6; bestIdx6 = ei6; }
          }
          if (bestIdx6 < 0) continue;
          if (!elements[bestIdx6].animations) elements[bestIdx6].animations = [];
          var dup6 = false;
          for (var dai6 = 0; dai6 < elements[bestIdx6].animations.length; dai6++) {
            if (elements[bestIdx6].animations[dai6].name === ra.animName) { dup6 = true; break; }
          }
          if (!dup6) { elements[bestIdx6].animations.push(animData6); cssAnimCount++; }
        } catch(e) {}
      }
    }
    console.log('CSS rule animation scan: ' + cssAnimCount + ' animations injected from ' + ruleAnims.length + ' rules');
  })();

  // ── Compute comp duration ──────────────────────────────────────────────────
  var maxAnimDur = 10;
  elements.forEach(function(el) {
    if (!el.animations) return;
    el.animations.forEach(function(anim) {
      var totalDur;
      if (anim.trigger === 'scroll') { totalDur = 5; }
      else if (anim.iterationCount === -1) { totalDur = (anim.delay || 0) + anim.duration; }
      else { totalDur = (anim.delay || 0) + anim.duration * (anim.iterationCount || 1); }
      if (totalDur > maxAnimDur) maxAnimDur = totalDur;
    });
  });
  if (maxAnimDur > 120) maxAnimDur = 120;

  var maxScrollY = Math.max(0, document.body.scrollHeight - window.innerHeight);
  if (maxScrollY > 0 && scrollAnimCount > 0) { if (maxAnimDur < 20) maxAnimDur = 20; }

  // ── Sort & build manifest ──────────────────────────────────────────────────
  elements.sort(function(a, b) { return a.z - b.z; });

  var imageManifest = [];
  var ytDlpManifest = [];
  elements.forEach(function(el) {
    if (el.imageUrl && el.imageKey) {
      imageManifest.push({ key: el.imageKey, url: el.imageUrl, type: el.imageType || 'img' });
    }
    if (el.videoUrl && el.videoKey) {
      imageManifest.push({ key: el.videoKey, url: el.videoUrl, type: 'video' });
    }
    if (el.ytDlpHint && el.videoKey) {
      ytDlpManifest.push({ key: el.videoKey, hint: el.ytDlpHint });
    }
  });

  var payload = {
    meta: {
      version:          18,
      extractedAt:      new Date().toISOString(),
      url:              vp.url,
      title:            vp.title,
      elementCount:     elements.length,
      compDuration:     maxAnimDur,
      maxScrollY:       maxScrollY,
      scrollNullRange:  {
        yMin: 0, yMax: maxScrollY,
        note: 'SCROLL NULL Y=0 is page top; Y=compHeight is page bottom.'
      }
    },
    viewport:      vp,
    bodyBg:        bodyBg,
    imageManifest: imageManifest,
    ytDlpManifest: ytDlpManifest,
    elements:      elements
  };

  var blob = new Blob([JSON.stringify(payload, null, 2)], { type:'application/json' });
  var a    = document.createElement('a');
  a.href   = URL.createObjectURL(blob);
  a.download = 'ui_extract.json';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);

  console.log('%c✅ UI Extractor v18 — ' + elements.length + ' elements  compDuration=' + maxAnimDur + 's  pageHeight=' + vp.pageHeight + 'px', 'color:#0f0;font-size:16px;font-weight:bold');
  console.log('Shapes:' + counts.shapes + ' | Text:' + counts.text + ' | Icons:' + counts.icons
    + ' | Gradients:' + counts.gradients + ' | Images:' + counts.images
    + ' | Videos:' + counts.videos + ' | Skipped:' + counts.skipped);
  console.log('Scroll animations: ' + scrollAnimCount + ' | Scroll reveals: ' + revealCount + ' | yt-dlp hints: ' + ytDlpManifest.length);

})();
