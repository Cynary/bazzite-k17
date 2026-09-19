import subprocess,time,pathlib,json
pre=pathlib.Path('/sys/kernel/debug/sched/preempt')
epps=list(pathlib.Path('/sys/devices/system/cpu/cpufreq').glob('policy*/energy_performance_preference'))
original={p:p.read_text().strip() for p in epps}
hw=next(p for p in pathlib.Path('/sys/class/hwmon').glob('hwmon*') if (p/'name').read_text().strip()=='coretemp')
configs=['default','full','lavd','bpfland','epp-performance']
sched=None;load=None
try:
 for round,order in enumerate([configs,list(reversed(configs))]):
  for conf in order:
   pre.write_text('full' if conf=='full' else 'lazy')
   for p,v in original.items():p.write_text('performance' if conf=='epp-performance' else v)
   if conf in ['lavd','bpfland']:
    sched=subprocess.Popen(['/usr/bin/scx_'+conf],stdout=open('/tmp/k17-scx-'+conf+'.log','a'),stderr=subprocess.STDOUT)
    time.sleep(2)
    if sched.poll() is not None: raise RuntimeError('Scheduler failed '+conf)
   load=subprocess.Popen(['stress-ng','--cpu','8','--cpu-method','matrixprod','--timeout','25s'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   time.sleep(2)
   test=subprocess.Popen(['/tmp/k17-latency'],stdout=subprocess.PIPE,text=True)
   temps=[]
   energy=pathlib.Path('/sys/class/powercap/intel-rapl:0/energy_uj')
   erange=int(pathlib.Path('/sys/class/powercap/intel-rapl:0/max_energy_range_uj').read_text())
   e0=int(energy.read_text());t0=time.monotonic()
   while test.poll() is None:
    temp=int((hw/'temp1_input').read_text())/1000;temps.append(temp)
    if temp>=95:test.terminate();raise RuntimeError('Temperature limit')
    time.sleep(.5)
   out=test.communicate()[0]
   if test.returncode:raise RuntimeError('benchmark failed')
   print(json.dumps(dict(round=round,config=conf,result=json.loads(out),max_temp=max(temps),avg_watts=((int(energy.read_text())-e0)%erange)/1e6/(time.monotonic()-t0),preempt=pre.read_text().strip(),epp=epps[0].read_text().strip(),scx=pathlib.Path("/sys/kernel/sched_ext/state").read_text().strip())),flush=True)
   load.terminate();load.wait();load=None
   if sched:sched.terminate();sched.wait(timeout=10);sched=None
finally:
 if load:load.terminate();load.wait()
 if sched:sched.terminate();sched.wait(timeout=10)
 pre.write_text('lazy')
 for p,v in original.items():p.write_text(v)
