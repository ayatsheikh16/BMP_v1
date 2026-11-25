"""Merge the two Helo BMP prototypes into one single-file HTML.
usage: python3 -I build.py <fileA.html> <fileB.html> <out.html> <accounts.html>
A = "SKU configuration, catalog configuration, plan configuration and add-on pack configuration"
B = "Dashboard and approval configuration"
"""
import sys, os, re, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from chunks import chunks as _chunks
import cssmerge

a_path, b_path, out_path, ac_path = sys.argv[1:5]   # ac = "BMP account creation review": Accounts and Actions, embedded unchanged
A_HTML = open(a_path, encoding='utf-8').read()
B_HTML = open(b_path, encoding='utf-8').read()

def between(s, start, end, from_=0):
    i = s.index(start, from_) + len(start); j = s.index(end, i); return s[i:j], j

# ---------- split each file ----------
a_css, _ = between(A_HTML, '<style>', '</style>')
b_css, _ = between(B_HTML, '<style>', '</style>')
a_body_i = A_HTML.index('</style>'); b_body_i = B_HTML.index('</style>')
a_js, _ = between(A_HTML, '<script>', '</script>', a_body_i)
# file B: first <script> is the 90% zoom helper, the second is the app
_, j = between(B_HTML, '<script>', '</script>', b_body_i)
b_js, _ = between(B_HTML, '<script>', '</script>', j)
a_js = a_js[1:] if a_js.startswith('\n') else a_js
b_js = b_js[1:] if b_js.startswith('\n') else b_js
b_shell = B_HTML[b_body_i + len('</style>'):B_HTML.index('<script>', b_body_i)].strip()

def chunks_of(text):
    p = os.path.join(HERE, '_tmp.js'); open(p, 'w', encoding='utf-8').write(text)
    try: return _chunks(p)
    finally: os.remove(p)

def must_replace(s, old, new, count=1, what=''):
    n = s.count(old)
    if n != count: raise SystemExit(f'patch "{what or old[:60]}": expected {count} match(es), found {n}')
    return s.replace(old, new)

# ---------- A: text-level patches before chunking ----------
a_js = re.sub(r'\bczDrag\b', 'czDragA', a_js)
TAIL = "trialDocApi.resume();\nentApi.restore();\nif (!PEOPLE[S.user]) S.user = 'meera';\nrender();"
assert a_js.count(TAIL) == 1, 'A boot tail'
a_js = a_js.replace(TAIL, '')   # A's boot tail moves to the very end, after file 2's code          # A's home-customise drag state; B has a czDrag() function
A = chunks_of(a_js); B = chunks_of(b_js)
Akey = {}; [Akey.setdefault(c['key'], c) for c in A]
Bkey = {}; [Bkey.setdefault(c['key'], c) for c in B]
def setA(key, text): Akey[key]['text'] = text
def patchA(key, old, new, count=1): Akey[key]['text'] = must_replace(Akey[key]['text'], old, new, count, key + ': ' + old[:50])

# people and teams from B (the dashboard's sales-team data needs them); everything else from A
for k in ['decl:PEOPLE', 'decl:PERSONA_ORDER', 'decl:TEAM_OF', 'decl:REPS', 'decl:TGT_PEOPLE', 'decl:PUB_SHORT', 'decl:toast', 'decl:openMenu']:
    setA(k, Bkey[k]['text'])
# Arun Mehta (Sales Manager) can create everything: catalogs, SKUs, plans and add-on packs (SKU Maker) and approval rules
patchA('decl:PEOPLE', "role:'Sales Manager', type:'sm',  perms:[],           mgr:'meera', title:'Sales Manager · West'", "role:'Sales Manager', type:'sm',  perms:['SKU Maker','Approval rules'], mgr:'meera', title:'Sales Manager · West'")
patchA('decl:can', "  admin:         () => meRaw().perms.includes('BMP Admin') || T() === 'md',", "  admin:         () => meRaw().perms.includes('BMP Admin') || T() === 'md',\n  apprRules:     () => can.admin() || meRaw().perms.includes('Approval rules'),   // create and publish approval rules")
# account owners from B (only the owner column differs)
mask = lambda t: re.sub(r"^(\s*\['[^']*','[A-Z]{2}',)'[^']*'", r"\1'_'", t, flags=re.M)
assert mask(Akey['decl:ACC_SEED']['text']) == mask(Bkey['decl:ACC_SEED']['text']), 'ACC_SEED differs beyond owners'
setA('decl:ACC_SEED', Bkey['decl:ACC_SEED']['text'])
# icons: A's set plus the ones only B has
a_ic = set(re.findall(r"^\s+([\w$]+)\s*:", Akey['decl:IP']['text'], re.M))
extra = [l.rstrip().rstrip(',') for l in Bkey['decl:IP']['text'].split('\n')[1:] if re.match(r"^\s+([\w$]+)\s*:", l) and re.match(r"^\s+([\w$]+)", l).group(1) not in a_ic]
Akey['decl:IP']['text'] += '\nObject.assign(IP, {\n' + ',\n'.join(extra) + '\n});'
patchA('decl:S', "route: {v:'skus'}", "route: {v:'home2'}")
patchA('decl:trialLog', "to:t.to || null, ext:null})));", "to:t.to || null, ext:t.ext || null, req:t.req || null, h2:!!t.h2})));")
patchA('decl:trialLog', "by:w.trial.by, ext:w.trial.ext || null, running:true}));", "by:w.trial.by, ext:w.trial.ext || null, req:w.trial.req || null, running:true}));")
# shell
patchA('decl:renderNav', "I('menu', 18)", "I('sidebar', 20)")
patchA('decl:renderUserMenu', 'PERSONA_ORDER.map', 'PERSONA_SWITCH.map')
SHELL_JS = open(os.path.join(HERE, 'shell.js'), encoding='utf-8').read()
for k in ['decl:navItems', 'decl:NAV_PARENT', 'decl:go', 'decl:KEEP_VIEWS']: Akey[k]['text'] = ''
setA('decl:render', SHELL_JS)
nav_a = [c for c in A if c['key'].startswith("stmt:$('#navtoggle').addEventListener")]
nav_b = [c for c in B if c['key'].startswith("stmt:$('#navtoggle').addEventListener")]
assert len(nav_a) == 1 and len(nav_b) == 1; nav_a[0]['text'] = nav_b[0]['text']
# visibility: an approver the rule picked can open what they're asked to approve
patchA('decl:canSee', 'function canSee(a){', 'function canSee0(a){')
Akey['decl:canSee']['text'] += "\nfunction canSee(a){ return canSee0(a) || (!!a && !isTM() && S.deals.some(d => d.aid === a.id && d.apr && d.apr.levels.some(l => l.names.includes(me().name)))); }"
patchA('decl:canSeeWs', 'function canSeeWs(w){', 'function canSeeWs0(w){')
Akey['decl:canSeeWs']['text'] += "\nfunction canSeeWs(w){ return canSeeWs0(w) || (!!w && !isTM() && S.deals.some(d => d.wid === w.id && d.apr && d.apr.levels.some(l => l.names.includes(me().name)))); }"

