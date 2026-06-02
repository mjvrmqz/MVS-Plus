#!/usr/bin/env node
/**
 * UI Image + Video Downloader v7
 * Usage:  node download_images.js /path/to/ui_extract.json
 *
 * v7 changes:
 *   - RETRY WITHOUT REFERER: Images blocked by CORS/hotlink protection are
 *     retried without Origin/Referer headers. Many CDNs reject requests that
 *     look like they come from another domain but accept bare requests.
 *   - RELATIVE URL RESOLUTION: data-src / lazy-load attrs sometimes contain
 *     relative paths. These are now resolved against the page origin.
 *   - ALL OTHER v6 BEHAVIOR RETAINED.
 */

var fs         = require('fs');
var path       = require('path');
var https      = require('https');
var http       = require('http');
var os         = require('os');
var url_mod    = require('url');
var child_proc = require('child_process');

// sips is built into macOS — no install needed. Used to convert WebP/AVIF/SVG → PNG.

var jsonPath = process.argv[2];
if (!jsonPath) {
  console.error('Usage: node download_images.js /path/to/ui_extract.json');
  process.exit(1);
}

var raw;
try { raw = fs.readFileSync(jsonPath, 'utf8'); }
catch (e) { console.error('Cannot read file: ' + jsonPath); process.exit(1); }

var data;
try { data = JSON.parse(raw); }
catch (e) { console.error('Invalid JSON: ' + e.message); process.exit(1); }

var manifest      = data.imageManifest  || [];
var ytDlpManifest = data.ytDlpManifest  || [];

if (manifest.length === 0 && ytDlpManifest.length === 0) {
  console.log('No images/videos in manifest.');
  process.exit(0);
}

var pageUrl = (data.meta && data.meta.url) ? data.meta.url : 'https://www.youtube.com/';

