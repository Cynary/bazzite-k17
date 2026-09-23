"""Compile the actual changed callbacks with mocked OS calls; no hardware effects."""
from pathlib import Path
import subprocess, sys
root=Path(sys.argv[1])
def function(path, signature):
 s=path.read_text(); start=s.index(signature); pos=s.index('{',start); depth=1;i=pos+1
 while depth:
  depth += (s[i]=='{')-(s[i]=='}'); i+=1
 return s[start:i]
common='''#include <linux/input.h>
#include <stdint.h>
#include <assert.h>
#include <errno.h>
#include <string.h>
#include <stdio.h>
#include <stdbool.h>
#include <limits.h>
'''
xone=common+'''
typedef uint16_t u16; typedef uint32_t u32;
#define U16_MAX UINT16_MAX
#define GIP_GP_RUMBLE_MAX 100
#define GIP_GP_RUMBLE_DELAY 10
#define spin_lock_irqsave(lock,flags) ((void)(lock),(flags)=0)
#define spin_unlock_irqrestore(lock,flags) ((void)(lock),(void)(flags))
static unsigned long jiffies;
struct gip_gamepad_rumble { unsigned long lock,last; int timer;
 struct { uint8_t left,right,left_trigger,right_trigger; } pkt; };
struct input_dev { struct gip_gamepad_rumble *rumble; };
static void *input_get_drvdata(struct input_dev *d) {return d->rumble;}
static int timer_pending(int *t){return *t;}
static void mod_timer(int *t,unsigned long until){(void)until;*t=1;}
'''+function(root/'xone/driver/gamepad.c','static int gip_gamepad_queue_rumble')+'''
int main(void) {
 struct gip_gamepad_rumble r={0};struct input_dev d={&r};struct ff_effect e={0};
 e.type=FF_RUMBLE;e.u.rumble.strong_magnitude=65535;e.u.rumble.weak_magnitude=32768;
 gip_gamepad_queue_rumble(&d,NULL,&e);assert(r.pkt.left==100 && r.pkt.right==50);
 e.type=FF_TRIGGER_RUMBLE;e.u.trigger_rumble.left_magnitude=16384;e.u.trigger_rumble.right_magnitude=65535;
 gip_gamepad_queue_rumble(&d,NULL,&e);assert(r.pkt.left==100 && r.pkt.right==50 && r.pkt.left_trigger==25 && r.pkt.right_trigger==100);
 e.u.trigger_rumble.left_magnitude=e.u.trigger_rumble.right_magnitude=0;
 gip_gamepad_queue_rumble(&d,NULL,&e);assert(r.pkt.left==100 && r.pkt.right==50 && !r.pkt.left_trigger && !r.pkt.right_trigger);
 e.u.trigger_rumble.right_magnitude=65535;gip_gamepad_queue_rumble(&d,NULL,&e);
 e.type=FF_RUMBLE;e.u.rumble.strong_magnitude=e.u.rumble.weak_magnitude=0;
 gip_gamepad_queue_rumble(&d,NULL,&e);assert(!r.pkt.left && !r.pkt.right && r.pkt.right_trigger==100);
 e.type=FF_CONSTANT;gip_gamepad_queue_rumble(&d,NULL,&e);assert(r.pkt.right_trigger==100);
 puts("xone: scaling, separate pairs, independent stops and unrelated effect passed");
}
'''
sdl=common+'''
#include <sys/types.h>
typedef uint16_t Uint16;
#define SDL_MAX_RUMBLE_DURATION_MS 65535
#define SDL_AssertJoysticksLocked() ((void)0)
#define SDL_Unsupported() false
#define SDL_SetError(...) false
struct hw {struct ff_effect trigger_effect;bool ff_trigger_rumble;int fd;};
typedef struct {struct hw *hwdata;} SDL_Joystick;
static int calls,fail_once,fail_errno,short_write;static struct input_event last;
static int mock_ioctl(int fd,unsigned long request,struct ff_effect *e) {
 (void)fd;assert(request==EVIOCSFF);calls++;
 if(fail_once){fail_once=0;errno=fail_errno;return -1;}if(e->id==-1)e->id=7;return 0;
}
static ssize_t mock_write(int fd,const void *p,size_t n){(void)fd;last=*(const struct input_event*)p;return short_write?0:(ssize_t)n;}
#define ioctl mock_ioctl
#define write mock_write
'''+function(root/'SDL/src/joystick/linux/SDL_sysjoystick.c','static bool LINUX_JoystickRumbleTriggers')+'''
int main(void) {
 struct hw h={.trigger_effect={.id=-1},.ff_trigger_rumble=true,.fd=3};SDL_Joystick j={&h};
 assert(LINUX_JoystickRumbleTriggers(&j,123,456));assert(calls==1 && h.trigger_effect.id==7);
 assert(h.trigger_effect.type==FF_TRIGGER_RUMBLE && h.trigger_effect.u.trigger_rumble.left_magnitude==123 && h.trigger_effect.u.trigger_rumble.right_magnitude==456);
 assert(last.code==7 && last.value==1);assert(LINUX_JoystickRumbleTriggers(&j,0,0));assert(last.value==0);
 calls=0;fail_once=1;fail_errno=EINVAL;assert(LINUX_JoystickRumbleTriggers(&j,1,2));assert(calls==2);
 calls=0;fail_once=1;fail_errno=EACCES;assert(!LINUX_JoystickRumbleTriggers(&j,1,2));assert(calls==1);
 h.trigger_effect.id=-1;calls=0;fail_once=1;fail_errno=ENOSPC;assert(!LINUX_JoystickRumbleTriggers(&j,1,2));assert(calls==1);
 short_write=1;assert(!LINUX_JoystickRumbleTriggers(&j,1,2));short_write=0;
 h.ff_trigger_rumble=false;calls=0;assert(!LINUX_JoystickRumbleTriggers(&j,1,2));assert(calls==0);
 puts("SDL: capability, independent effect, stop, reset recovery and error handling passed");
}
'''
for name,src in [('xone',xone),('sdl',sdl)]:
 p=root/f'test-{name}.c';p.write_text(src)
 subprocess.run(['cc','-Wall','-Wextra','-Wno-unused-parameter','-Wno-unused-variable','-I'+str(root/'uapi'),str(p),'-o',str(root/f'test-{name}')],check=True)
 subprocess.run([str(root/f'test-{name}')],check=True)