# ---------- approval engine hooks (deals) ----------
setA('decl:routeFor', 'function routeFor(d){ return apDealLive(d).levels.map(l => l.role); }   // roles on the route, from Approval configuration')
patchA('decl:savePlanDeal', """    const route = routeFor(d);
    d.stage = route[0] === 'MD' ? 'Waiting for MD' : 'Waiting for Sales Manager';
    d.submitted = 0;
    d.chain = [{who: isTM() ? 'Kiran for Arun' : maker, role:'Submitted', on:0, state:'ok'}, {who: route[0] === 'MD' ? mdName() : managerOf(maker), role: route[0], state:'now'}];""",
"""    d.submitted = 0;
    d.chain = [{who: isTM() ? 'Kiran for Arun' : maker, role:'Submitted', on:0, state:'ok'}];""")
patchA('decl:savePlanDeal', "    log(resend ? 'Resubmitted deal' : 'Submitted deal for approval', d.id);",
       "    apDealSubmit(d, maker);      // route from Approval configuration › Create deal or plan\n    log(resend ? 'Resubmitted deal' : 'Submitted deal for approval', d.id);")
patchA('decl:dealSteps', "const L = [['Configure', S1], ['Sales Manager OK', S2], ['MD OK', S3], ['Papers & e-sign', S4], ['Publish', S5]];",
       "const L = [['Configure', S1], ...apDealSteps(d), ['Papers & e-sign', S4], ['Publish', S5]];")
patchA('decl:dealNext', "mine = (who === 'md' && can.mdApprove()) || (who === 'sm' && can.firstApprove() && (TEAM_OF[me().key] || []).includes(d.maker));", "mine = apDealMine(d);")
patchA('decl:dealNext', "Sent to you because: ${mdTriggers(d).join('; ') || 'the maker is a Sales Manager'}", "Sent to you because: ${esc(apDealWhyTxt(d))}", 2)
patchA('decl:dealNext', "(mdTriggers(d).length ? 'If you approve, it goes to the MD next.' : 'If you approve, it’s approved. No MD step is needed.')",
       "(d.apr && d.apr.levels[(d.lvl || 0) + 1] ? `If you approve, it goes to ${apNames(d.apr.levels[(d.lvl || 0) + 1])} next.` : d.apr && d.apr.rule ? 'If you approve, it’s approved.' : 'If you approve, it’s approved. No MD step is needed.')")
patchA('decl:dealNext', "t:`Waiting for ${who === 'md' ? mdName() + ' (MD)' : managerOf(d.maker) + ' (Sales Manager)'} · ${plural(since, 'day')}`", "t:`Waiting for ${apDealWaitTxt(d)} · ${plural(since, 'day')}`")
def patch_any(old, new, count=1):
    hits = [c for c in A if old in c['text']]
    if len(hits) != 1 or hits[0]['text'].count(old) != count: raise SystemExit(f'patch_any "{old[:60]}": {len(hits)} chunks')
    hits[0]['text'] = hits[0]['text'].replace(old, new)
patch_any("${next === 'Waiting for MD' ? 'It goes to Meera (MD) next because: ' + esc(mdTriggers(d).join('; ')) + '.' : 'It becomes Approved. The maker then adds the papers and publishes.'}", "${apDealNextTxt(d)}")
patch_any("who = me().name, role = T() === 'md' ? 'MD' : 'Sales Manager';", "who = me().name, role = (apDealCur(d) || {}).role || (T() === 'md' ? 'MD' : 'Sales Manager');")
patch_any("""      d.chain.push({who, role, on:0, state:'ok', note:n});
      if (d.stage === 'Waiting for Sales Manager' && routeFor(d).includes('MD')){ d.stage = 'Waiting for MD'; d.chain.push({who:mdName(), role:'MD', state:'now'}); d.history.unshift({on:D(0), who, what:'Approved at Sales Manager step · sent to MD'}); toast('Approved and sent to the MD.', 'ok'); }
      else { d.stage = 'Approved'; d.history.unshift({on:D(0), who, what:`Approved by ${role}`}); toast('Approved. The maker can now add the papers and publish.', 'ok'); }""",
"""      apDealApprove(d, who, n);   // next level from Approval configuration, or Approved""")
patch_any("const d = deal(x.did); if (d){ const route = routeFor(d); d.stage = route[0] === 'MD' ? 'Waiting for MD' : 'Waiting for Sales Manager'; d.submitted = 0; d.chain = [{who:'Kiran for Arun', role:'Submitted', on:0, state:'ok'}, {who: route[0] === 'MD' ? 'Meera' : 'Arun', role:route[0], state:'now'}]; }",
          "const d = deal(x.did); if (d){ d.submitted = 0; d.chain = [{who:'Kiran for Arun', role:'Submitted', on:0, state:'ok'}]; apDealSubmit(d, d.maker); }")
