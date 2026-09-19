import subprocess,time,pathlib,json
root=pathlib.Path('/sys/class/hwmon')
hw=next(p for p in root.glob('hwmon*') if (p/'name').read_text().strip()=='coretemp')
energy=pathlib.Path('/sys/class/powercap/intel-rapl:0/energy_uj')
limit=int(pathlib.Path('/sys/class/powercap/intel-rapl:0/max_energy_range_uj').read_text())
p=subprocess.Popen(['stress-ng','--cpu','8','--cpu-method','matrixprod','--timeout','180s','--metrics-brief'],stdout=open('/tmp/k17-thermal-stress.log','w'),stderr=subprocess.STDOUT)
prev_e=int(energy.read_text());prev_t=time.monotonic()
try:
 while p.poll() is None:
  time.sleep(2); now=time.monotonic();e=int(energy.read_text());temp=int((hw/'temp1_input').read_text())/1000
  freqs=[int(f.read_text())/1000 for f in pathlib.Path('/sys/devices/system/cpu').glob('cpu[0-9]*/cpufreq/scaling_cur_freq')]
  counters={str(f):int(f.read_text()) for f in pathlib.Path('/sys/devices/system/cpu').glob('cpu[0-9]*/thermal_throttle/*throttle_count')}
  print(json.dumps(dict(time=time.time(),temp=temp,watts=((e-prev_e)%limit)/1e6/(now-prev_t),mhz=freqs,throttle=counters)),flush=True)
  prev_e=e;prev_t=now
  if temp>=95: print('STOP: reached 95 C',flush=True);p.terminate();break
finally:
 if p.poll() is None:p.terminate()
 p.wait()