function slugify(str) {
  return (str || 'ui_images')
    .replace(/https?:\/\//g, '')
    .replace(/[^a-zA-Z0-9]+/g, '_')
    .slice(0, 40)
    .replace(/^_+|_+$/g, '');
}

var folderName = slugify(data.meta && data.meta.title ? data.meta.title : 'ui_images');
var outDir     = path.join(os.homedir(), 'Downloads', 'ui_images', folderName);
if (!fs.existsSync(outDir)) { fs.mkdirSync(outDir, { recursive: true }); }

console.log('Output folder: ' + outDir);
console.log('Page URL (Referer): ' + pageUrl);

// Separate image and video entries
var imageItems = [];
var videoItems = [];
manifest.forEach(function(item) {
  if (item.type === 'video') videoItems.push(item);
  else imageItems.push(item);
});

// Build a set of videoKeys already covered by ytDlpManifest so we don't
// attempt a direct HTTP download on adaptive streams that will fail anyway.
var ytDlpKeySet = {};
ytDlpManifest.forEach(function(entry) { ytDlpKeySet[entry.key] = entry; });

console.log('Downloading ' + imageItems.length + ' images, '
  + videoItems.length + ' direct videos, '
  + ytDlpManifest.length + ' yt-dlp videos…\n');

// ── Format detection from magic bytes ─────────────────────────────────────────

function detectFormat(buf) {
  if (!buf || buf.length < 4) return { ext: '.bin', isWebp: false, valid: false };
  var b = buf;
  if (b[0] === 0xFF && b[1] === 0xD8)
    return { ext: '.jpg', isWebp: false, valid: true };
  if (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4E && b[3] === 0x47)
    return { ext: '.png', isWebp: false, valid: true };
  if (b[0] === 0x47 && b[1] === 0x49 && b[2] === 0x46)
    return { ext: '.gif', isWebp: false, valid: true };
  if (buf.length >= 12 &&
      b[0] === 0x52 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x46 &&
      b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50)
    return { ext: '.webp', isWebp: true, valid: true };
  if (buf.length >= 12 &&
      b[4] === 0x66 && b[5] === 0x74 && b[6] === 0x79 && b[7] === 0x70) {
    // Check ftyp brand: AVIF vs MP4
    var brand = buf.slice(8, 12).toString('ascii');
    if (brand === 'avif' || brand === 'avis') {
      return { ext: '.avif', isWebp: false, isAvif: true, valid: true };
    }
    return { ext: '.mp4', isWebp: false, valid: true };
  }
  if (b[0] === 0x1A && b[1] === 0x45 && b[2] === 0xDF && b[3] === 0xA3)
    return { ext: '.webm', isWebp: false, valid: true };
  if (buf.length >= 12 &&
      b[4] === 0x66 && b[5] === 0x74 && b[6] === 0x79 && b[7] === 0x70 &&
      b[8] === 0x71 && b[9] === 0x74)
    return { ext: '.mov', isWebp: false, valid: true };
  var head = buf.slice(0, 5).toString('utf8');
  if (head.slice(0, 4) === '<svg' || head === '<?xml')
    return { ext: '.svg', isWebp: false, valid: true };
  var preview = buf.slice(0, 120).toString('utf8').replace(/[\r\n]/g, ' ');
  return { ext: '.bin', isWebp: false, valid: false, preview: preview };
}

function detectVideoExt(contentType, buf) {
  if (contentType) {
    var ct = contentType.toLowerCase();
    if (ct.indexOf('mp4')       !== -1) return '.mp4';
    if (ct.indexOf('webm')      !== -1) return '.webm';
    if (ct.indexOf('ogg')       !== -1) return '.ogg';
    if (ct.indexOf('quicktime') !== -1 || ct.indexOf('mov') !== -1) return '.mov';
    if (ct.indexOf('mpeg')      !== -1) return '.mpeg';
  }
  if (buf) {
    var fmt = detectFormat(buf.slice(0, 16));
    if (fmt.valid) return fmt.ext;
  }
  return '.mp4';
}

// ── data: URL decoder ─────────────────────────────────────────────────────────

function decodeDataUrl(dataUrl) {
  if (!dataUrl || dataUrl.indexOf('data:') !== 0) return null;
  try {
    var commaIdx = dataUrl.indexOf(',');
    if (commaIdx === -1) return null;
    var header   = dataUrl.slice(5, commaIdx);
    var payload  = dataUrl.slice(commaIdx + 1);
    var isBase64 = header.indexOf(';base64') !== -1;
    var mime     = header.replace(';base64', '').split(';')[0].trim();
    var buf = isBase64 ? Buffer.from(payload, 'base64') : Buffer.from(decodeURIComponent(payload), 'utf8');
    var ext = '.bin';
    if      (mime === 'image/png')              ext = '.png';
    else if (mime === 'image/jpeg' || mime === 'image/jpg') ext = '.jpg';
    else if (mime === 'image/gif')              ext = '.gif';
    else if (mime === 'image/svg+xml')          ext = '.svg';
    else if (mime === 'image/webp')             ext = '.webp';
    else if (mime === 'video/mp4')              ext = '.mp4';
    else if (mime === 'video/webm')             ext = '.webm';
    else { var fmt = detectFormat(buf); if (fmt.valid) ext = fmt.ext; }
    return { buf: buf, ext: ext };
  } catch(e) { return null; }
}

// ── Resolve potentially-relative image URLs against page origin ──────────────

function resolveUrl(rawUrl, baseUrl) {
  if (!rawUrl) return rawUrl;
  if (rawUrl.indexOf('data:') === 0) return rawUrl;
  if (rawUrl.indexOf('http://') === 0 || rawUrl.indexOf('https://') === 0) return rawUrl;
  // Protocol-relative
  if (rawUrl.indexOf('//') === 0) return 'https:' + rawUrl;
  // Root-relative
  try {
    var parsed = url_mod.parse(baseUrl);
    if (rawUrl.indexOf('/') === 0) return parsed.protocol + '//' + parsed.host + rawUrl;
    // Relative path
    var base = parsed.protocol + '//' + parsed.host + (parsed.pathname || '/').replace(/\/[^/]*$/, '/');
    return base + rawUrl;
  } catch(e) { return rawUrl; }
}

// Resolve all manifest URLs against pageUrl
manifest.forEach(function(item) {
  if (item.url && item.url.indexOf('data:') !== 0) {
    item.url = resolveUrl(item.url, pageUrl);
  }
});

// ── HTTP download with redirect following ─────────────────────────────────────

function downloadToBuffer(srcUrl, referer, redirects, acceptHeader, cb) {
  if (redirects > 5) { cb(new Error('Too many redirects')); return; }
  var parsed = url_mod.parse(srcUrl);
  var mod    = parsed.protocol === 'https:' ? https : http;
  var opts = {
    hostname: parsed.hostname, port: parsed.port, path: parsed.path, method: 'GET',
    headers: {
      'User-Agent':      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
      'Accept':          acceptHeader,
      'Accept-Language': 'en-US,en;q=0.9',
      'Referer':         referer,
      'Origin':          parsed.protocol + '//' + parsed.hostname,
      'sec-fetch-dest':  'image', 'sec-fetch-mode': 'no-cors', 'sec-fetch-site': 'cross-site'
    }
  };
  var req = mod.request(opts, function(res) {
    if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
      var loc = res.headers.location;
      if (loc.indexOf('http') !== 0) loc = parsed.protocol + '//' + parsed.hostname + loc;
      res.resume();
      downloadToBuffer(loc, referer, redirects + 1, acceptHeader, cb);
      return;
    }
    if (res.statusCode !== 200) { res.resume(); cb(new Error('HTTP ' + res.statusCode), null, res.headers); return; }
    var chunks = [];
    res.on('data', function(chunk) { chunks.push(chunk); });
    res.on('end',  function() { cb(null, Buffer.concat(chunks), res.headers); });
    res.on('error', function(e) { cb(e, null, res.headers); });
  });
  req.on('error', cb);
  req.end();
}

