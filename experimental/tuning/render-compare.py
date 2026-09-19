import subprocess,pathlib,time,json,os,pwd
test_user=os.environ['TEST_USER']; account=pwd.getpwnam(test_user)
runtime='/run/user/'+str(account.pw_uid); app_id=int(os.environ['VRRTEST_APP_ID'])
home=pathlib.Path(account.pw_dir);main=home/'VRRTest/main.lua';original=main.read_bytes()
result=home/'.var/app/org.love2d.love2d/data/love/freesynctest/k17-timing.json'
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
env=os.environ.copy();env.update(DISPLAY=':0',XDG_RUNTIME_DIR=runtime,DBUS_SESSION_BUS_ADDRESS='unix:path='+runtime+'/bus')
hw=next(p for p in pathlib.Path('/sys/class/hwmon').glob('hwmon*') if (p/'name').read_text().strip()=='coretemp')
try:
 main.write_bytes(original+instrument.encode())
 for conf in ['default','bpfland','bpfland','default']:
  if conf=='bpfland':
   sched=subprocess.Popen(['/usr/bin/scx_bpfland'],stdout=open('/tmp/k17-scx-render.log','a'),stderr=subprocess.STDOUT);time.sleep(2)
   if sched.poll() is not None:raise RuntimeError('scheduler startup')
  result.unlink(missing_ok=True)
  load=subprocess.Popen(['stress-ng','--cpu','8','--cpu-method','matrixprod','--timeout','50s'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  subprocess.run(['runuser','-u',test_user,'--','env','DISPLAY=:0','XDG_RUNTIME_DIR='+runtime,'DBUS_SESSION_BUS_ADDRESS=unix:path='+runtime+'/bus','/usr/bin/steam','steam://rungameid/'+str((app_id<<32)|0x02000000)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
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
 main.write_bytes(original)
 if load:load.terminate();load.wait()
 if sched:sched.terminate();sched.wait(timeout=10)