patch_any("toast(`Submitted to ${d.stage === 'Waiting for MD' ? 'Meera (MD)' : managerOf(d.maker)}. Configuration PDF",
          "toast(`${d.stage === 'Approved' ? 'Approved straight away: the approval rule needs no approval for it.' : 'Submitted to ' + apDealWaitTxt(d) + '.'} Configuration PDF")
patch_any("Goes to ${routeFor(dm).map(r => r === 'MD' ? 'the MD' : managerOf(maker) + ' (Sales Manager)').join(', then ')}.", "Goes to ${esc(apGoesTo(dm))}.")
patch_any("${routeFor(d).join(' → ')}${trig.length ? ' · MD because: ' + esc(trig.join('; ')) : ''}",
          "${esc(apChainTxt(apDeal(d)))}${apDeal(d).rule ? ' · ' + esc(apDeal(d).ruleName) + ': ' + esc(apDeal(d).why) : trig.length ? ' · MD because: ' + esc(trig.join('; ')) : ''}")
# Actions / bell
patchA('decl:myWork', 'function myWork(){', 'function myWork0(){')
Akey['decl:myWork']['text'] += '\nfunction myWork(){ return apExtraWork(myWork0()); }   // plus whatever Approval configuration routed to me'
patchA('decl:myWork', "S.changeReqs.filter(c => c.status === 'Waiting for MD').forEach(", "S.changeReqs.filter(c => c.status === 'Waiting for MD' && apCrMine(c)).forEach(")
patchA('decl:myWork', "pkPending().forEach(add);", "if (apPlanMine()) pkPending().forEach(add);")
# catalogue / SKU change requests
patchA('decl:crCards', "const md = can.mdApprove(), mine = c.maker === meRaw().name;", "const md = apCrMine(c), mine = c.maker === meRaw().name;")
patchA('decl:crCards', "${pill(c.status, ", "${pill(apCrStatus(c), ")
patchA('decl:crCards', '<span class="b4">Waiting for Meera (MD).</span>',
       '<span class="b4">Waiting for ${esc(apCrWaitTxt(c))}${c.apr && c.apr.levels.length > 1 ? ` · level ${(c.lvl || 0) + 1} of ${c.apr.levels.length}` : \'\'}${c.apr && c.apr.rule ? ` · ${esc(c.apr.ruleName)}: ${esc(c.apr.why)}` : \'\'}.</span>')
patch_any("crCards(S.changeReqs.filter(c => c.status === 'Waiting for MD'))", "crCards(S.changeReqs.filter(c => c.status === 'Waiting for MD' && (apCrMine(c) || c.maker === me().name)))")
patchA('ACT:cr-decide', "if (k === 'ok'){\n    c.status = 'Approved'; c.decidedBy = 'Meera'; c.decidedOn = 0;",
       "if (k === 'ok'){\n    if (apCrAdvance(c)) return render();   // more approval levels to go\n    c.status = 'Approved'; c.decidedBy = apCrDecider(); c.decidedOn = 0;\n    if (c.maker !== c.decidedBy) S.notifs.unshift({for:c.maker, to:[], on:0, text:`${c.decidedBy === 'System' ? 'No approval was needed for' : fullOf(c.decidedBy) + ' approved'} ${c.id}: ${c.title}.`, go:{v:'skus'}});")
patchA('ACT:cr-decide-ok', "c.decidedBy = 'Meera';", "c.decidedBy = me().name; S.notifs.unshift({for:c.maker, to:[], on:0, text:`${fullOf(me().name)} ${t.dataset.k === 'back' ? 'sent back' : 'rejected'} ${c.id}: ${n}`, go:{v:'skus'}});")
# SaaS catalogs: a new single SKU can't be created yet; the option stays visible, disabled, with the reason on hover
SAAS_TIP = "Creating a new SKU isn’t available for SaaS catalogs yet. Assign existing SKUs instead."
Akey['decl:cmAddOpts']['text'] = ("const SAAS_NEW_TIP = " + json.dumps(SAAS_TIP) + ";\nconst saasNoNew = c => !!c && c.prod === 'clarity';   // SaaS catalog\n") + Akey['decl:cmAddOpts']['text']
patchA('decl:cmAddOpts', "data-k=\"${esc(c.name)}\" ${why ? `aria-disabled=\"true\" data-tip=\"${esc(why)}\"` : ''}>",
       "data-k=\"${esc(c.name)}\" ${why ? `aria-disabled=\"true\" data-tip=\"${esc(why)}\"` : m === 'single' && saasNoNew(c) ? `aria-disabled=\"true\" data-tip=\"${esc(SAAS_NEW_TIP)}\"` : ''}>")
patch_any("`<button role=\"menuitem\" data-act=\"cat-add\" data-m=\"${m}\" data-k=\"${esc(c.name)}\">${I(ic,18)}",
          "`<button role=\"menuitem\" data-act=\"cat-add\" data-m=\"${m}\" data-k=\"${esc(c.name)}\" ${m === 'single' && saasNoNew(c) ? `aria-disabled=\"true\" data-tip=\"${esc(SAAS_NEW_TIP)}\"` : ''}>${I(ic,18)}")
