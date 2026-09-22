"""Regenerate figures: pip install matplotlib numpy; python docs/latency/plot.py"""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'#fafbfe','axes.facecolor':'#fafbfe','svg.fonttype':'none'})
def load(name):
    rows=list(csv.DictReader((root/'data'/f'{name}.csv').open()))
    return {k:np.array([float(r[k]) for r in rows]) for k in rows[0]}
names=['before-clock-fix','release-yuv444','release-vulkan444','release-rgb444','release-yuv420']
data={n:load(n) for n in names}
summary={n:{'n':len(d['total_ms']),'mean_ms':float(d['total_ms'].mean()),'p99_ms':float(np.sort(d['total_ms'])[int(.99*len(d['total_ms']))]),'max_ms':float(d['total_ms'].max()),'stage_means_ms':{k:float(d[k].mean()) for k in ['decode_wait_ms','prepare_ms','other_ms','submit_to_flip_ms']}} for n,d in data.items()}
(root/'data/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
def save(fig,name):
    fig.savefig(root/'figures'/f'{name}.png',dpi=160)
    fig.savefig(root/'figures'/f'{name}.svg')
    plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(12,5.7))
for name,label,col in [('before-clock-fix','Before clock/readiness fix','#b86633'),('release-yuv444','Published release','#087f8c')]:
    v=data[name]['total_ms']; s=np.sort(v)
    axes[0].hist(v,bins=np.arange(0,16,.25),weights=np.ones(len(v))*100/len(v),histtype='step',lw=2,color=col,label=label)
    axes[1].step(s,100*np.arange(len(s),0,-1)/len(s),where='post',lw=2,color=col)
for ax in axes:
    ax.axvline(1000/120,color='#656c79',ls='--',lw=1)
    ax.set_xlabel('Complete frame received → DRM display (ms)');ax.grid(axis='y',alpha=.2)
axes[0].set(title='Distribution',ylabel='Frames per 0.25 ms bin (%)',xlim=(0,16));axes[0].legend(frameon=False,fontsize=10)
axes[1].set(title='How many frames take longer?',ylabel='Frames exceeding this latency (%)',yscale='log',ylim=(.01,105),xlim=(0,16))
fig.suptitle('Removing the long tail in 4:4:4 streaming',x=.075,ha='left',fontsize=18,fontweight='bold')
fig.subplots_adjust(left=.075,right=.98,top=.82,bottom=.23,wspace=.28)
fig.text(.075,.115,'Before: mean 6.95 ms / p99 13.96 ms. Release: mean 6.08 ms / p99 7.09 ms.',fontsize=11)
fig.text(.075,.06,'K17 · 4K HDR · ~116 FPS · separate streams · first 30 s excluded · dashed line: 120 Hz frame period.',fontsize=9)
fig.text(.075,.025,'Host, network transit, scanout position and TV processing excluded. 8,467 / 8,453 matched frames; no recorded drops.',fontsize=9)
save(fig,'latency-tail')
fig,ax=plt.subplots(figsize=(12,6))
show=['before-clock-fix','release-yuv444','release-vulkan444','release-rgb444','release-yuv420']
labels=['Direct YUV 4:4:4\nbefore clock fix','Direct YUV 4:4:4\nrelease','Vulkan 4:4:4\nrelease','Direct RGB 4:4:4\nrelease','Direct YUV 4:2:0\nshort release sample']
left=np.zeros(len(show))
for key,label,color in [('decode_wait_ms','GPU decode wait','#3579b8'),('prepare_ms','Prepare / colour conversion','#e39b45'),('other_ms','Other receipt + pacing work','#b0b7c8'),('submit_to_flip_ms','Submission → display','#148a84')]:
    vals=np.array([data[n][key].mean() for n in show]);assert all(vals>=0)
    ax.barh(labels,vals,left=left,label=label,color=color,height=.65)
    for i,v in enumerate(vals):
        if v>.65:ax.text(left[i]+v/2,i,f'{v:.2f}',ha='center',va='center',fontsize=10,color='white' if key in ['decode_wait_ms','submit_to_flip_ms'] else '#202530')
    left+=vals
