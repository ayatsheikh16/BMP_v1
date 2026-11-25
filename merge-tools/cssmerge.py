import re, os
from css import blocks

SHELL_TOK = re.compile(r'(?<![\w-])(\.shell|\.side|\.side-brand|\.side-nav|\.side-foot|\.navitem|\.navgroup|\.usermenu|\.usercard|\.userwrap|\.uinfo|\.topbar|\.crumbs|\.gsearch|\.gresults|\.navtoggle|#bell|\.toasts|\.toast|\.actingbar|\.sb-sw|\.brandtx|\.logo|#acting|\.dotn|\.t-ic|\.t-msg|\.t-x)(?![\w-])')
BODYSHELL = re.compile(r'^(html|body)?\[data-(nav|side|focus)')
def is_shell_sel(s):
    s=s.strip()
    return bool(SHELL_TOK.search(s)) or bool(re.match(r'^body\[data-(nav|side|focus)',s))
def is_shell_rule(sel):
    parts=[p for p in split_sel(sel)]
    return all(is_shell_sel(p) for p in parts)
def split_sel(sel):
    out=[];depth=0;cur=''
    for ch in sel:
        if ch in '([': depth+=1
        elif ch in ')]': depth-=1
        if ch==',' and depth==0: out.append(cur);cur=''
        else: cur+=ch
    out.append(cur)
    return [x.strip() for x in out if x.strip()]
TOKEN_SEL = re.compile(r'^(:root(\[data-theme="?(dark|light)"?\])?|:root:not\(\[data-theme="?light"?\]\))$')
def is_token_rule(sel): return all(TOKEN_SEL.match(p) for p in split_sel(sel))
def scope_sel(s, src):
    w=f':where(html[data-src="{src}"])' if src!='nb' else ':where(html:not([data-src="b"]))'
    att=f'[data-src="{src}"]' if src!='nb' else ':not([data-src="b"])'
    if s.startswith(':root'): return ':root:where('+att+')'+s[5:]
    if re.match(r'^html(?![\w-])',s): return 'html:where('+att+')'+s[4:]
    return w+' '+s
def scope(sel, src): return ','.join(scope_sel(p,src) for p in split_sel(sel))
def inner_rules(body):
    # parse inner of @media into rules
    import tempfile,os
    return blocks_from_text(body)
def blocks_from_text(s):
    out=[];i=0;n=len(s)
    while i<n:
        m=re.match(r'\s+',s[i:])
        if m: i+=m.end(); continue
        if s.startswith('/*',i): j=s.index('*/',i)+2; i=j; continue
        j=s.index('{',i); sel=s[i:j].strip(); depth=0;k=j
        while True:
            c=s[k]
            if c=='{': depth+=1
            elif c=='}':
                depth-=1
                if depth==0: break
            k+=1
        out.append((sel,s[j+1:k].strip())); i=k+1
    return out
def emit(sel,body): return f'{sel}{{{body}}}'
def merge(a_path,b_path,log):
    A=[(x[1],x[2]) for x in blocks(a_path) if x[0]=='rule']
    B=[(x[1],x[2]) for x in blocks(b_path) if x[0]=='rule']
    aset=set(A); bset=set(B)
    out=['/* ===== merged stylesheet: tokens and shared rules, then file-1 screens (Catalogs, Plans, Accounts…), then file-2 screens (Home, Approval configuration). Shell = file 2. ===== */']
    def handle(rules, other_set, src, keep_identical, shell_mode):
        res=[]
        for sel,body in rules:
            if sel.startswith('@media') or sel.startswith('@supports') or sel.startswith('@container'):
                inner=blocks_from_text(body); acc=[]
                for isel,ibody in inner:
                    if is_token_rule(isel): acc.append(emit(isel,ibody)); continue
                    shell=is_shell_rule(isel)
                    ident=(sel,body) in other_set
                    if shell:
                        if shell_mode=='keep': acc.append(emit(isel,ibody))
                        continue
                    if ident and not keep_identical: continue
                    acc.append(emit(isel,ibody) if ident else emit(scope(isel,src),ibody))
                if acc: res.append(sel+'{\n  '+'\n  '.join(acc)+'\n}')
                continue
            if sel.startswith('@'):  # keyframes, font-face, etc.
                if (sel,body) in other_set and not keep_identical: continue
                res.append(emit(sel,body)); continue
            if is_token_rule(sel): res.append(emit(sel,body)); continue
            if is_shell_rule(sel):
                if shell_mode=='keep': res.append(emit(sel,body))
                continue
            ident=(sel,body) in other_set
            if ident:
                if keep_identical: res.append(emit(sel,body))
                continue
            res.append(emit(scope(sel,src),body))
        return res
    out.append('/* ---- file 1 (A) rules; rules unique to file 1 apply only outside file-2 screens ---- */')
    out+=handle(A,bset,'nb',True,'drop')
    out.append('/* ---- file 2 (B) rules; shell rules apply everywhere, the rest only on file-2 screens ---- */')
    out+=handle(B,aset,'b',False,'keep')
    return '\n'.join(out)

def merge_text(a_css, b_css, log=None):
    import tempfile
    d = tempfile.mkdtemp()
    pa, pb = os.path.join(d, 'a.css'), os.path.join(d, 'b.css')
    open(pa, 'w', encoding='utf-8').write(a_css); open(pb, 'w', encoding='utf-8').write(b_css)
    return merge(pa, pb, log)