patch_any("<button class=\"btn btn-pri\" data-act=\"cat-add\" data-m=\"single\" data-k=\"${esc(c.name)}\" ${dz}>New SKU</button>",
          "<button class=\"btn btn-pri\" data-act=\"cat-add\" data-m=\"single\" data-k=\"${esc(c.name)}\" ${dz || (saasNoNew(c) ? `aria-disabled=\"true\" data-tip=\"${esc(SAAS_NEW_TIP)}\"` : '')}>New SKU</button>")
patch_any("<button role=\"menuitem\" data-act=\"cat-add\" data-m=\"single\" data-k=\"${esc(c.name)}\" ${cm.locked ? 'aria-disabled=\"true\" data-tip=\"Product catalogs have a fixed set of SKUs, so new SKUs can’t be added.\"' : ''}>",
          "<button role=\"menuitem\" data-act=\"cat-add\" data-m=\"single\" data-k=\"${esc(c.name)}\" ${cm.locked ? 'aria-disabled=\"true\" data-tip=\"Product catalogs have a fixed set of SKUs, so new SKUs can’t be added.\"' : saasNoNew(cm) || saasNoNew(catByName(c.name)) ? `aria-disabled=\"true\" data-tip=\"${esc(SAAS_NEW_TIP)}\"` : ''}>")
patch_any("const c = catByName(t.dataset.k), m = t.dataset.m; S._catMenu = null; S._skuNew = false; if (!c || !can.sku() || c.locked) return;",
          "const c = catByName(t.dataset.k), m = t.dataset.m; S._catMenu = null; S._skuNew = false; if (!c || !can.sku() || c.locked || (m === 'single' && saasNoNew(c))) return;")

# SaaS catalogs charged On/off list only on/off SKUs in "Select existing SKUs"; Charged by usage lists only usage SKUs; Both lists every one
patchA('decl:bkExPool', "const bkExPool = B => S.skus.filter(s => !s.legacy && s.product === B.prod && s.status === 'Active' && (B.prod !== 'clarity' || B.anyType || (bkFeat(B) ? s.type === 'Feature' : s.type !== 'Feature')));",
       "const bkCharge = s => s.access || (['Consumable','Usage'].includes(s.type) ? 'metered' : s.type === 'Feature' ? 'onoff' : '');   // how a SaaS SKU is charged\nconst bkExPool = B => S.skus.filter(s => !s.legacy && s.product === B.prod && s.status === 'Active' && (B.prod !== 'clarity' || (['onoff','metered','both'].includes(B.access) ? s.type === 'Feature' && (B.access === 'both' ? ['onoff','metered'].includes(bkCharge(s)) : bkCharge(s) === B.access) : B.anyType || (bkFeat(B) ? s.type === 'Feature' : s.type !== 'Feature'))));   // SaaS catalogs: features charged the catalog's way (Both = on/off and usage)")
patch_any("if (m === 'existing' && c.prod === 'clarity') Object.assign(B, {type:'MTP', anyType:true});",
          "if (m === 'existing' && c.prod === 'clarity') Object.assign(B, {type:'MTP', anyType:true, access:c.access || ''});")

# a tax category belongs to one country: the New category dialog's country list has no "Global (all countries)"
patchA('decl:ctyOpts', "const ctyOpts = (cur, flagAttr = true) =>", "const ctyOpts = (cur, flagAttr = true, global = true) =>")
patchA('decl:ctyOpts', "<optgroup label=\"Frequently used\"><option value=\"GL\" ${flagAttr ? 'data-flag=\"GL\"' : ''} ${cur === 'GL' ? 'selected' : ''}>Global (all countries)</option>",
       "<optgroup label=\"Frequently used\">${global ? `<option value=\"GL\" ${flagAttr ? 'data-flag=\"GL\"' : ''} ${cur === 'GL' ? 'selected' : ''}>Global (all countries)</option>` : ''}")
patch_any('id="bkc-cty" data-chg="bkc" data-k="cty">${ctyOpts(D.cty)}</select>', 'id="bkc-cty" data-chg="bkc" data-k="cty">${ctyOpts(D.cty, true, false)}</select>')

# a Global SKU (or SaaS feature) is priced in US dollars
patchA('decl:nsCur', "const nsCur = cty => cty === 'GL' ? 'INR' :", "const nsCur = cty => cty === 'GL' ? 'USD' :")

# SaaS on/off features (user's list, Nov 2026): every one configured On/off for India, so they're what an On/off SaaS catalog can pick
ONOFF_FEATS = [('Data and segments', ['Data ingestion (SDK and pixel)', 'Data ingestion (CRM)', 'Data ingestion (Files)', 'Data ingestion (APIs)',
    'Segment Builder + Re-targeting (Portfolio)', 'Segment Builder + Re-targeting (Projects)', 'Funnel analytics + Re-targeting',
    'Event Analytics (Mixpanel/Amplitude Grade) + Re-targeting', 'CQL — Clarity Query Language', 'Journeys (Sankey)', 'SCV (Basic + Events)', 'SCV (Advanced)']),
  ('Campaigns and workflows', ['Campaign scheduling + failover', 'Workflow Builder', 'AI Optimiser (WHEN + WHERE)', 'Workflow - AB Test Node', 'Workflow - API Node',
    'Campaigns - AB Test', 'Campaigns - Single Channel', 'Campaigns - MCO', 'Campaigns via Files', 'Campaigns via Segments']),
  ('Links and QR codes', ['QR Code Customisation', 'Smart Redirections (conditional landing)', 'Shortlinks & QR Codes']),
  ('Content and analytics', ['Content Studio', 'Analyse - Dashboard', 'Analyse - Reports'])]