for i,v in enumerate(left):ax.text(v+.12,i,f'{v:.2f} ms',va='center',fontweight='bold')
ax.invert_yaxis();ax.set_xlim(0,11);ax.set_xlabel('Mean client time (ms)');ax.grid(axis='x',alpha=.18);ax.set_axisbelow(True)
ax.axvline(1000/120,color='#656c79',ls='--',lw=1)
fig.suptitle('Where the client spends its time',x=.04,ha='left',fontsize=18,fontweight='bold')
fig.subplots_adjust(left=.21,right=.98,top=.83,bottom=.25)
fig.legend(loc='lower center',bbox_to_anchor=(.52,.085),ncol=2,frameon=False,fontsize=10)
fig.text(.04,.055,'Matched per-frame intervals, not Moonlight’s UI decode statistic. “Other” is the remaining time, including pacing.',fontsize=9)
fig.text(.04,.02,'Separate 4K HDR streams; first 30 s excluded. 4:2:0 has only 967 samples. Excludes host, network transit and TV processing.',fontsize=9)
save(fig,'latency-stages')
fig,ax=plt.subplots(figsize=(10,4.5))
vals=[24.01,14.65,10.80,9.790,8.513]
labels=['Gaming Mode after first timing fixes','KDE comparison','Native HDR scanout + ready wake-up','Normal Steam launch, Low Latency preset','Longer run with CPU/GPU tuning']
ax.barh(labels,vals,color=['#ab6770','#8e91a3','#458bb2','#238e9b','#087f8c']);ax.invert_yaxis()
for i,v in enumerate(vals):ax.text(v+.25,i,f'{v:.2f} ms',va='center')
ax.set_xlim(0,28);ax.set_xlabel('Mean decoder-output → DRM display (ms)');ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
fig.suptitle('Earlier investigation: finding the extra waits',x=.03,ha='left',fontsize=17,fontweight='bold')
fig.subplots_adjust(left=.40,right=.98,top=.80,bottom=.23)
fig.text(.03,.065,'Historical checkpoints, not isolated per-patch speedups. Different runs, settings and sample lengths.',fontsize=9)
fig.text(.03,.025,'This chart starts at CPU decoder output. The release charts start earlier, at complete frame receipt.',fontsize=9)
save(fig,'investigation-checkpoints')

# Schematic ordering only: coordinates do not represent measured milliseconds.
fig,ax=plt.subplots(figsize=(12,5.4))
ax.set_xlim(-.2,10.7);ax.set_ylim(-.85,3.25);ax.axis('off')
colors={'cpu':'#3579b8','gpu':'#148a84','wait':'#e39b45'}
ax.barh(2.2,2.5,left=0,height=.4,color=colors['cpu'])
ax.barh(1.1,5.4,left=.6,height=.4,color=colors['gpu'])
ax.barh(0,2.8,left=3.2,height=.4,color=colors['wait'])
ax.barh(0,3.7,left=6,height=.4,color=colors['gpu'])
ax.text(.12,2.2,'CPU: enqueue → handle',va='center',color='white',fontsize=11)
ax.text(.8,1.1,'GPU: decode continues after the handle is returned',va='center',color='white',fontsize=11)
ax.text(4.6,0,'Worker waits for readiness',ha='center',va='center',fontsize=10)
ax.text(7.85,0,'Export → pace → present',ha='center',va='center',color='white',fontsize=11)
for x,label in [(2.5,'Decode statistic ends\n(pixels may not be ready)'),(6,'GPU completion observed\n(pixels can be consumed)')]:
    ax.plot([x,x],[-.3,2.65],ls='--',color='#626b7c',lw=1)
    ax.text(x,2.8,label,ha='center',va='bottom',fontsize=11)
ax.annotate('',xy=(10.2,-.55),xytext=(0,-.55),arrowprops={'arrowstyle':'->','color':'#626b7c'})
ax.text(5,-.8,'Time →   schematic only, not to scale',ha='center',fontsize=10,color='#626b7c')
fig.suptitle('The decode statistic stops before the GPU necessarily does',x=.04,ha='left',fontsize=17,fontweight='bold')
fig.subplots_adjust(left=.04,right=.98,top=.78,bottom=.19)
fig.text(.04,.07,'A frame handle identifies a GPU surface. It does not certify that decoding into that surface has finished.',fontsize=11)
fig.text(.04,.025,'Our worker synchronizes before using the pixels. Other pipelines can enforce the dependency without blocking the CPU.',fontsize=10)
save(fig,'async-decode')
