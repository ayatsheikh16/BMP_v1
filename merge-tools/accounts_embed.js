/* =====================================================================
   ACCOUNTS and ACTIONS — the "BMP account creation review" file, embedded exactly as designed.
   It runs as its own page inside the portal (like Plans and Add-on packs): its screens, rules and data
   are unchanged. Only its own sidebar and top bar are hidden; the portal's sidebar, breadcrumbs and
   persona switcher drive it. One frame is kept for the whole session so its data survives navigation.
   ===================================================================== */
const AC_VIEWS = ['accounts', 'work'];
const AC_PEOPLE = ['meera', 'arun', 'dev'];   // the personas the embedded file has
const AC_CSS = '<style>.side,.topbar{display:none!important}.shell{display:block!important;min-height:0!important}#view{min-height:100vh!important}</style>';
const acWin = () => { const f = document.getElementById('acframe'); return f && f.contentWindow && f.dataset.ready === '1' ? f.contentWindow : null; };
const acRun = code => { const w = acWin(); if (!w) return undefined; try { return w.eval(code); } catch (e) { console.error(e); return undefined; } };
function acDoc(){
  const h = new TextDecoder().decode(Uint8Array.from(atob(AC_SRC), c => c.charCodeAt(0)));
  return `<script>try { localStorage.setItem('bmp.user', ${JSON.stringify(JSON.stringify(S.user))}); } catch (e) {}<\/script>` + AC_CSS + h;
}
/* its breadcrumbs show in the portal's top bar; a click runs the same breadcrumb inside the page */
function acCrumbs(){
  const w = acWin(); if (!w || !AC_VIEWS.includes(S.route.v)) return;
  const src = w.document.getElementById('crumbs'); if (!src) return;
  const box = $('#crumbs'); box.innerHTML = src.innerHTML;
  box.querySelectorAll('button').forEach((b, i) => { b.dataset.act = 'ac-crumb'; b.dataset.i = i; delete b.dataset.r; });
  const v = acRun('S.route.v'), nv = v === 'work' ? 'work' : 'accounts';
  if (S.route.v !== nv){ S.route = {v:nv}; renderNav(); }
}
ACT['ac-crumb'] = t => { const w = acWin(); const b = w && w.document.querySelectorAll('#crumbs button')[+t.dataset.i]; if (b) b.click(); };
function acSync(){   // persona, theme and route of the embedded page follow the portal
  if (acRun('S.user') !== S.user) acRun(`S.user = ${JSON.stringify(S.user)}; store.set('user', S.user); S.accFilter = null; S.f.sel.clear(); render();`);
  const th = document.documentElement.dataset.theme, d = acWin().document.documentElement;
  if (th) d.dataset.theme = th; else delete d.dataset.theme;
}
function acShow(params){
  const f = document.getElementById('acframe');
  $('#view').innerHTML = ''; $('#view').style.display = 'none'; f.hidden = false; f.style.display = 'block';
  const goIn = () => { acSync(); if (params) acRun(`go(${JSON.stringify(S.route.v)}, ${JSON.stringify(params)})`); acCrumbs(); };
  if (!f.dataset.started){ f.dataset.started = '1';
    f.addEventListener('load', () => { f.dataset.ready = '1';
      new MutationObserver(acCrumbs).observe(f.contentDocument.getElementById('crumbs'), {childList:true, subtree:true, characterData:true});
      goIn(); renderNav(); });
    f.srcdoc = acDoc(); return; }
  if (f.dataset.ready === '1') goIn();
}
function acHide(){ const f = document.getElementById('acframe'); if (f){ f.hidden = true; f.style.display = 'none'; } $('#view').style.display = ''; }
const acCount = () => { const n = acRun('myWork().length'); return n || null; };