FEAT_KEYS = {   # short keys, like the designer's ('sso', 'custom-domains'): the SKU code is FT-<KEY>-<COUNTRY>
  'Data ingestion (SDK and pixel)':'ingest-sdk', 'Data ingestion (CRM)':'ingest-crm', 'Data ingestion (Files)':'ingest-files', 'Data ingestion (APIs)':'ingest-api',
  'Segment Builder + Re-targeting (Portfolio)':'segment-portfolio', 'Segment Builder + Re-targeting (Projects)':'segment-projects', 'Funnel analytics + Re-targeting':'funnel',
  'Event Analytics (Mixpanel/Amplitude Grade) + Re-targeting':'event-analytics', 'CQL — Clarity Query Language':'cql', 'Journeys (Sankey)':'journeys',
  'SCV (Basic + Events)':'scv-basic', 'SCV (Advanced)':'scv-advanced', 'Campaign scheduling + failover':'campaign-schedule', 'Workflow Builder':'workflow-builder',
  'AI Optimiser (WHEN + WHERE)':'ai-optimiser', 'Workflow - AB Test Node':'workflow-ab', 'Workflow - API Node':'workflow-api', 'Campaigns - AB Test':'campaign-ab',
  'Campaigns - Single Channel':'campaign-single', 'Campaigns - MCO':'campaign-mco', 'Campaigns via Files':'campaign-files', 'Campaigns via Segments':'campaign-segments',
  'QR Code Customisation':'qr-custom', 'Smart Redirections (conditional landing)':'smart-redirect', 'Shortlinks & QR Codes':'shortlinks',
  'Content Studio':'content-studio', 'Analyse - Dashboard':'analyse-dashboard', 'Analyse - Reports':'analyse-reports'}
def _fkey(n): return FEAT_KEYS[n]
_rows = ',\n'.join(f"  [{json.dumps(_fkey(n))}, {json.dumps(n)}, {json.dumps('On/off feature · ' + g)}, [['IN', 'onoff', 0, '', 'Monthly', 'Active']]]" for g, L in ONOFF_FEATS for n in L)
patchA('decl:FT_SEED', "  ['sso', 'Single sign-on', 'SAML and OIDC sign-in for workspaces.', [['IN', 'onoff', 2500, '', 'Monthly', 'Active']]],\n", _rows + ',\n')
patchA('decl:FT_SEED', "  ['custom-domains', 'Custom domains', 'Branded short links on the customer’s own domain.', [['IN', 'onoff', 1500, '', 'Monthly', 'Active']]],\n", '')
assert len(set(_fkey(n) for g, L in ONOFF_FEATS for n in L)) == 28

# SaaS charged-by-usage features = the Core features of Plans › Modify plan (Helo Clarity): its usage rates and seats,
# priced at the catalogue base rates, so they're what a "Charged by usage" SaaS catalog can pick
USAGE_FEATS = [('mtp', 'Monthly Tracked Profiles', 'profile', 0.12), ('executions', 'Executions', 'execution', 0.015),
  ('ai-tokens', 'AI Tokens', '1K tokens', 0.4), ('workflows', 'Workflows', 'workflow', 1500), ('seats', 'Seats', 'seat', 2500)]
_urows = ''.join(f"  [{json.dumps(k)}, {json.dumps(n)}, 'Charged by usage · Core feature in Plans', [['IN', 'metered', {p}, {json.dumps(u)}, 'Monthly', 'Active']]],\n" for k, n, u, p in USAGE_FEATS)
patchA('decl:FT_SEED', "  ['api-access', 'API access', 'Programmatic access to messaging and reporting.', [['IN', 'metered', 0.05, 'api_call', 'Monthly', 'Active']]],\n", _urows)
patchA('decl:FT_UNITS', "['1K tokens','Per 1K tokens']];", "['1K tokens','Per 1K tokens'], ['workflow','Per workflow']];")   # Workflows is charged per workflow in Plans

# New SKU: Message type is mandatory for messaging SKUs (no "(Optional)", same error as Channel)
patch_any("<label for=\"ns-traffic\">Message type${OPT}</label>${sel('traffic', 'traffic', (NS_MTYPES[N.chan] || []).map(x => [x, x]), N.chan ? 'Select message type' : 'Select channel first', N.chan ? '' : 'disabled')}</div>",
          "<label for=\"ns-traffic\">Message type</label>${sel('traffic', 'traffic', (NS_MTYPES[N.chan] || []).map(x => [x, x]), N.chan ? 'Select message type' : 'Select channel first', N.chan ? '' : 'disabled')}${err('traffic')}</div>")
patch_any("if (msg && !N.chan) E.chan = 'Choose the channel.';", "if (msg && !N.chan) E.chan = 'Choose the channel.'; if (msg && !N.traffic) E.traffic = N.chan ? 'Choose the message type.' : 'Choose the channel first.';")

# New category goes for approval: the CTA says "Submit for approval", the category waits as "Pending approval" and becomes
# active when its change request is approved (routed by Approval configuration › Create catalogue; MD by default)
patch_any('<button class="btn btn-pri" data-act="bkc-save">Create category</button>', '<button class="btn btn-pri" data-act="bkc-save">Submit for approval</button>')
patch_any('Assigned automatically when you create the category.', 'Assigned automatically when you submit the category.')
patch_any("bkCats().push({name:nm, base, cty:D.cty, ccode:D.ccode, codeType:D.codeType, code:D.code, custom:true}); log('Created category', D.ccode, '', `${nm} · ${D.codeType} ${D.code}`);",
          "const crId = 'CR-0' + (Math.max(150, ...S.changeReqs.map(r => +String(r.id).replace(/\\D/g, '') || 0)) + 1);\n"
          "    bkCats().push({name:nm, base, cty:D.cty, ccode:D.ccode, codeType:D.codeType, code:D.code, custom:true, pending:crId});\n"
          "    S.changeReqs.unshift({id:crId, title:`New category · ${nm}`, urgent:false, lines:[{code:'—', field:'New category', old:'—', next:`${nm} · ${D.codeType} ${D.code}`, eff:'On approval', _f:'newcat', _cat:nm}], reason:`New tax category for ${D.cty} · ${D.codeType} ${D.code}`, attach:'', maker:meRaw().name, on:0, status:'Waiting for MD', impact:{review:0, below:0, live:0, plans:0, revenue:'—'}});\n"
          "    log('Submitted category for approval', crId, '', `${nm} · ${D.codeType} ${D.code}`);")
