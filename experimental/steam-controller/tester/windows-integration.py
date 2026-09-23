#!/usr/bin/env python3
"""Exercise the tester's actual Windows HID reader with an explicitly synthetic fixture."""
import subprocess,time,selectors,json,argparse,re
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--host',required=True)
parser.add_argument('--windows-root',required=True,help='Directory containing tester and steam-native; no spaces')
parser.add_argument('--output',type=Path,default=Path('lab-test-results'))
a=parser.parse_args()
if not re.fullmatch(r'[A-Za-z]:/[A-Za-z0-9_./-]+',a.windows_root):parser.error('Use an absolute Windows path with forward slashes and no spaces')
root=a.output;root.mkdir(parents=True,exist_ok=True)
w=a.windows_root.rstrip('/')
raw=bytearray(54);raw[0]=0x42;raw[46:48]=(32767).to_bytes(2,'little');raw[40:42]=(1234).to_bytes(2,'little')
err=open(root/'lab-integration.stderr','w')
b=subprocess.Popen(['ssh',a.host,w+'/steam-native/broker.exe'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,bufsize=0)
p=None
try:
 time.sleep(.5)
 p=subprocess.Popen(['ssh',a.host,w+'/tester/LabTests.exe --capture 5 '+w+'/tester/native-capture.json'],stdout=subprocess.PIPE,stderr=err)
 sel=selectors.DefaultSelector();sel.register(b.stdout,selectors.EVENT_READ);buf=b'';end=time.monotonic()+6
 while time.monotonic()<end:
  b.stdin.write(b'I '+raw.hex().encode()+b'\n')
  for key,_ in sel.select(.004):
   chunk=b.stdout.read(65536)
   if not chunk:raise RuntimeError('broker closed')
   buf+=chunk
   while b'\n' in buf:
    line,buf=buf.split(b'\n',1);q=line.split()
    if q[0]==b'Q':b.stdin.write(b'R '+q[1]+b' -1 -\n')
 print(p.communicate(timeout=10)[0].decode())
 if p.returncode:raise RuntimeError('viewer could not read Windows HID')
 subprocess.run(['scp','-q',a.host+':'+w+'/tester/native-capture.json',str(root/'lab-native-capture.json')],check=True)
 result=json.loads((root/'lab-native-capture.json').read_text(encoding='utf-8-sig'))
 assert bytes.fromhex(result['raw'].replace('-',''))==bytes(raw),result
 assert result['reports']>100 and result['invalid']==0,result
 print('PASS: native Windows viewer received exact fixture bytes, zero invalid reports')
finally:
 if p and p.poll() is None:p.kill();p.wait()
 try:b.stdin.write(b'X\n');b.stdin.close();b.wait(timeout=10)
 except (BrokenPipeError,subprocess.TimeoutExpired):b.kill();b.wait()
 err.close()
