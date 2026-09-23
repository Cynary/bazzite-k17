// SPDX-License-Identifier: MIT
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Windows.Forms;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

namespace Moonmachine.ControllerTest {
public sealed class Tester : Form {
    SteamMotion steamMotion;
    readonly Tracker data=new Tracker();readonly Guide guide=new Guide();NativeHid hid;
    readonly Timer timer=new Timer{Interval=33};
    readonly bool demo;bool hapticBusy;string message="R: guided check    C: centre pose    H / J: left / right haptic    F9: save    F11: fullscreen";
    readonly Font normal=new Font("Segoe UI",13),small=new Font("Segoe UI",10),title=new Font("Segoe UI Semibold",25),heading=new Font("Segoe UI Semibold",16);
    static Color Bg=Color.FromArgb(12,17,26),Card=Color.FromArgb(23,31,43),Ink=Color.FromArgb(234,240,247),Muted=Color.FromArgb(151,168,190),Mint=Color.FromArgb(78,231,185),Amber=Color.FromArgb(255,193,100);
    double[] zero=new[]{1.0,0,0,0};long lastCount;DateTime rateAt=DateTime.UtcNow;double hz;int hapticStep=-1;bool savedComplete;
    public Tester(bool simulation){demo=simulation;Text="Steam Controller Lab";DoubleBuffered=true;AutoScaleMode=AutoScaleMode.None;BackColor=Bg;ClientSize=new Size(1536,960);KeyPreview=true;
        timer.Tick+=(a,b)=>{if(steamMotion!=null)steamMotion.Poll();guide.Tick(data);if(!demo&&guide.Current!=null&&guide.Current.Kind.StartsWith("haptic")&&hapticStep!=guide.Index&&!hapticBusy){hapticStep=guide.Index;Haptic(guide.Current.Kind=="haptic-left"?0:1);}if(!demo&&guide.Index==guide.Steps.Count&&!savedComplete){savedComplete=true;Save();}if((DateTime.UtcNow-rateAt).TotalSeconds>1){lock(data.Sync){hz=(data.Reports-lastCount)/(DateTime.UtcNow-rateAt).TotalSeconds;lastCount=data.Reports;}rateAt=DateTime.UtcNow;}Invalidate();};
        if(demo){data.Open("SIMULATION — synthetic data, not a forwarding test");data.Add(Demo());hz=266;}
        else {if(Environment.GetEnvironmentVariable("CONTROLLER_LAB_STEAM_INPUT")=="1")steamMotion=new SteamMotion();hid=new NativeHid(data);hid.Start();guide.Start(data);}
        timer.Start();KeyDown+=KeysDown;MouseClick+=ClickAt;
        FormClosing+=(a,b)=>{timer.Stop();if(hid!=null)hid.Dispose();if(steamMotion!=null)steamMotion.Dispose();normal.Dispose();small.Dispose();title.Dispose();heading.Dispose();};
    }
    void TextAt(Graphics g,string s,float x,float y,Font f,Color c){using(var b=new SolidBrush(c))g.DrawString(s,f,b,x,y);}
    void Box(Graphics g,float x,float y,float w,float h,Color c){using(var b=new SolidBrush(c))g.FillRectangle(b,x,y,w,h);}
    void Line(Graphics g,float x,float y,float xx,float yy,Color c,float w=1){using(var p=new Pen(c,w))g.DrawLine(p,x,y,xx,yy);}
    void Circle(Graphics g,float x,float y,float r,Color c){using(var b=new SolidBrush(c))g.FillEllipse(b,x-r,y-r,2*r,2*r);}
    bool Down(State s,int i){return s!=null&&s.Down(i);}
    protected override void OnPaint(PaintEventArgs e){base.OnPaint(e);Render(e.Graphics,ClientSize.Width,ClientSize.Height);}
    void Render(Graphics g,int width,int height){g.Clear(Bg);g.SmoothingMode=SmoothingMode.AntiAlias;float scale=Math.Min(width/1536f,height/960f);g.ScaleTransform(scale,scale);
        lock(data.Sync){var s=data.Latest;bool live=data.Connected&&s!=null&&(demo||(DateTime.UtcNow-data.LastReport).TotalSeconds<.5);
            TextAt(g,"Steam Controller Lab",32,22,title,Ink);TextAt(g,"Native controls • Windows receiver",34,68,normal,Muted);
            Box(g,1120,30,380,40,Card);Circle(g,1140,50,5,live?Mint:Amber);TextAt(g,demo?"SIMULATION":live?"Native HID connected":"Waiting for native input",1155,37,normal,live?Mint:Amber);
            TextAt(g,data.Device,34,105,small,Muted);
            Box(g,32,145,930,454,Card);Box(g,986,145,514,454,Card);
            TextAt(g,"CONTROLS",52,159,small,Muted);DrawController(g,s);
            TextAt(g,"ORIENTATION",1006,159,small,Muted);Draw3D(g,s);
            TextAt(g,steamMotion!=null?steamMotion.Status:"C / Centre pose resets the visual reference",1006,501,small,Muted);
            TextAt(g,"Raw HID quaternion W X Y Z",1006,526,small,Muted);TextAt(g,s!=null&&s.HasQuaternion?String.Join("   ",s.Quaternion):"Not present in the current report",1006,547,normal,Ink);
            TextAt(g,"BUTTONS & TOUCH  •  all 32 raw bits",32,617,small,Muted);
            for(int i=0;i<32;i++){int col=i%8,row=i/8;float x=32+col*184,y=643+row*36;bool on=Down(s,i);Box(g,x,y,176,30,on?Mint:Card);TextAt(g,State.Buttons[i],x+7,y+6,small,on?Bg:Muted);}
            TextAt(g,String.Format("{0:0} reports/s   ·   {1:N0} received   ·   {2} invalid   ·   {3} sequence discontinuities",hz,data.Reports,data.Invalid,data.Discontinuities),32,798,small,Muted);
            DrawGuide(g);
            TextAt(g,message,32,930,small,Muted);
            if(!live&&!demo){Box(g,300,297,675,106,Color.FromArgb(240,12,17,26));TextAt(g,"Waiting for Windows HID reports",320,313,heading,Amber);TextAt(g,"Turn on the controller and start the diagnostic relay.",320,350,normal,Ink);}
        }
    }
    void DrawController(Graphics g,State s){
        // Front schematic. Back paddles are shown below the grips.
        PointF[] shape={new PointF(208,247),new PointF(326,218),new PointF(660,218),new PointF(778,247),new PointF(862,459),new PointF(808,514),new PointF(684,444),new PointF(305,444),new PointF(180,514),new PointF(129,459)};
        using(var b=new SolidBrush(Color.FromArgb(39,51,69)))g.FillPolygon(b,shape);
        Pad(g,274,352,s,0);Pad(g,714,352,s,1);
        Stick(g,379,281,s,0);Stick(g,609,281,s,1);
        Button(g,704,225,3,s,"Y");Button(g,753,267,1,s,"B");Button(g,654,267,2,s,"X");Button(g,704,310,0,s,"A");
        Button(g,270,225,13,s,"↑");Button(g,316,267,11,s,"→");Button(g,224,267,12,s,"←");Button(g,270,309,10,s,"↓");
        Button(g,445,270,14,s,"View",24);Button(g,542,270,6,s,"Menu",24);Button(g,494,313,16,s,"Steam",26);Button(g,494,376,4,s,"···",23);
        TextAt(g,"LB",158,194,normal,Down(s,19)?Mint:Muted);TextAt(g,"RB",801,194,normal,Down(s,9)?Mint:Muted);
        Meter(g,355,202,116,s==null?0:s.Triggers[0]/32767.0,"LT",s==null?0:s.Triggers[0]);Meter(g,518,202,116,s==null?0:s.Triggers[1]/32767.0,"RT",s==null?0:s.Triggers[1]);
        Button(g,222,505,17,s,"L4",21);Button(g,278,505,18,s,"L5",21);Button(g,705,505,7,s,"R4",21);Button(g,761,505,8,s,"R5",21);
        TextAt(g,"Left grip touch",149,525,small,Down(s,29)?Mint:Muted);TextAt(g,"Right grip touch",735,525,small,Down(s,28)?Mint:Muted);
        TextAt(g,"Triggers 0…32767  ·  sticks / pads −32768…32767  ·  pressure raw",52,570,small,Muted);
    }
    void Button(Graphics g,float x,float y,int bit,State s,string label,float r=19){Circle(g,x,y,r,Down(s,bit)?Mint:Bg);var size=g.MeasureString(label,small);TextAt(g,label,x-size.Width/2,y-size.Height/2,small,Down(s,bit)?Bg:Ink);}
    void Stick(Graphics g,float x,float y,State s,int side){int touch=side==0?24:20,click=side==0?15:5;Circle(g,x,y,40,Down(s,touch)?Color.FromArgb(61,111,105):Bg);using(var p=new Pen(Down(s,click)?Mint:Muted,2))g.DrawEllipse(p,x-39,y-39,78,78);float xx=s==null?0:s.Sticks[side*2]/32768f,yy=s==null?0:s.Sticks[side*2+1]/32768f;Circle(g,x+xx*25,y-yy*25,12,Ink);TextAt(g,s==null?"0, 0":s.Sticks[side*2]+", "+s.Sticks[side*2+1],x-54,y+44,small,Muted);}
    void Pad(Graphics g,float x,float y,State s,int side){int touch=side==0?25:21,click=side==0?26:22;Box(g,x-53,y-5,106,78,Down(s,click)?Color.FromArgb(61,111,105):Bg);if(Down(s,touch)){float xx=s.Pads[side*2]/32768f,yy=s.Pads[side*2+1]/32768f;Circle(g,x+xx*44,y+34-yy*31,7,Mint);}TextAt(g,s==null?"0, 0":s.Pads[side*2]+", "+s.Pads[side*2+1],x-57,y+79,small,Muted);TextAt(g,"P "+(s==null?0:s.Pressure[side]),x-32,y+96,small,Ink);}
    void Meter(Graphics g,float x,float y,float w,double v,string label,int raw){TextAt(g,label+" "+raw,x,y-25,small,Muted);Box(g,x,y,w,7,Bg);Box(g,x,y,(float)(w*Math.Max(0,Math.Min(1,v))),7,Mint);}
    void Draw3D(Graphics g,State s){var raw=steamMotion!=null?steamMotion.Quaternion:Rotation.Unit(s);var q=raw==null?new[]{1.0,0,0,0}:Rotation.Multiply(zero,raw);
        var saved=g.Save();g.SetClip(new RectangleF(992,213,503,226));ControllerModel.Draw(g,q,s);g.Restore(saved);
        TextAt(g,raw==null?"No valid orientation data":(steamMotion!=null?"Steam Input orientation • 3D model":"Controller quaternion • 3D model"),1006,186,small,raw==null?Amber:Muted);
        TextAt(g,"Gyro °/s  "+(s==null?"—":Fmt(s.Gyro,2000.0/32768)),1006,447,normal,Ink);
        TextAt(g,"Accel g    "+(s==null?"—":Fmt(s.Accel,2.0/32768)),1006,474,normal,Ink);
    }
    static string Fmt(int[] a,double scale){return String.Format("{0,7:0.00}  {1,7:0.00}  {2,7:0.00}",a[0]*scale,a[1]*scale,a[2]*scale);}
    void DrawGuide(Graphics g){Box(g,32,832,1468,86,Card);var c=guide.Current;
        if(c==null){TextAt(g,guide.Index<0?"Guided check":"Guided check complete",50,844,heading,Ink);int pass=0,skip=0,fail=0;foreach(var s in guide.Steps){if(s.Result=="passed"||s.Result=="confirmed")pass++;if(s.Result=="skipped")skip++;if(s.Result=="failed")fail++;}TextAt(g,guide.Index<0?"Press R or click here to check every control. Each step waits for real Windows input.":String.Format("{0} passed / confirmed · {1} skipped · {2} failed. F9 saves the evidence.",pass,skip,fail),50,879,normal,Muted);}
        else {TextAt(g,String.Format("{0}/{1}  {2}",guide.Index+1,guide.Steps.Count,c.Name),50,842,heading,Mint);TextAt(g,c.Instruction,370,843,normal,Ink);TextAt(g,guide.Hint+"   S: skip unverified · P: previous · F9: save",370,879,small,Muted);}
    }
    void Centre(){lock(data.Sync){var q=steamMotion!=null?steamMotion.Quaternion:Rotation.Unit(data.Latest);if(q!=null)zero=new[]{q[0],-q[1],-q[2],-q[3]};}}
    async void Haptic(int side){if(hapticBusy||demo||hid==null)return;hapticBusy=true;bool ok=await Task.Run(()=>hid.Rumble(side));hapticBusy=false;guide.HapticSent(data,side,ok);message=ok?"Windows sent the haptic command. Confirm what you felt in the guided check.":"Haptic write failed; check the relay and native device.";}
    void Save(){lock(data.Sync){string dir=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"Steam Controller Lab");Directory.CreateDirectory(dir);string file=Path.Combine(dir,"validation-"+DateTime.Now.ToString("yyyyMMdd-HHmmss")+".json");var result=new {schema=1,simulation=demo,utc=DateTime.UtcNow.ToString("o"),device=data.Device,transport="Prototype relay; viewer reads Windows HID",reports=data.Reports,invalid=data.Invalid,sequenceDiscontinuities=data.Discontinuities,presses=data.Presses,releases=data.Releases,min=data.Min,max=data.Max,steps=guide.Steps,raw=data.Latest==null?null:BitConverter.ToString(data.Latest.Raw)};File.WriteAllText(file,new JavaScriptSerializer().Serialize(result));message="Saved "+file;}}
    void Fullscreen(){if(FormBorderStyle==FormBorderStyle.None){FormBorderStyle=FormBorderStyle.Sizable;WindowState=FormWindowState.Normal;}else{FormBorderStyle=FormBorderStyle.None;WindowState=FormWindowState.Maximized;}}
    void KeysDown(object sender,KeyEventArgs e){if(e.KeyCode==Keys.R){savedComplete=false;hapticStep=-1;guide.Start(data);}if(e.KeyCode==Keys.C)Centre();if(e.KeyCode==Keys.H)Haptic(0);if(e.KeyCode==Keys.J)Haptic(1);if(e.KeyCode==Keys.F9)Save();if(e.KeyCode==Keys.F11)Fullscreen();if(e.KeyCode==Keys.Escape&&FormBorderStyle==FormBorderStyle.None)Fullscreen();if(e.KeyCode==Keys.Q&&e.Control)Close();if(e.KeyCode==Keys.Enter)guide.Confirm(data);if(e.KeyCode==Keys.S)guide.Next(data,"skipped","User skipped; not verified.");if(e.KeyCode==Keys.P&&guide.Index>0){guide.Index--;guide.Arm(data);}}
    void ClickAt(object sender,MouseEventArgs e){float scale=Math.Min(ClientSize.Width/1536f,ClientSize.Height/960f);float x=e.X/scale,y=e.Y/scale;if(y>830&&y<920&&guide.Current==null)guide.Start(data);if(x>986&&y>145&&y<599)Centre();}
    public void Snapshot(string path){using(var bitmap=new Bitmap(1536,960)){using(var graphics=Graphics.FromImage(bitmap))Render(graphics,1536,960);bitmap.Save(path);}}
    static byte[] Demo(){var b=new byte[54];b[0]=0x42;b[2]=1;b[5]=0x22;Put(b,6,11000);Put(b,10,14000);Put(b,12,-9000);Put(b,18,-15000);Put(b,20,19000);Put(b,22,12000);Put(b,24,9000);Put(b,26,-12000);Put(b,28,20000);Put(b,38,16384);Put(b,40,700);Put(b,42,-180);Put(b,44,380);Put(b,46,30000);Put(b,48,5000);Put(b,50,9000);Put(b,52,3000);return b;}
    static void Put(byte[] b,int at,int v){b[at]=(byte)v;b[at+1]=(byte)(v>>8);}
    static int CaptureReports(int seconds,string path){
        if(seconds<1||seconds>600)return 2;
        var tracker=new Tracker();using(var device=new NativeHid(tracker)){device.Start();System.Threading.Thread.Sleep(seconds*1000);
            lock(tracker.Sync){var report=new {reports=tracker.Reports,invalid=tracker.Invalid,device=tracker.Device,connected=tracker.Connected,presses=tracker.Presses,raw=tracker.Latest==null?null:BitConverter.ToString(tracker.Latest.Raw)};File.WriteAllText(path,new JavaScriptSerializer().Serialize(report));Console.WriteLine("Windows HID reports received: "+tracker.Reports);return tracker.Reports>0?0:4;}}
    }
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern bool SetProcessDPIAware();
    [STAThread] public static int Main(string[] args){SetProcessDPIAware();if(Array.IndexOf(args,"--steam-input")>=0)Environment.SetEnvironmentVariable("CONTROLLER_LAB_STEAM_INPUT","1");if(args.Length>0&&args[0]=="--self-test")return Tests.Run();if(args.Length==3&&args[0]=="--capture")return CaptureReports(int.Parse(args[1]),args[2]);Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);bool demo=Array.IndexOf(args,"--demo")>=0;using(var form=new Tester(demo)){if(args.Length>=3&&args[0]=="--snapshot"){form.Snapshot(args[1]);return 0;}if(Array.IndexOf(args,"--windowed")<0){form.FormBorderStyle=FormBorderStyle.None;form.WindowState=FormWindowState.Maximized;}Application.Run(form);}return 0;}
}
}
