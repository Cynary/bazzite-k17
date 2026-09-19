import json, pathlib, subprocess, time
bore=pathlib.Path('/proc/sys/kernel/sched_bore')
assert pathlib.Path('/sys/kernel/sched_ext/state').read_text().strip()=='disabled'
original=bore.read_text().strip()
hw=next(p for p in pathlib.Path('/sys/class/hwmon').glob('hwmon*') if (p/'name').read_text().strip()=='coretemp')
load=test=None
try:
 for mode in [0,1,1,0]:
  bore.write_text(str(mode))
  load=subprocess.Popen(['stress-ng','--cpu','8','--cpu-method','matrixprod','--timeout','25s'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  time.sleep(2)
  test=subprocess.Popen(['/tmp/k17-latency'],stdout=subprocess.PIPE,text=True)
  temps=[]
  while test.poll() is None:
   temp=max(int(p.read_text())/1000 for p in hw.glob('temp*_input'));temps.append(temp)
   if temp>=95:raise RuntimeError('Temperature limit')
   time.sleep(.5)
  out=test.communicate()[0]
  if test.returncode:raise RuntimeError('Benchmark failed')
  print(json.dumps(dict(bore=mode,result=json.loads(out),max_temp=max(temps))),flush=True)
  test=None;load.terminate();load.wait();load=None
finally:
 for p in [test,load]:
  if p is not None and p.poll() is None:p.terminate();p.wait()
 bore.write_text(original)