patch_any("if (page){ S.bkCatD = null; S._catFor = null; closeOverlay(); toast(`${nm} created · ${D.codeType} ${D.code}.`, 'ok'); return render(); }",
          "if (page){ S.bkCatD = null; S._catFor = null; closeOverlay(); toast(`${nm} sent for approval · ${D.codeType} ${D.code}.`, 'ok'); return render(); }")
patch_any("toast(`${nm} created · ${D.codeType} ${D.code}.`, 'ok'); bkCatDone(); }", "toast(`${nm} sent for approval · ${D.codeType} ${D.code}.`, 'ok'); bkCatDone(); }")
# approved → active; rejected or sent back → withdrawn
patchA('ACT:cr-decide', "    c.lines.forEach(l => { if (l._f === 'catrename'){", "    c.lines.forEach(l => { if (l._f === 'newcat'){ const k = bkCats().find(x => x.name === l._cat); if (k) delete k.pending; return; } if (l._f === 'catrename'){")
patchA('ACT:cr-decide-ok', "c.decidedBy = me().name;", "c.decidedBy = me().name; c.lines.forEach(l => { if (l._f === 'newcat') S.bkCats = bkCats().filter(x => x.name !== l._cat || x.pending !== c.id); });")
# Categories and tax: a waiting category shows the designer's Pending approval status and can't be edited yet
patch_any('<td class="ctl-cat1"><div class="sk2-n">${esc(c.base || c.name)}</div>',
          '<td class="ctl-cat1"><div class="sk2-n">${esc(c.base || c.name)}${c.pending ? ` <span class="sk2-st t-warn"><i></i>Pending approval</span>` : \'\'}</div>')
patch_any('${mk ? `<button class="btn btn-sec sm" data-act="cat-tax" data-i="${i}">Edit tax code</button>` : \'\'}',
          '${mk ? `<button class="btn btn-sec sm" data-act="cat-tax" data-i="${i}" ${c.pending ? `aria-disabled="true" data-tip="Waiting for approval in ${esc(c.pending)}."` : \'\'}>Edit tax code</button>` : \'\'}')

patch_any("'cat-tax': t => { const c = bkCats()[+t.dataset.i]; if (!c) return;", "'cat-tax': t => { if (t.getAttribute && t.getAttribute('aria-disabled') === 'true') return; const c = bkCats()[+t.dataset.i]; if (!c) return;")

# SaaS features page: a configured feature's action reads "Edit" (was "Add country")
patch_any('data-act="ft-cfg" data-k="${esc(x.key)}">Add country</button>', 'data-act="ft-cfg" data-k="${esc(x.key)}">Edit</button>')

# Default product catalogs (Data & Intelligence, Communicate, Touchpoints, Services): existing SKUs can be assigned;
# New SKU and Bulk upload stay disabled with the designer's lock tooltip
LOCK_TIP = "Product catalogs have a fixed set of SKUs, so new SKUs can’t be added."
patch_any("c.archived ? 'This catalog is archived. Restore it to add SKUs.' : c.locked ? lockTip : '';",
          "c.archived ? 'This catalog is archived. Restore it to add SKUs.' : '';   // a product catalog only takes existing SKUs (set per option)")
patch_any('`<button role="menuitem" data-act="cat-add" data-m="${m}" data-k="${esc(c.name)}" ${m === \'single\' && saasNoNew(c) ?',
          '`<button role="menuitem" data-act="cat-add" data-m="${m}" data-k="${esc(c.name)}" ${c.locked && m !== \'existing\' ? `aria-disabled="true" data-tip="${esc(lockTip)}"` : m === \'single\' && saasNoNew(c) ?')
patchA('decl:cmAddOpts', ": m === 'single' && saasNoNew(c) ?", ": c.locked && m !== 'existing' ? `aria-disabled=\"true\" data-tip=\"" + LOCK_TIP + "\"` : m === 'single' && saasNoNew(c) ?")
patch_any("${dz || (saasNoNew(c) ?", "${dz || (c.locked ? `aria-disabled=\"true\" data-tip=\"${esc(lockTip)}\"` : saasNoNew(c) ?")
patch_any('data-m="file" data-k="${esc(c.name)}" ${dz}>upload a CSV', 'data-m="file" data-k="${esc(c.name)}" ${dz || (c.locked ? `aria-disabled="true" data-tip="${esc(lockTip)}"` : \'\')}>upload a CSV')
patch_any('data-act="cat-add" data-m="existing" data-k="${esc(c.name)}" ${cm.locked ? \'aria-disabled="true" data-tip="Product catalogs have a fixed set of SKUs, so new SKUs can’t be added."\' : \'\'}>',
          'data-act="cat-add" data-m="existing" data-k="${esc(c.name)}">')
patch_any("if (!c || !can.sku() || c.locked || (m === 'single' && saasNoNew(c))) return;", "if (!c || !can.sku() || (c.locked && m !== 'existing') || (m === 'single' && saasNoNew(c))) return;")