function streamToDisk(srcUrl, referer, redirects, destPath, cb) {
  if (redirects > 5) { cb(new Error('Too many redirects')); return; }
  var parsed = url_mod.parse(srcUrl);
  var mod    = parsed.protocol === 'https:' ? https : http;
  var opts = {
    hostname: parsed.hostname, port: parsed.port, path: parsed.path, method: 'GET',
    headers: {
      'User-Agent':      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
      'Accept':          'video/*, */*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.9',
      'Referer':         referer,
      'Origin':          parsed.protocol + '//' + parsed.hostname,
      'Range':           'bytes=0-16'
    }
  };
  var sniffReq = mod.request(opts, function(res) {
    if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
      var loc = res.headers.location;
      if (loc.indexOf('http') !== 0) loc = parsed.protocol + '//' + parsed.hostname + loc;
      res.resume(); streamToDisk(loc, referer, redirects + 1, destPath, cb); return;
    }
    var ct = res.headers['content-type'] || '';
    var sniffBuf = [];
    res.on('data', function(c) { sniffBuf.push(c); });
    res.on('end', function() {
      var head = Buffer.concat(sniffBuf);
      var ext  = detectVideoExt(ct, head);
      var finalPath = destPath.replace(/\.[^.]+$/, '') + ext;
      delete opts.headers['Range'];
      var fullReq = mod.request(opts, function(fullRes) {
        if (fullRes.statusCode >= 300 && fullRes.statusCode < 400 && fullRes.headers.location) {
          var loc = fullRes.headers.location;
          if (loc.indexOf('http') !== 0) loc = parsed.protocol + '//' + parsed.hostname + loc;
          fullRes.resume(); streamToDisk(loc, referer, 0, destPath, cb); return;
        }
        if (fullRes.statusCode !== 200 && fullRes.statusCode !== 206) {
          fullRes.resume(); cb(new Error('HTTP ' + fullRes.statusCode + ' on full download'), null); return;
        }
        var out  = fs.createWriteStream(finalPath);
        var size = 0;
        fullRes.on('data', function(chunk) { size += chunk.length; });
        fullRes.pipe(out);
        out.on('finish', function() { cb(null, finalPath, size); });
        out.on('error',  function(e) { cb(e, null); });
        fullRes.on('error', function(e) { cb(e, null); });
      });
      fullReq.on('error', function(e) { cb(e, null); });
      fullReq.end();
    });
    res.on('error', function(e) { cb(e, null); });
  });
  sniffReq.on('error', function(e) { cb(e, null); });
  sniffReq.end();
}

// ── yt-dlp downloader ─────────────────────────────────────────────────────────
//
// Invokes yt-dlp as a subprocess to download a YouTube (or other) video.
// Uses format selector: bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best
// Output is placed in outDir with the videoKey as filename.
//
// cb(err, finalPath)

