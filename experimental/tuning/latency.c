#define _GNU_SOURCE
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
static int64_t ns(clockid_t c){struct timespec t;clock_gettime(c,&t);return (int64_t)t.tv_sec*1000000000+t.tv_nsec;}
static int cmp(const void*a,const void*b){double x=*(double*)a,y=*(double*)b;return (x>y)-(x<y);}
int main(){double wake[1800],finish[1800];int misses=0;int64_t next=ns(CLOCK_MONOTONIC)+100000000;for(int i=0;i<1800;i++){struct timespec t={next/1000000000,next%1000000000};clock_nanosleep(CLOCK_MONOTONIC,TIMER_ABSTIME,&t,0);wake[i]=(ns(CLOCK_MONOTONIC)-next)/1e6;int64_t cpu=ns(CLOCK_THREAD_CPUTIME_ID);while(ns(CLOCK_THREAD_CPUTIME_ID)-cpu<1000000){for(volatile int j=0;j<100;j++); } finish[i]=(ns(CLOCK_MONOTONIC)-next)/1e6;if(finish[i]>8.333333)misses++;next+=8333333;}qsort(wake,1800,sizeof(double),cmp);qsort(finish,1800,sizeof(double),cmp);printf("{\"wake_p99_ms\":%.3f,\"finish_p95_ms\":%.3f,\"finish_p99_ms\":%.3f,\"finish_max_ms\":%.3f,\"misses\":%d,\"samples\":1800}\n",wake[1782],finish[1710],finish[1782],finish[1799],misses);}