# A new SKU waiting for approval can be revised: the change updates its open request (no second request), the SKU stays
# Pending approval and the approver is told
patchA('decl:skuRevBlock', "if (s.status !== 'Active') return", "if (s.status !== 'Active' && s.status !== 'Pending approval') return")
patch_any("s.status === 'Active' ? `<button class=\"btn btn-pri\" data-act=\"sku-rev\"", "['Active','Pending approval'].includes(s.status) ? `<button class=\"btn btn-pri\" data-act=\"sku-rev\"")
patchA('ACT:sku-rev', "  const dup = S.changeReqs.find(c => c.status === 'Waiting for MD' && c.lines.some(l => l.code === s.code));",
       "  const pnew = skuPendingCr(s), dup = !pnew && S.changeReqs.find(c => c.status === 'Waiting for MD' && c.lines.some(l => l.code === s.code));")
patchA('ACT:sku-rev', "${dup ? note('warn', `${dup.id} for this SKU is already waiting for the MD. Wait for it before revising again.`) : ''}",
       "${dup ? note('warn', `${dup.id} for this SKU is already waiting for the MD. Wait for it before revising again.`) : pnew ? note('info', `This SKU is waiting for approval in ${pnew.id}. Your changes update that request.`) : ''}")
patchA('ACT:sku-rev', "<div class=\"b4\">A new rate becomes v${skuVer(s) + 1} once approved. Live deals keep their rates.</div>",
       "<div class=\"b4\">${pnew ? 'The new rate replaces the one waiting for approval.' : `A new rate becomes v${skuVer(s) + 1} once approved. Live deals keep their rates.`}</div>")
patchA('ACT:sku-rev-ok', "  if (bad) return;\n", r"""  if (bad) return;
  const pc = skuPendingCr(s);
  if (pc){ const old = s.name;
    L.forEach(l => { if (l._f === 'name') s.name = l.next; if (l._f === 'rate') s.base = l._v; if (l._f === 'desc') s.desc = l.next === '—' ? '' : l.next; });
    pc.lines.forEach(l => { if (l.code === s.code && l.field === 'New SKU' && s.type !== 'Feature') l.next = `${rate(s.base, s.cur)} per ${s.unit}`; });
    if (old !== s.name) pc.title = pc.title.split(old).join(s.name);
    (pc.revs = pc.revs || []).push({by:meRaw().name, on:0, what:L.map(l => l.field).join(', '), reason:r});
    const cur = typeof apCrCur === 'function' ? apCrCur(pc) : null;
    (cur ? cur.names : [mdName()]).forEach(n => S.notifs.unshift({for:n, to:[], on:0, text:`${fullOf(meRaw().name)} revised ${s.code} in ${pc.id} (${L.map(l => l.field.toLowerCase()).join(', ')}). It still needs your approval.`, go:{v:'work', tab:'approvals', grp:'SKU approval'}}));
    log('Revised SKU waiting for approval', pc.id, s.code, L.map(l => l.field).join(', '));
    S._skr = null; closeOverlay(); toast(`${s.code} updated in ${pc.id}. It’s still waiting for approval.`, 'ok'); return render(); }
""")
Akey['decl:skuRevBlock']['text'] += "\nconst skuPendingCr = s => s && s.status === 'Pending approval' ? S.changeReqs.find(c => c.status === 'Waiting for MD' && c.lines.some(l => l.code === s.code && l.field === 'New SKU')) : null;   // the request a new SKU is waiting in"

# Catalogs side list: archived catalogs are kept in their own "Archived" list below the active ones (collapsed; it opens
# by itself while an archived catalog is being viewed)
patchA('decl:cmNav', "const L = cmShown(), item = c =>", "const all = cmShown(), L = all.filter(c => !c.archived), AR = all.filter(c => c.archived), item = c =>")
patchA('decl:cmNav', "${c.archived ? ' <span class=\"ctl-mut\">(archived)</span>' : ''}", "")
patchA('decl:cmNav', '<div class="b4 ctl-none" hidden>No catalogs match.</div>',
       '<div class="b4 ctl-none" hidden>No catalogs match.</div>'
       '${AR.length ? (open => `<div class="ctl-sep" role="separator"></div><a href="#" class="ctl-item ctl-wide" data-act="cm-arch" aria-expanded="${open}"><span class="ctl-name">Archived</span><span class="ctl-n num">${AR.length}</span></a>'
       '${open ? `<div class="ctl-list ctl-arch" aria-label="Archived catalogs">${AR.map(item).join(\'\')}</div>` : \'\'}`)(!!S._cmArch || AR.some(c => active === \'cat:\' + c.name)) : \'\'}')
Akey['decl:cmNav']['text'] += "\nACT['cm-arch'] = () => { S._cmArch = !S._cmArch; render(); };"

# plans and add-on packs (embedded page): the approver comes from Approval configuration › Revise plan
patchA('decl:pkDoc', "(T() === 'md')", "apPlanMine()")
patchA('decl:pkFrame', "if (!can.sku() && T() !== 'md') return noAccess(label);", "if (!can.sku() && T() !== 'md' && !apPlanMine()) return noAccess(label);")
# account creation journey · setup summary: approval status of the plan
patch_any("""        planSt = ['Sent back', 'Approved'].includes(od.stage) ? 'action' : 'pending';
        planSub = esc(od.stage);""",
"""        planSt = ['Sent back', 'Approved'].includes(od.stage) || (od.stage === 'Draft' && (od.chain || []).some(c => c.state === 'bad')) ? 'action' : apDealWaiting(od) ? 'review' : 'pending';
        planSub = apDealSub(od);""")