function downloadWithYtDlp(pageUrl, videoKey, cb) {
  // Find yt-dlp binary
  var ytDlpBin = 'yt-dlp';
  try {
    child_proc.execSync('which yt-dlp 2>/dev/null || command -v yt-dlp 2>/dev/null', { stdio: 'pipe' });
  } catch(e) {
    // Try common install locations
    var candidates = [
      '/usr/local/bin/yt-dlp',
      '/opt/homebrew/bin/yt-dlp',
      path.join(os.homedir(), '.local/bin/yt-dlp'),
      path.join(os.homedir(), 'Library/Python/3.11/bin/yt-dlp'),
      path.join(os.homedir(), 'Library/Python/3.12/bin/yt-dlp')
    ];
    var found = false;
    for (var ci = 0; ci < candidates.length; ci++) {
      if (fs.existsSync(candidates[ci])) { ytDlpBin = candidates[ci]; found = true; break; }
    }
    if (!found) {
      cb(new Error('yt-dlp not found. Install with: brew install yt-dlp  or  pip install yt-dlp'));
      return;
    }
  }

  // Sanitize key for filename
  var safeKey = videoKey.replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 60);
  var outTemplate = path.join(outDir, safeKey + '.%(ext)s');

  // Format: prefer h264 mp4 for AE compatibility
  var formatStr = 'bestvideo[height<=1080][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best';

  var args = [
    '--format', formatStr,
    '--merge-output-format', 'mp4',
    '--output', outTemplate,
    '--no-playlist',
    '--quiet',
    '--no-warnings',
    '--progress',
    pageUrl
  ];

  console.log('  ⬇ yt-dlp: ' + pageUrl.slice(0, 80) + '…');

  var proc = child_proc.spawn(ytDlpBin, args, { stdio: ['ignore', 'pipe', 'pipe'] });
  var stdout = ''; var stderr = '';
  proc.stdout.on('data', function(d) { stdout += d.toString(); });
  proc.stderr.on('data', function(d) { stderr += d.toString(); });
  proc.on('close', function(code) {
    if (code !== 0) {
      cb(new Error('yt-dlp exited ' + code + ': ' + (stderr || stdout).slice(0, 200)));
      return;
    }
    // Find the downloaded file
    var finalPath = null;
    var exts = ['.mp4', '.mkv', '.webm', '.mov', '.m4v'];
    for (var ei = 0; ei < exts.length; ei++) {
      var candidate = path.join(outDir, safeKey + exts[ei]);
      if (fs.existsSync(candidate) && fs.statSync(candidate).size > 1024) {
        finalPath = candidate;
        break;
      }
    }
    if (!finalPath) {
      // yt-dlp may have used a different filename; search for recent files
      try {
        var files = fs.readdirSync(outDir);
        var now   = Date.now();
        for (var fi = 0; fi < files.length; fi++) {
          var fp = path.join(outDir, files[fi]);
          var stat = fs.statSync(fp);
          if (stat.size > 1024 && (now - stat.mtimeMs) < 30000) {
            var ext2 = path.extname(files[fi]).toLowerCase();
            if (['.mp4','.mkv','.webm','.mov','.m4v'].indexOf(ext2) !== -1) {
              finalPath = fp;
              break;
            }
          }
        }
      } catch(e) {}
    }
    if (!finalPath) {
      cb(new Error('yt-dlp succeeded but output file not found'));
      return;
    }
    var sizeBytes = fs.statSync(finalPath).size;
    cb(null, finalPath, sizeBytes);
  });
  proc.on('error', function(e) { cb(e); });
}

// ── Per-image download ────────────────────────────────────────────────────────

// ── sips-based image converter ───────────────────────────────────────────────
// Converts WebP / AVIF / SVG buffers to PNG using macOS sips (always available).
// cb(err, pngBuf, '.png')

