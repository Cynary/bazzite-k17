import subprocess,pathlib,time,json,os
home=pathlib.Path('/var/home/rodrigo');main=home/'VRRTest/main.lua';original=main.read_bytes()
result=home/'.var/app/org.love2d.love2d/data/love/freesynctest/k17-timing.json'
bore=pathlib.Path('/proc/sys/kernel/sched_bore');original_bore=bore.read_text().strip()
assert pathlib.Path('/sys/kernel/sched_ext/state').read_text().strip()=='disabled'
sched=None;load=None
instrument='''
local original_update = love.update
local elapsed, samples = 0, {}
love.update = function(dt)
 original_update(dt)
 elapsed = elapsed + dt
 if elapsed > 5 then samples[#samples+1] = dt*1000 end
 if elapsed > 30 then
  table.sort(samples)
  local n = #samples
  local missed=0
  for _,v in ipairs(samples) do if v>16.667 then missed=missed+1 end end
  love.filesystem.write("k17-timing.json",string.format('{"n":%d,"median_ms":%.3f,"p99_ms":%.3f,"max_ms":%.3f,"over_16_667ms":%d}',n,samples[math.floor(n*.5)],samples[math.floor(n*.99)],samples[n],missed))
  love.event.quit()
 end
end
'''
env=os.environ.copy();env.update(DISPLAY=':0',XDG_RUNTIME_DIR='/run/user/1000',DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
hw=next(p for p in pathlib.Path('/sys/class/hwmon').glob('hwmon*') if (p/'name').read_text().strip()=='coretemp')
try:
 main.write_bytes(original+instrument.encode())
 for conf in [0,1,1,0]:
  bore.write_text(str(conf))
  result.unlink(missing_ok=True)
  load=subprocess.Popen(['stress-ng','--cpu','8','--cpu-method','matrixprod','--timeout','50s'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  subprocess.run(['runuser','-u','rodrigo','--','env','DISPLAY=:0','XDG_RUNTIME_DIR=/run/user/1000','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus','/usr/bin/steam','steam://rungameid/'+str((4063733204<<32)|0x02000000)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
  deadline=time.monotonic()+65
  while not result.exists():
   if time.monotonic()>deadline:raise RuntimeError('No render result')
   if int((hw/'temp1_input').read_text())>=95000:raise RuntimeError('Temperature limit')
   time.sleep(1)
  print(json.dumps(dict(config=conf,result=json.loads(result.read_text()))),flush=True)
  load.terminate();load.wait();load=None
  time.sleep(3)
  if sched:sched.terminate();sched.wait(timeout=10);sched=None
finally:
 bore.write_text(original_bore)
 main.write_bytes(original)
 if load:load.terminate();load.wait()
 if sched:sched.terminate();sched.wait(timeout=10)
