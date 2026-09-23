// SPDX-License-Identifier: MIT
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using Microsoft.Win32.SafeHandles;

namespace Moonmachine.ControllerTest {
public sealed class NativeHid : IDisposable {
    [StructLayout(LayoutKind.Sequential)] struct Interface {public int Size;public Guid Class;public int Flags;public IntPtr Reserved;}
    [StructLayout(LayoutKind.Sequential)] struct Attributes {public int Size;public ushort Vendor,Product,Version;}
    [StructLayout(LayoutKind.Sequential)] struct Overlap {public IntPtr Internal,InternalHigh;public uint Offset,OffsetHigh;public IntPtr Event;}
    [DllImport("hid.dll")] static extern void HidD_GetHidGuid(out Guid g);
    [DllImport("hid.dll",SetLastError=true)] static extern bool HidD_SetFeature(SafeFileHandle h,byte[] data,int length);
    [DllImport("hid.dll")] static extern bool HidD_GetAttributes(SafeFileHandle h,ref Attributes a);
    [DllImport("setupapi.dll",CharSet=CharSet.Unicode)] static extern IntPtr SetupDiGetClassDevs(ref Guid g,string e,IntPtr w,uint flags);
    [DllImport("setupapi.dll")] static extern bool SetupDiEnumDeviceInterfaces(IntPtr set,IntPtr d,ref Guid g,uint index,ref Interface i);
    [DllImport("setupapi.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool SetupDiGetDeviceInterfaceDetail(IntPtr set,ref Interface i,IntPtr detail,uint size,out uint required,IntPtr device);
    [DllImport("setupapi.dll")] static extern bool SetupDiDestroyDeviceInfoList(IntPtr set);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern SafeFileHandle CreateFile(string path,uint access,uint share,IntPtr security,uint disposition,uint flags,IntPtr template);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool ReadFile(SafeFileHandle h,IntPtr b,uint n,out uint got,IntPtr overlap);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool WriteFile(SafeFileHandle h,byte[] b,uint n,out uint got,IntPtr overlap);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetOverlappedResult(SafeFileHandle h,IntPtr overlap,out uint n,bool wait);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool CancelIoEx(SafeFileHandle h,IntPtr overlap);
    readonly Tracker tracker;
    volatile bool stopping;
    Thread worker;
    string path;
    readonly object pathLock=new object();
    public NativeHid(Tracker t){tracker=t;}
    public void Start(){worker=new Thread(Run){IsBackground=true,Name="Steam Controller HID"};worker.Start();}
    static SafeFileHandle Open(string p,bool async){return CreateFile(p,0xc0000000,3,IntPtr.Zero,3,async?0x40000000u:0,IntPtr.Zero);}
    static string Find(out ushort version){
        version=0;Guid guid;HidD_GetHidGuid(out guid);var set=SetupDiGetClassDevs(ref guid,null,IntPtr.Zero,0x12);
        try{for(uint n=0;;n++){
            var i=new Interface{Size=Marshal.SizeOf(typeof(Interface))};if(!SetupDiEnumDeviceInterfaces(set,IntPtr.Zero,ref guid,n,ref i))break;
            uint size;SetupDiGetDeviceInterfaceDetail(set,ref i,IntPtr.Zero,0,out size,IntPtr.Zero);if(size<8||size>65536)continue;
            IntPtr detail=Marshal.AllocHGlobal((int)size);try{
                Marshal.WriteInt32(detail,IntPtr.Size==8?8:6);
                if(!SetupDiGetDeviceInterfaceDetail(set,ref i,detail,size,out size,IntPtr.Zero))continue;
                string p=Marshal.PtrToStringUni(IntPtr.Add(detail,4));
                if(p.IndexOf("vid_28de&pid_1304",StringComparison.OrdinalIgnoreCase)<0||p.IndexOf("mi_02",StringComparison.OrdinalIgnoreCase)<0)continue;
                using(var h=Open(p,true)){if(h.IsInvalid)continue;var a=new Attributes{Size=Marshal.SizeOf(typeof(Attributes))};if(HidD_GetAttributes(h,ref a)&&a.Vendor==0x28de&&a.Product==0x1304){version=a.Version;return p;}}
            }finally{Marshal.FreeHGlobal(detail);}
        }}finally{SetupDiDestroyDeviceInfoList(set);}return null;
    }
    void Run(){while(!stopping){
        try{ushort version;var p=Find(out version);if(p==null){tracker.Disconnect("No native Steam Controller in Windows. Start the prototype relay.");Thread.Sleep(750);continue;}
            using(var h=Open(p,true)){
                if(h.IsInvalid){Thread.Sleep(750);continue;}
                lock(pathLock)path=p;
                // Request raw IMU and the controller's fused orientation. This changes
                // a runtime sensor setting, not persistent calibration or pairing.
                using(var control=Open(p,false)){
                    var settings=new byte[64];settings[0]=1;settings[1]=0x87;
                    settings[2]=3;settings[3]=48;settings[4]=0x1c;
                    if(!control.IsInvalid)HidD_SetFeature(control,settings,settings.Length);
                }
                tracker.Open("Windows HID 28DE:1304 / MI_02 / revision "+version.ToString("X4"));
                IntPtr buffer=Marshal.AllocHGlobal(64),ov=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Overlap)));
                using(var ready=new ManualResetEvent(false)){
                    try{while(!stopping){
                        ready.Reset();Marshal.StructureToPtr(new Overlap{Event=ready.SafeWaitHandle.DangerousGetHandle()},ov,false);
                        uint got;bool ok=ReadFile(h,buffer,54,out got,ov);
                        if(!ok&&Marshal.GetLastWin32Error()==997){
                            while(!ready.WaitOne(200)&&!stopping){}
                            if(stopping)CancelIoEx(h,ov);
                            ok=GetOverlappedResult(h,ov,out got,true);
                        }
                        if(!ok)break;if(got==0||got>64)break;var b=new byte[got];Marshal.Copy(buffer,b,0,(int)got);tracker.Add(b);
                    }}finally{CancelIoEx(h,ov);Marshal.FreeHGlobal(ov);Marshal.FreeHGlobal(buffer);}
                }
            }
        }catch(Exception e){tracker.Disconnect("HID read: "+e.Message);}
        finally{lock(pathLock)path=null;tracker.Disconnect("Native controller disconnected. Waiting for reconnection.");}
        if(!stopping)Thread.Sleep(500);
    }}
    public bool Rumble(int side){string p;lock(pathLock)p=path;if(p==null)return false;
        using(var h=Open(p,false)){if(h.IsInvalid)return false;bool ok=true;var b=new byte[64];b[0]=0x80;
            b[side==0?5:8]=0x18;
            try{for(int i=0;i<7;i++){uint n;ok=WriteFile(h,b,64,out n,IntPtr.Zero)&&n==64&&ok;Thread.Sleep(35);}}
            finally{Array.Clear(b,1,63);uint n;ok=WriteFile(h,b,64,out n,IntPtr.Zero)&&n==64&&ok;}
            return ok;
        }
    }
    public void Dispose(){stopping=true;if(worker!=null)worker.Join(2000);}
}
}