function convertToPng(buf, srcExt, cb) {
  var tmpSrc = path.join(os.tmpdir(), 'ui_dl_' + Date.now() + (srcExt || '.webp'));
  var tmpDst = tmpSrc.replace(/\.[^.]+$/, '.png');
  try { fs.writeFileSync(tmpSrc, buf); } catch(e) { cb(e); return; }
  var sips = child_proc.spawn('sips', ['-s', 'format', 'png', tmpSrc, '--out', tmpDst], { stdio: 'pipe' });
  sips.on('close', function(code) {
    try { fs.unlinkSync(tmpSrc); } catch(e) {}
    if (code === 0 && fs.existsSync(tmpDst) && fs.statSync(tmpDst).size > 0) {
      try { var png = fs.readFileSync(tmpDst); fs.unlinkSync(tmpDst); cb(null, png, '.png'); }
      catch(e) { cb(e); }
    } else {
      // sips failed (e.g. on SVG with no dimensions) — save original
      cb(null, buf, srcExt || '.bin');
    }
  });
  sips.on('error', function(e) { cb(null, buf, srcExt || '.bin'); }); // sips missing — keep as-is
}

function downloadImage(item, cb) {
  var ACCEPT_FULL = 'image/avif,image/webp,image/apng,image/jpeg,image/*,*/*;q=0.8';

  downloadToBuffer(item.url, pageUrl, 0, ACCEPT_FULL, function(err, buf, headers) {
    if (err) {
      // Retry without Referer/Origin — works for CDNs with hotlink protection
      var parsed = url_mod.parse(item.url);
      var bareOpts = {
        hostname: parsed.hostname, port: parsed.port, path: parsed.path, method: 'GET',
        headers: {
          'User-Agent':      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
          'Accept':          ACCEPT_FULL,
          'Accept-Language': 'en-US,en;q=0.9'
        }
      };
      var mod2 = parsed.protocol === 'https:' ? https : http;
      var retryReq = mod2.request(bareOpts, function(res) {
        if (res.statusCode !== 200) { res.resume(); cb(err, null, null); return; } // return original error
        var chunks = [];
        res.on('data', function(c) { chunks.push(c); });
        res.on('end', function() {
          var retryBuf = Buffer.concat(chunks);
          var fmt2 = detectFormat(retryBuf);
          if (!fmt2.valid) { cb(err, null, null); return; }
          if (fmt2.isWebp || fmt2.isAvif || fmt2.ext === '.svg') {
            convertToPng(retryBuf, fmt2.ext, cb); return;
          }
          cb(null, retryBuf, fmt2.ext);
        });
        res.on('error', function() { cb(err, null, null); });
      });
      retryReq.on('error', function() { cb(err, null, null); });
      retryReq.end();
      return;
    }
    var fmt = detectFormat(buf);
    if (!fmt.valid) { cb(new Error('Not a valid image. Preview: ' + (fmt.preview || '?')), null, null); return; }
    if (fmt.isWebp || fmt.isAvif || fmt.ext === '.svg') {
      convertToPng(buf, fmt.ext, cb);
      return;
    }
    cb(null, buf, fmt.ext);
  });
}

// ── Counters & result maps ────────────────────────────────────────────────────

var imageMap  = {};
var videoMap  = {};
var imgDone   = 0; var imgErrors  = 0;
var vidDone   = 0; var vidErrors  = 0;
var ytDone    = 0; var ytErrors   = 0;

// Total tasks to complete before calling finish()
var totalTasks = imageItems.length + videoItems.length + ytDlpManifest.length;
var completedTasks = 0;

function taskDone() {
  completedTasks++;
  if (completedTasks >= totalTasks) finish();
}

// ── Process images ────────────────────────────────────────────────────────────

