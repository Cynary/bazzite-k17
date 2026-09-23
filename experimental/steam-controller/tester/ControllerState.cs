// SPDX-License-Identifier: MIT
using System;
using System.Collections.Generic;

namespace Moonmachine.ControllerTest {
public sealed class State {
    // Valve's Triton definitions, as published in SDL 3.4.16.
    public static readonly string[] Buttons = {
        "A", "B", "X", "Y", "Quick Access", "R3", "Menu", "R4", "R5", "RB",
        "D-pad Down", "D-pad Right", "D-pad Left", "D-pad Up", "View", "L3",
        "Steam", "L4", "L5", "LB", "Right stick touch", "Right pad touch",
        "Right pad click", "Right trigger click", "Left stick touch", "Left pad touch",
        "Left pad click", "Left trigger click", "Right grip touch", "Left grip touch",
        "Unknown bit 30", "Unknown bit 31"
    };
    public byte ReportId, Sequence;
    public uint ButtonsMask, ImuTime;
    public int[] Triggers = new int[2], Sticks = new int[4], Pads = new int[4], Pressure = new int[2];
    public int[] Accel = new int[3], Gyro = new int[3], Quaternion = new int[4];
    public bool HasQuaternion;
    public byte[] Raw;
    public bool Down(int bit) { return (ButtonsMask & (1u << bit)) != 0; }
    static int U16(byte[] b,int o) { return b[o] | b[o+1]<<8; }
    static int I16(byte[] b,int o) { return unchecked((short)U16(b,o)); }
    static uint U32(byte[] b,int o) { return (uint)(U16(b,o) | U16(b,o+2)<<16); }
    public static State Decode(byte[] b) {
        if(b==null || b.Length<46 || b.Length>64 || (b[0]!=0x42 && b[0]!=0x45)) return null;
        int expected=b[0]==0x42?54:46;if(b.Length<expected)return null;
        for(int i=expected;i<b.Length;i++)if(b[i]!=0)return null;
        var s=new State {ReportId=b[0],Sequence=b[1],ButtonsMask=U32(b,2),ImuTime=U32(b,30),Raw=(byte[])b.Clone()};
        for(int i=0;i<2;i++) { s.Triggers[i]=I16(b,6+i*2); s.Pressure[i]=U16(b,22+i*6); }
        for(int i=0;i<4;i++) s.Sticks[i]=I16(b,10+i*2);
        s.Pads[0]=I16(b,18);s.Pads[1]=I16(b,20);s.Pads[2]=I16(b,24);s.Pads[3]=I16(b,26);
        for(int i=0;i<3;i++){s.Accel[i]=I16(b,34+i*2);s.Gyro[i]=I16(b,40+i*2);}
        s.HasQuaternion=b[0]==0x42;
        if(s.HasQuaternion)for(int i=0;i<4;i++)s.Quaternion[i]=I16(b,46+i*2);
        return s;
    }
}
public sealed class Tracker {
    public readonly object Sync=new object();
    public State Latest;
    public long Reports, Invalid, Other, Discontinuities;
    public int Generation;
    public DateTime LastReport=DateTime.MinValue;
    public readonly long[] Presses=new long[32], Releases=new long[32];
    public readonly int[] Min=new int[18], Max=new int[18];
    bool ranges;
    public string Device="Waiting for the Windows Steam Controller HID device";
    public bool Connected;
    public void Disconnect(string reason) {lock(Sync){Connected=false;Latest=null;Device=reason;}}
    public void Open(string label) {lock(Sync){Generation++;Connected=true;Latest=null;Device=label;}}
    public void Add(byte[] raw) {
        lock(Sync) {
            var s=State.Decode(raw);
            if(s==null){if(raw.Length>0&&(raw[0]==0x43||raw[0]==0x44||raw[0]==0x79||raw[0]==0x7b))Other++;else Invalid++;return;}
            if(Latest!=null && unchecked((byte)(Latest.Sequence+1))!=s.Sequence)Discontinuities++;
            uint old=Latest==null?0:Latest.ButtonsMask;
            for(int i=0;i<32;i++){uint bit=1u<<i;if((old&bit)==0 && (s.ButtonsMask&bit)!=0)Presses[i]++;if((old&bit)!=0&&(s.ButtonsMask&bit)==0)Releases[i]++;}
            int[] v=Values(s);
            for(int i=0;i<v.Length;i++){if(!ranges){Min[i]=Max[i]=v[i];}else {Min[i]=Math.Min(Min[i],v[i]);Max[i]=Math.Max(Max[i],v[i]);}}
            ranges=true;Latest=s;Reports++;LastReport=DateTime.UtcNow;
        }
    }
    public static int[] Values(State s) {
        return new[]{s.Triggers[0],s.Triggers[1],s.Sticks[0],s.Sticks[1],s.Sticks[2],s.Sticks[3],s.Pads[0],s.Pads[1],s.Pads[2],s.Pads[3],s.Pressure[0],s.Pressure[1],s.Accel[0],s.Accel[1],s.Accel[2],s.Gyro[0],s.Gyro[1],s.Gyro[2]};
    }
}
public sealed class Step {
    public string Name, Instruction, Result="pending", Evidence="";
    public int Bit=-1, Axis=-1;
    public string Kind="button";
    public Step(string name,string instruction) {Name=name;Instruction=instruction;}
}
public sealed class Guide {
    public List<Step> Steps=new List<Step>();
    public int Index=-1;
    int generation;
    long startPress, yes, no, confirm;
    bool neutral, pressed;
    int minimum=int.MaxValue,maximum=int.MinValue;
    double[] startQ;
    public bool Ready;
    public string Hint="";
    public Guide() {
        int[] order={0,1,2,3,10,11,12,13,19,9,6,14,4,16,15,5,17,18,7,8,27,23,24,20,25,21,26,22,29,28};
        foreach(int bit in order) Steps.Add(new Step(State.Buttons[bit],"Release, then activate "+State.Buttons[bit]+" and release again."){Bit=bit});
        string[] axes={"Left trigger","Right trigger","Left stick X","Left stick Y","Right stick X","Right stick Y","Left pad X","Left pad Y","Right pad X","Right pad Y","Left pad pressure","Right pad pressure"};
        for(int i=0;i<axes.Length;i++)Steps.Add(new Step(axes[i],i<2?"Fully squeeze and release the trigger.":i<10?"Sweep the axis to both extremes.":"Touch lightly, then press the pad firmly and release."){Kind="axis",Axis=i});
        string[] rot={"Gyro X","Gyro Y","Gyro Z"};
        for(int i=0;i<3;i++)Steps.Add(new Step(rot[i],"Rotate the controller in both directions around this axis. Watch the raw gyro values."){Kind="axis",Axis=15+i});
        for(int i=0;i<3;i++)Steps.Add(new Step("Accelerometer "+"XYZ"[i],"Slowly tilt until gravity points both ways along this sensor axis."){Kind="axis",Axis=12+i});
        Steps.Add(new Step("Orientation","Tilt and rotate the controller; the 3D model should follow. Press Menu (or Enter) after checking its direction."){Kind="orientation"});
        Steps.Add(new Step("Left haptic","A left pulse will play. Press A if felt, or B if not. H repeats."){Kind="haptic-left"});
        Steps.Add(new Step("Right haptic","A right pulse will play. Press A if felt, or B if not. J repeats."){Kind="haptic-right"});
    }
    public Step Current {get{return Index>=0&&Index<Steps.Count?Steps[Index]:null;}}
    public void Start(Tracker t){foreach(var s in Steps){s.Result="pending";s.Evidence="";}Index=0;Arm(t);}
    public void Arm(Tracker t){lock(t.Sync){generation=t.Generation;neutral=false;pressed=false;Ready=false;Hint="";minimum=int.MaxValue;maximum=int.MinValue;startQ=null;yes=t.Presses[0];no=t.Presses[1];confirm=t.Presses[6];startPress=Current!=null&&Current.Bit>=0?t.Presses[Current.Bit]:0;}}
    public void Next(Tracker t,string result,string evidence){if(Current==null)return;Current.Result=result;Current.Evidence=evidence;Index++;Arm(t);}
    public void Tick(Tracker t){
        lock(t.Sync){var c=Current;var s=t.Latest;if(c==null||s==null||!t.Connected||(DateTime.UtcNow-t.LastReport).TotalSeconds>.5)return;
            if(generation!=t.Generation){Arm(t);Hint="Reconnected: repeat this step.";return;}
            if(c.Bit>=0){if(!neutral){if(!s.Down(c.Bit)){neutral=true;startPress=t.Presses[c.Bit];}return;}
                if(t.Presses[c.Bit]>startPress)pressed=true;
                if(pressed&&!s.Down(c.Bit))Next(t,"passed","Observed fresh press and release in Windows HID reports.");
            }else if(c.Kind=="axis"){
                int v=Tracker.Values(s)[c.Axis];minimum=Math.Min(minimum,v);maximum=Math.Max(maximum,v);
                if(c.Axis<2)Ready=minimum<1500&&maximum>26000;
                else if(c.Axis<10)Ready=minimum< -18000&&maximum>18000;
                else if(c.Axis<12)Ready=minimum<1000&&maximum>2500;
                else if(c.Axis<15)Ready=minimum< -5000&&maximum>5000;
                else Ready=minimum< -400&&maximum>400;
                Hint="Observed range "+minimum+" to "+maximum;
                if(Ready)Next(t,"passed",Hint);
            }else if(c.Kind=="orientation"){
                var q=Rotation.Unit(s);if(q==null){Hint="No valid quaternion in this report.";return;}
                if(startQ==null)startQ=q;
                double dot=0;for(int i=0;i<4;i++)dot+=q[i]*startQ[i];double angle=2*Math.Acos(Math.Min(1,Math.Abs(dot)))*180/Math.PI;
                if(angle>25)Ready=true;Hint=Ready?"Motion observed. Menu / Enter confirms visual direction; S skips.":"Rotate at least 25 degrees from the starting pose.";
                if(Ready&&t.Presses[6]>confirm)Next(t,"confirmed","Quaternion changed >25 degrees; user confirmed visual orientation.");
            }else if(c.Kind.StartsWith("haptic")&&Ready){if(t.Presses[0]>yes)Next(t,"confirmed","User felt haptic after a successful Windows HID write.");else if(t.Presses[1]>no)Next(t,"failed","User did not feel haptic.");}
        }
    }
    public void Confirm(Tracker t){if(Current!=null&&Current.Kind=="orientation"&&Ready)Next(t,"confirmed","Quaternion changed >25 degrees; user confirmed visual orientation.");}
    public void HapticSent(Tracker t,int side,bool ok){lock(t.Sync){if(Current!=null&&Current.Kind==(side==0?"haptic-left":"haptic-right")){Ready=ok;yes=t.Presses[0];no=t.Presses[1];Hint=ok?"Press A if felt; B if not.":"HID write failed. This step has not passed.";}}}
}
public static class Rotation {
    public static double[] Unit(State s){if(s==null||!s.HasQuaternion)return null;double n=0;foreach(int v in s.Quaternion)n+=(double)v*v;if(n<100)return null;n=Math.Sqrt(n);var q=new double[4];for(int i=0;i<4;i++)q[i]=s.Quaternion[i]/n;return q;}
    public static double[] Multiply(double[] a,double[] b){return new[]{a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3],a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2],a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1],a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0]};}
    public static double[] Apply(double[] q,double x,double y,double z){var r=Multiply(Multiply(q,new[]{0.0,x,y,z}),new[]{q[0],-q[1],-q[2],-q[3]});return new[]{r[1],r[2],r[3]};}
}
}
