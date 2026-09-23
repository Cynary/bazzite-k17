#!/usr/bin/env python3
"""Finite diagnostic relay. No shell interpolation or unauthenticated listener."""
import subprocess,sys,selectors,time,json,pathlib
seconds=int(sys.argv[1]) if len(sys.argv)>1 else 30
prefix=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else 'relay')
logs=[open(str(prefix)+suffix,'w') for suffix in ('.linux.log','.windows.log','.transactions.jsonl')]
linux=subprocess.Popen(['ssh','k17','sudo python3 /tmp/steam-native-gateway.py /dev/hidraw5'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=logs[0],bufsize=0)
windows=None
try:
 if linux.stdout.readline()!=b'READY\n':raise RuntimeError('physical endpoint unavailable')
 windows=subprocess.Popen(['ssh','shed','C:/Users/rodri/controller-forwarding/steam-native/broker.exe'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=logs[1],bufsize=0)
 sel=selectors.DefaultSelector();sel.register(linux.stdout,selectors.EVENT_READ,windows);sel.register(windows.stdout,selectors.EVENT_READ,linux)
 buffers={linux.stdout:b'',windows.stdout:b''};end=time.monotonic()+seconds;inputs=0;queries=0
 while time.monotonic()<end:
  for key,_ in sel.select(max(0,end-time.monotonic())):
   data=key.fileobj.read(65536)
   if not data:raise RuntimeError('endpoint closed')
   buffers[key.fileobj]+=data
   while b'\n' in buffers[key.fileobj]:
    line,buffers[key.fileobj]=buffers[key.fileobj].split(b'\n',1)
    if line.startswith(b'I '):inputs+=1
    else:
     logs[2].write(json.dumps({'t':time.monotonic(),'line':line.decode()})+'\n');logs[2].flush()
     queries+=line.startswith(b'Q ')
    key.data.stdin.write(line+b'\n')
 print(json.dumps({'inputs':inputs,'queries':queries}))
finally:
 for p in (windows,linux):
  if p:
   try:p.stdin.write(b'X\n');p.stdin.close();p.wait(timeout=10)
   except (BrokenPipeError,subprocess.TimeoutExpired):p.kill();p.wait()
 for f in logs:f.close()
