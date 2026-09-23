// SPDX-License-Identifier: MIT
using System;
namespace Moonmachine.ControllerTest {
public static class Tests {
    static int checks;
    static void Check(bool v,string why){checks++;if(!v)throw new Exception(why);}
    static void Put(byte[] b,int at,int value){b[at]=(byte)value;b[at+1]=(byte)(value>>8);}
    static byte[] Report(uint bits){var b=new byte[54];b[0]=0x42;for(int i=0;i<4;i++)b[2+i]=(byte)(bits>>(i*8));Put(b,46,32767);return b;}
    public static int Run(){try{
        for(int bit=0;bit<32;bit++){var s=State.Decode(Report(1u<<bit));for(int other=0;other<32;other++)Check(s.Down(other)==(bit==other),"button isolation");}
        var raw=Report(0);Put(raw,6,16384);Put(raw,8,8000);Put(raw,10,-32768);Put(raw,12,32767);Put(raw,18,-12345);Put(raw,20,23456);Put(raw,22,40000);Put(raw,24,-9000);Put(raw,28,2500);Put(raw,34,-16384);Put(raw,40,16384);
        var p=State.Decode(raw);Check(p.Triggers[0]==16384&&p.Triggers[1]==8000,"trigger offsets");Check(p.Sticks[0]==-32768&&p.Sticks[1]==32767,"signed sticks");Check(p.Pads[0]==-12345&&p.Pads[1]==23456&&p.Pads[2]==-9000,"pad offsets");Check(p.Pressure[0]==40000&&p.Pressure[1]==2500,"unsigned pressure");Check(p.Accel[0]==-16384&&p.Gyro[0]==16384,"motion offsets");Check(p.Quaternion[0]==32767,"quaternion W first");
        for(int len=0;len<54;len++){var b=new byte[len];if(len>0)b[0]=0x42;Check(State.Decode(b)==null,"truncated report");}
        var shortReport=new byte[54];shortReport[0]=0x45;Check(State.Decode(shortReport)!=null&&!State.Decode(shortReport).HasQuaternion,"padded report45");shortReport[53]=1;Check(State.Decode(shortReport)==null,"nonzero padding");
        var t=new Tracker();t.Open("test");t.Add(Report(0));var guide=new Guide();guide.Start(t);guide.Tick(t);t.Add(Report(1));t.Add(Report(0));guide.Tick(t);Check(guide.Steps[0].Result=="passed","short press survives UI polling");Check(guide.Index==1,"one step advances");
        guide.Start(t);t.Add(Report(1));guide.Tick(t);t.Add(Report(0));guide.Tick(t);Check(guide.Index==0,"initial held button is not a fresh press");t.Add(Report(1));guide.Tick(t);t.Add(Report(0));guide.Tick(t);Check(guide.Index==1,"fresh press and release");
        guide.Next(t,"skipped","test");Check(guide.Steps[1].Result=="skipped","skip not pass");
        guide.Start(t);guide.Tick(t);t.Add(Report(1));guide.Tick(t);t.Disconnect("test");t.Open("reconnect");t.Add(Report(0));guide.Tick(t);Check(guide.Index==0,"disconnect cannot finish step");
        var q=Rotation.Unit(State.Decode(Report(0)));var v=Rotation.Apply(q,1,2,3);Check(Math.Abs(v[0]-1)<1e-9&&Math.Abs(v[2]-3)<1e-9,"identity rotation");v=Rotation.Apply(new[]{Math.Sqrt(.5),0.0,0.0,Math.Sqrt(.5)},1,0,0);Check(Math.Abs(v[0])<1e-9&&Math.Abs(v[1]-1)<1e-9,"90deg rotation");
        var rng=new Random(42);for(int i=0;i<10000;i++){var b=new byte[rng.Next(0,100)];rng.NextBytes(b);State.Decode(b);}checks+=10000;
        Console.WriteLine("PASS: "+checks+" decoder, guide and orientation checks");return 0;
    }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
}
