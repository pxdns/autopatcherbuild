import re,sys
L=open(sys.argv[1] if len(sys.argv)>1 else 'rtc.log',errors='replace').read().split('\n')
out=[]
for i,l in enumerate(L):
    m=re.match(r'^(?:rt/)?(\S+)\.java:(\d+): error: (.*)',l)
    if m:
        det=' '.join(x.strip() for x in L[i+1:i+6] if x.strip().startswith(('symbol','required','found','location','reason')))[:150]
        out.append(f"{m.group(1).replace('net/minecraft/','')}:{m.group(2)} {m.group(3)[:100]} | {det}")
print('\n'.join(sorted(out)))
