// SPDX-License-Identifier: MIT
using System;
using System.Runtime.InteropServices;
namespace Moonmachine.ControllerTest {
public sealed class SteamMotion : IDisposable {
    [StructLayout(LayoutKind.Sequential)] public struct Motion {public float X,Y,Z,W,AX,AY,AZ,GX,GY,GZ;}
    [DllImport("steam_api64",CallingConvention=CallingConvention.Cdecl)] static extern int SteamAPI_InitFlat(System.Text.StringBuilder error);
    [DllImport("steam_api64",CallingConvention=CallingConvention.Cdecl)] static extern void SteamAPI_Shutdown();
    [DllImport("steam_api64",CallingConvention=CallingConvention.Cdecl)] static extern void SteamAPI_RunCallbacks();
    [DllImport("steam_api64",CallingConvention=CallingConvention.Cdecl)] static extern IntPtr SteamAPI_SteamInput_v007();
    [DllImport("steam_api64",CallingConvention=CallingConvention.Cdecl)] [return:MarshalAs(UnmanagedType.I1)] static extern bool SteamAPI_ISteamInput_Init(IntPtr p,[MarshalAs(UnmanagedType.I1)] bool explicitFrames);
    [DllImport("steam_api64",CallingConvention=CallingConvention.Cdecl)] static extern void SteamAPI_ISteamInput_RunFrame(IntPtr p,[MarshalAs(UnmanagedType.I1)] bool reserved);
    [DllImport("steam_api64",CallingConvention=CallingConvention.Cdecl)] static extern int SteamAPI_ISteamInput_GetConnectedControllers(IntPtr p,[Out] ulong[] handles);
    [DllImport("steam_api64",CallingConvention=CallingConvention.Cdecl)] static extern int SteamAPI_ISteamInput_GetInputTypeForHandle(IntPtr p,ulong handle);
    [DllImport("steam_api64",CallingConvention=CallingConvention.Cdecl)] static extern Motion SteamAPI_ISteamInput_GetMotionData(IntPtr p,ulong handle);
    System.IO.StreamWriter log;int ticks;
    IntPtr input;bool initialized;readonly ulong[] handles=new ulong[16];
    public string Status="Steam Input not initialized";public double[] Quaternion;public Motion Latest;public int Type,Count;
    public SteamMotion(){try{Environment.SetEnvironmentVariable("SteamAppId","480");log=new System.IO.StreamWriter(System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"steam-motion.jsonl"),false){AutoFlush=true};var error=new System.Text.StringBuilder(1024);initialized=SteamAPI_InitFlat(error)==0;if(!initialized){Status="Steam API initialization failed: "+error;log.WriteLine(Status);return;}input=SteamAPI_SteamInput_v007();if(input==IntPtr.Zero||!SteamAPI_ISteamInput_Init(input,true)){input=IntPtr.Zero;Status="Steam Input initialization failed";}}catch(Exception e){Status=e.GetType().Name+": "+e.Message;if(log!=null)log.WriteLine(Status);}}
    public void Poll(){if(input==IntPtr.Zero)return;SteamAPI_RunCallbacks();SteamAPI_ISteamInput_RunFrame(input,false);int oldCount=Count;Count=SteamAPI_ISteamInput_GetConnectedControllers(input,handles);if(Count!=oldCount)log.WriteLine("Controller count: "+Count);Quaternion=null;Status="Steam Input: "+Count+" controllers";
        for(int i=0;i<Count&&i<handles.Length;i++){int type=SteamAPI_ISteamInput_GetInputTypeForHandle(input,handles[i]);if(type!=1&&type!=17)continue;Type=type;Latest=SteamAPI_ISteamInput_GetMotionData(input,handles[i]);double norm=Latest.X*Latest.X+Latest.Y*Latest.Y+Latest.Z*Latest.Z+Latest.W*Latest.W;if(norm>.5&&norm<1.5)Quaternion=new[]{(double)Latest.W,Latest.X,Latest.Y,Latest.Z};Status="Steam Input controller type "+type;if((ticks++%3)==0)log.WriteLine(new System.Web.Script.Serialization.JavaScriptSerializer().Serialize(new {utc=DateTime.UtcNow.ToString("o"),type=Type,motion=Latest}));break;}}
    public void Dispose(){if(log!=null)log.Dispose();if(initialized)SteamAPI_Shutdown();}
}
}
