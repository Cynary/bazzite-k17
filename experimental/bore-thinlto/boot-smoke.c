#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <sys/reboot.h>
#include <sys/utsname.h>
#include <time.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
static void bore(int v){FILE*f=fopen("/proc/sys/kernel/sched_bore","w");if(!f){perror("sched_bore");exit(1);}fprintf(f,"%d\n",v);fclose(f);}
int main(void){mkdir("/proc",0755);mkdir("/sys",0755);mount("proc","/proc","proc",0,0);mount("sysfs","/sys","sysfs",0,0);setbuf(stdout,0);struct utsname u;uname(&u);printf("K17_SMOKE_START %s\n",u.release);FILE*f=fopen("/proc/sys/kernel/sched_bore","r");int enabled=-1;if(f){fscanf(f,"%d",&enabled);fclose(f);}if(enabled!=1){printf("K17_SMOKE_FAIL BORE default=%d\n",enabled);reboot(RB_POWER_OFF);return 1;}for(int mode=0;mode<=1;mode++){bore(mode);for(int i=0;i<12;i++){if(!fork()){time_t end=time(0)+8;volatile unsigned long x=1;while(time(0)<end){for(int j=0;j<100000;j++)x=x*1664525+1013904223;if(i%2)usleep(1000);}exit(0);}}int status;for(int i=0;i<12;i++){wait(&status);if(!WIFEXITED(status)||WEXITSTATUS(status)){puts("K17_SMOKE_FAIL worker");reboot(RB_POWER_OFF);return 1;}}printf("K17_SMOKE_MODE %d PASS\n",mode);}puts("K17_SMOKE_PASS");sync();reboot(RB_POWER_OFF);return 0;}