imageItems.forEach(function(item) {
  var baseKey = item.key.replace(/\.(jpg|jpeg|png|gif|webp|svg|avif|bin)$/i, '');

  // ── inline data: URLs ────────────────────────────────────────────────────
  if (item.url && item.url.indexOf('data:') === 0) {
    var decoded = decodeDataUrl(item.url);
    if (!decoded) {
      console.error('  ✗ ' + item.key + ' (malformed data URL)');
      imgErrors++; taskDone(); return;
    }
    // SVG / WebP / AVIF must be converted to PNG for AE
    if (decoded.ext === '.svg' || decoded.ext === '.webp' || decoded.ext === '.avif') {
      convertToPng(decoded.buf, decoded.ext, function(convErr, outBuf, outExt) {
        if (convErr) { outBuf = decoded.buf; outExt = decoded.ext; }
        var filename = baseKey + outExt;
        var destPath = path.join(outDir, filename);
        try {
          fs.writeFileSync(destPath, outBuf);
          console.log('  ✓ ' + filename + ' (' + outBuf.length + ' bytes, inline→PNG)');
          imageMap[item.key] = destPath; imgDone++;
        } catch(e) {
          console.error('  ✗ ' + item.key + ' write failed: ' + e.message);
          imgErrors++;
        }
        taskDone();
      });
      return;
    }
    // All other inline data (PNG/JPG/GIF) — write directly
    var filenameD = baseKey + decoded.ext;
    var destPathD = path.join(outDir, filenameD);
    try {
      fs.writeFileSync(destPathD, decoded.buf);
      console.log('  ✓ ' + filenameD + ' (' + decoded.buf.length + ' bytes, inline ' + decoded.ext.slice(1).toUpperCase() + ')');
      imageMap[item.key] = destPathD; imgDone++;
    } catch(e) {
      console.error('  ✗ ' + item.key + ' write failed: ' + e.message);
      imgErrors++;
    }
    taskDone(); return;
  }

  // ── cached check (png/jpg/gif only — no svg/webp/avif) ───────────────────
  var cachedPath = null;
  var cacheExts = ['.png', '.jpg', '.jpeg', '.gif'];
  for (var ei = 0; ei < cacheExts.length; ei++) {
    var candidate = path.join(outDir, baseKey + cacheExts[ei]);
    if (fs.existsSync(candidate) && fs.statSync(candidate).size > 0) {
      var existing = fs.readFileSync(candidate);
      var fmtC = detectFormat(existing);
      if (fmtC.valid && !fmtC.isWebp) { cachedPath = candidate; break; }
    }
  }
  if (cachedPath) {
    console.log('  ✓ (cached) ' + path.basename(cachedPath));
    imageMap[item.key] = cachedPath; imgDone++; taskDone(); return;
  }

  // ── download ─────────────────────────────────────────────────────────────
  downloadImage(item, function(err, buf, ext) {
    if (err) {
      console.error('  ✗ ' + item.key + '\n    ' + err.message);
      imgErrors++;
    } else {
      var filename = baseKey + ext;
      var destPath = path.join(outDir, filename);
      fs.writeFileSync(destPath, buf);
      console.log('  ✓ ' + filename + ' (' + buf.length + ' bytes, ' + ext.slice(1).toUpperCase() + ')');
      imageMap[item.key] = destPath; imgDone++;
    }
    taskDone();
  });
});

// ── Process direct video URLs ─────────────────────────────────────────────────

if (videoItems.length > 0) {
  console.log('\n── Direct Videos ─────────────────────────────────────────────────');
}

videoItems.forEach(function(item) {
  // If this video key is covered by yt-dlp, skip direct download
  if (ytDlpKeySet[item.key]) {
    console.log('  ↷ ' + item.key + ' (will use yt-dlp)');
    vidDone++; taskDone(); return;
  }

  var baseKey = item.key.replace(/\.(mp4|webm|ogg|mov|mpeg|bin)$/i, '');

  if (item.url && item.url.indexOf('data:') === 0) {
    var decoded = decodeDataUrl(item.url);
    if (!decoded) {
      console.error('  ✗ video ' + item.key + ' (malformed data URL)');
      vidErrors++; taskDone(); return;
    }
    var filename = baseKey + decoded.ext;
    var destPath = path.join(outDir, filename);
    try {
      fs.writeFileSync(destPath, decoded.buf);
      console.log('  ✓ video ' + filename + ' (' + decoded.buf.length + ' bytes, inline)');
      videoMap[item.key] = destPath; vidDone++;
    } catch(e) {
      console.error('  ✗ video ' + item.key + ' write failed: ' + e.message);
      vidErrors++;
    }
    taskDone(); return;
  }

  if (!item.url) {
    console.error('  ✗ video ' + item.key + ' (no URL)');
    vidErrors++; taskDone(); return;
  }

  var vidExts = ['.mp4', '.webm', '.ogg', '.mov', '.mpeg'];
  var cachedVid = null;
  for (var vi = 0; vi < vidExts.length; vi++) {
    var vc = path.join(outDir, baseKey + vidExts[vi]);
    if (fs.existsSync(vc) && fs.statSync(vc).size > 1024) { cachedVid = vc; break; }
  }
  if (cachedVid) {
    console.log('  ✓ video (cached) ' + path.basename(cachedVid));
    videoMap[item.key] = cachedVid; vidDone++; taskDone(); return;
  }

  var tmpPath = path.join(outDir, baseKey + '.mp4');
  console.log('  ⬇ video ' + item.key + ' from ' + (item.url || '').slice(0, 80) + '…');
  streamToDisk(item.url, pageUrl, 0, tmpPath, function(err, finalPath, size) {
    if (err) {
      console.error('  ✗ video ' + item.key + '\n    ' + err.message);
      vidErrors++;
    } else {
      var sizeStr = size > 1048576 ? (size / 1048576).toFixed(1) + ' MB' : (size / 1024).toFixed(0) + ' KB';
      console.log('  ✓ video ' + path.basename(finalPath) + ' (' + sizeStr + ')');
      videoMap[item.key] = finalPath; vidDone++;
    }
    taskDone();
  });
});

