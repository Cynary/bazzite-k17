#!/usr/bin/env python3
"""Driver transport test using a recorded neutral native report, not an emulation of firmware replies."""
import sys,json,subprocess,selectors,time
raw=bytes.fromhex(json.loads(open(sys.argv[1]).readline())['report'])
assert len(raw)==54 and raw[0]==0x42
err=open(sys.argv[2]+'.stderr','w');trace=open(sys.argv[2]+'.requests','w')
b=subprocess.Popen(['ssh','shed','C:/Users/rodri/controller-forwarding/steam-native/broker.exe'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,bufsize=0)
p=None
try:
 time.sleep(.5)
 p=subprocess.Popen(['ssh','shed','C:/Users/rodri/controller-forwarding/steam-native/probe.exe'],stdout=subprocess.PIPE,stderr=err)
 s=selectors.DefaultSelector();s.register(b.stdout,selectors.EVENT_READ);buf=b'';end=time.monotonic()+6
 while time.monotonic()<end:
  b.stdin.write(b'I '+raw.hex().encode()+b'\n')
  for key,_ in s.select(.004):
   data=b.stdout.read(65536)
   if not data:raise RuntimeError('broker exited')
   buf+=data
   while b'\n' in buf:
    line,buf=buf.split(b'\n',1);trace.write(line.decode()+'\n');parts=line.split()
    # Deliberately fail firmware requests: this tests only raw HID delivery.
    if parts[0]==b'Q':b.stdin.write(b'R '+parts[1]+b' -1 -\n')
 out=p.communicate(timeout=5)[0].decode();print(out)
 h=14695981039346656037
 for x in raw*20:h=((h^x)*1099511628211)&((1<<64)-1)
 print('expected fnv=%016x'%h)
 if p.returncode or 'fnv=%016x'%h not in out:raise RuntimeError('raw input mismatch')
finally:
 b.stdin.write(b'X\n');b.stdin.close();b.wait(timeout=10)
 if p and p.poll() is None:p.kill();p.wait()
 err.close();trace.close()
