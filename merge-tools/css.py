import re,sys
def blocks(path):
    s=open(path,encoding='utf-8').read()
    out=[];i=0;n=len(s)
    while i<n:
        # skip ws and comments
        m=re.match(r'\s+',s[i:]); 
        if m: i+=m.end(); continue
        if s.startswith('/*',i):
            j=s.index('*/',i)+2; out.append(('comment',s[i:j],None)); i=j; continue
        j=s.index('{',i); sel=s[i:j].strip()
        depth=0;k=j
        while True:
            c=s[k]
            if c=='{': depth+=1
            elif c=='}':
                depth-=1
                if depth==0: break
            k+=1
        out.append(('rule',sel,s[j+1:k].strip())); i=k+1
    return out
if __name__=='__main__':
    A=blocks('src/a.css');B=blocks('src/b.css')
    ar=[(x[1],x[2]) for x in A if x[0]=='rule']; br=[(x[1],x[2]) for x in B if x[0]=='rule']
    aset=set(ar); asel={}
    for s,b in ar: asel.setdefault(s,[]).append(b)
    same=sum(1 for r in br if r in aset)
    mod=[r for r in br if r not in aset and r[0] in asel]
    new=[r for r in br if r[0] not in asel]
    aonly=[r for r in ar if r[0] not in set(s for s,_ in br)]
    print('A rules',len(ar),'B rules',len(br),'same',same,'B modified',len(mod),'B new',len(new),'A-only selectors',len(aonly))
    for s,b in mod: print('MOD',s[:100],'|',b[:150].replace('\n',' '))