// ── Process yt-dlp videos (sequential to avoid hammering) ────────────────────

if (ytDlpManifest.length > 0) {
  console.log('\n── yt-dlp Videos ─────────────────────────────────────────────────');
}

// Run yt-dlp downloads sequentially (yt-dlp itself parallelizes internally)
var ytDlpQueue = ytDlpManifest.slice();

function processNextYtDlp() {
  if (ytDlpQueue.length === 0) return;
  var entry = ytDlpQueue.shift();

  // Check cache
  var safeKey = entry.key.replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 60);
  var cachedExts = ['.mp4', '.mkv', '.webm', '.mov', '.m4v'];
  var cachedVid = null;
  for (var ci = 0; ci < cachedExts.length; ci++) {
    var cc = path.join(outDir, safeKey + cachedExts[ci]);
    if (fs.existsSync(cc) && fs.statSync(cc).size > 1024) { cachedVid = cc; break; }
  }
  if (cachedVid) {
    console.log('  ✓ yt-dlp (cached) ' + path.basename(cachedVid));
    videoMap[entry.key] = cachedVid; ytDone++; taskDone();
    processNextYtDlp();
    return;
  }

  var dlUrl = (entry.hint && entry.hint.pageUrl) ? entry.hint.pageUrl : pageUrl;
  downloadWithYtDlp(dlUrl, entry.key, function(err, finalPath, size) {
    if (err) {
      console.error('  ✗ yt-dlp ' + entry.key + '\n    ' + err.message);
      ytErrors++;
    } else {
      var sizeStr = size > 1048576 ? (size / 1048576).toFixed(1) + ' MB' : (size / 1024).toFixed(0) + ' KB';
      console.log('  ✓ yt-dlp ' + path.basename(finalPath) + ' (' + sizeStr + ')');
      videoMap[entry.key] = finalPath; ytDone++;
    }
    taskDone();
    processNextYtDlp();
  });
}

if (ytDlpManifest.length > 0) {
  processNextYtDlp();
} else if (totalTasks === 0) {
  finish();
}

// Handle fully empty manifests
if (totalTasks === 0) { finish(); }

// ── Finish ────────────────────────────────────────────────────────────────────

function finish() {
  var imgMapPath = path.join(outDir, 'image_map.json');
  var vidMapPath = path.join(outDir, 'video_map.json');
  fs.writeFileSync(imgMapPath, JSON.stringify(imageMap, null, 2));
  fs.writeFileSync(vidMapPath, JSON.stringify(videoMap, null, 2));

  console.log('\n── Summary ──────────────────────────────────────────────────────');
  console.log('Images:       downloaded=' + imgDone  + '  failed=' + imgErrors);
  console.log('Direct video: downloaded=' + vidDone  + '  failed=' + vidErrors);
  console.log('yt-dlp video: downloaded=' + ytDone   + '  failed=' + ytErrors);
  console.log('image_map.json: ' + imgMapPath);
  console.log('video_map.json: ' + vidMapPath);
  if (imgErrors + vidErrors + ytErrors > 0)
    console.log('Note: failed images appear as grey placeholders in AE; failed videos are skipped.');
  if (ytErrors > 0)
    console.log('Tip: make sure yt-dlp is installed (brew install yt-dlp) and up to date (yt-dlp -U).');
}
