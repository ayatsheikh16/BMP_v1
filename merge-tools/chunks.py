import re,sys,json
def chunks(path):
    L=open(path,encoding='utf-8').read().split('\n')
    out=[];cur=None
    start=re.compile(r'^(async function|function|const|let|var|Object\.assign|VIEWS\.|VIEWS\[|ACT\.|ACT\[|CHG\[|CHG\.|INP\[|INP\.|MENUS\.|MENUS\[|document\.|\$\(|\(|window\.|[A-Za-z_$][\w$]*\s*\(|[A-Za-z_$][\w$.\[\]\'"]*\s*=|if|for|try|\{)')
    for i,l in enumerate(L):
        if l and not l[0].isspace() and start.match(l) and not l.startswith('}'):
            cur={'line':i+1,'lines':[l]};out.append(cur)
        elif cur is None:
            cur={'line':i+1,'lines':[l]};out.append(cur)
        else: cur['lines'].append(l)
    for c in out:
        h=c['lines'][0]
        m=re.match(r'^(?:async )?function ([\w$]+)|^(?:const|let|var) ([\w$]+)',h)
        if m: c['key']='decl:'+(m.group(1) or m.group(2))
        else:
            m=re.match(r'^(VIEWS|ACT|CHG|INP|MENUS)(?:\.([\w$]+)|\[\s*[\'"]([^\'"]+)[\'"]\s*\])\s*=',h)
            c['key']=('%s:%s'%(m.group(1),m.group(2) or m.group(3))) if m else 'stmt:'+h[:80]
        c['text']='\n'.join(c['lines']).rstrip()
    return out
if __name__=='__main__':
    for c in chunks(sys.argv[1]): print(c['line'],c['key'])