# BOOT tail of A moves to the very end
# ---------- B: the sections file 2 adds (Home 2 dashboard, approval configuration and helpers) ----------
TAKE = ['HOME · customisable dashboard','SALES TEAM PERFORMANCE widget','USAGE widgets','TRIALS widget','DASHBOARD PERIOD','ADD WIDGET','ADMIN PANEL · APPROVAL MANAGEMENT','APPROVAL MANAGEMENT 2','APPROVAL MANAGEMENT 3','VERSIONS 1B AND 2B','1B ·','4 · Hybrid','2B ·','HOME 2','1 · ','2 · ','REVENUE ·','PAYMENTS ·','TRIALS ·','WORKSPACE PIPELINE ·','3 · ','4 · ','5 · ','ACCOUNTS · Account','SALES TEAM ·','USAGE ·','ACTION CENTRE','SALES REP PERFORMANCE','EDIT DASHBOARD','CUSTOMISE','LEGENDS','USAGE —','TICK-BOX','NOV 21','APPROVAL CONFIGURATION']
BL = b_js.split('\n')
SECS = [(i + 1, BL[i].strip()) for i in range(1, len(BL)) if re.match(r'^\s*/\* =+', BL[i - 1])]
def b_section(line):
    s = ''
    for l, n in SECS:
        if l <= line: s = n
    return s
def taken(c):
    s = b_section(c['line'])
    return any(s.startswith(t) for t in TAKE)
a_texts = set(c['text'] for c in chunks_of(a_js))
B_ADD = []
for c in B:
    if not taken(c): continue
    if c['text'] in a_texts: continue
    if c['key'] == 'stmt:Object.assign(ACT, {' and "'range-apply'" in c['text'] and "'accf-clear'" in c['text']: continue   # same handlers A already has
    B_ADD.append(c['text'])

B_JS = '\n'.join(B_ADD)
for old, new, n in [
    ("who:d.stage === 'Waiting for MD' ? 'MD · Meera Iyer' : 'Sales Manager · Arun Mehta'", "who:apWhoTag(d)", 1),
    ("(d.stage === 'Waiting for MD' ? mine : team).push(x)", "(apDealMine(d) ? mine : team).push(x)", 1),
    ("S.deals.filter(d => d.stage === 'Waiting for MD' && d.submitted <= eo", "S.deals.filter(d => apDealMine(d) && d.submitted <= eo", 2),
    ("VIEWS.appr6 = function(){\n  if (!can.admin() || isTM())", "VIEWS.appr6 = function(){\n  if (!can.apprRules() || isTM())", 1)]:
    B_JS = must_replace(B_JS, old, new, n)    # the dashboard's approvals follow Approval configuration: waiting on the viewer
import base64
AC_JS = 'const AC_SRC = "' + base64.b64encode(open(ac_path, 'rb').read()).decode() + '";\n' + open(os.path.join(HERE, 'accounts_embed.js'), encoding='utf-8').read()
INTEGRATE = AC_JS + '\n' + open(os.path.join(HERE, 'integrate.js'), encoding='utf-8').read()
js = '\n'.join(c['text'] for c in A if c['text'] != '') + \
     '\n\n/* =====================================================================\n   FROM "DASHBOARD AND APPROVAL CONFIGURATION": Home 2 dashboard, approval configuration and their helpers\n   ===================================================================== */\n' + \
     B_JS + '\n\n' + INTEGRATE + \
     "\n/* =====================================================================\n   BOOT\n   ===================================================================== */\nh2Seed();\ntrialDocApi.resume();\nentApi.restore();\nif (!PERSONA_SWITCH.includes(S.user)) S.user = 'meera';\nrender();\n"

ZOOM_JS = """/* File 2 drew the portal at 90% browser zoom. The merged portal uses one scale for every screen:
   set UI_ZOOM to 0.9 to see everything the way file 2 showed it. File 2's code reads positions through zRect() / zIW() etc. */
(function(){
  const Z = 1; window.UI_ZOOM = Z; if (Z !== 1) document.documentElement.style.zoom = Z;
  document.documentElement.style.setProperty('--zvh', `calc(1vh / ${Z})`); document.documentElement.style.setProperty('--zvw', `calc(1vw / ${Z})`);
  Element.prototype.zRect = function(){ const r = this.getBoundingClientRect(); return new DOMRect(r.x / Z, r.y / Z, r.width / Z, r.height / Z); };
  window.zIW = () => window.innerWidth / Z; window.zIH = () => window.innerHeight / Z; window.zSX = () => window.scrollX / Z; window.zSY = () => window.scrollY / Z;
})();"""

b_shell = must_replace(b_shell, '<main id="view"></main>', '<main id="view"></main>\n    <iframe id="acframe" title="Accounts and Actions" hidden style="width:100%;height:calc(100vh - 60px);border:0;vertical-align:top;background:var(--canvas)"></iframe>')
css = cssmerge.merge_text(a_css, b_css)
css += '\n/* merged: a table\'s hidden label (.sr) stays inside its scroll box, so a wide table never scrolls the whole page */\n.sk2-card > .tblscroll{position:relative}\n'
css += '/* merged: the sticky cell holding an open row menu sits above the next rows, so the menu is never hidden */\ntd:has(> .sk2-mw > .sk2-catm){z-index:31}\n'
css = css.replace('--zvh:calc(1vh / .9);--zvw:calc(1vw / .9)', '--zvh:1vh;--zvw:1vw')
head_a = A_HTML[:A_HTML.index('<style>')]
tail_a = A_HTML[A_HTML.rindex('</script>') + len('</script>'):]
html = head_a + '<style>\n' + css + '\n</style>\n\n' + b_shell + '\n<script>\n' + ZOOM_JS + '\n</script>\n<script>\n' + js + '\n</script>' + tail_a
open(out_path, 'w', encoding='utf-8').write(html)
print('wrote', out_path, f'{len(html)/1e6:.1f} MB', 'B chunks added:', len(B_ADD))
