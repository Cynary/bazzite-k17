// SPDX-License-Identifier: MIT
using System;
using System.Collections.Generic;
using System.Drawing;
namespace Moonmachine.ControllerTest {
// Small software mesh renderer: all controls are geometry, including on the back.
// Dimensions are illustrative, not a CAD scan of the controller.
public static class ControllerModel {
    sealed class Face { public double[][] V; public Color C;  }
    static readonly Color Shell=Color.FromArgb(65,73,87), Edge=Color.FromArgb(35,42,53), Rubber=Color.FromArgb(24,28,35), Mint=Color.FromArgb(78,231,185);
    sealed class Mesh {
        public List<Face> Faces=new List<Face>();
        public void Poly(Color c,params double[][] v){Faces.Add(new Face{V=v,C=c});}
        public void Oval(double x,double y,double z,double rx,double ry,double rz,Color c){
            const int n=24,m=12;
            for(int j=0;j<m;j++)for(int i=0;i<n;i++){
                double a=i*Math.PI*2/n,b=(i+1)*Math.PI*2/n,t=-Math.PI/2+j*Math.PI/m,u=-Math.PI/2+(j+1)*Math.PI/m;
                Poly(c,Sphere(x,y,z,rx,ry,rz,a,t),Sphere(x,y,z,rx,ry,rz,b,t),Sphere(x,y,z,rx,ry,rz,b,u),Sphere(x,y,z,rx,ry,rz,a,u));
            }
        }
        static double[] Sphere(double x,double y,double z,double rx,double ry,double rz,double a,double t){return new[]{x+rx*Math.Cos(t)*Math.Cos(a),y+ry*Math.Cos(t)*Math.Sin(a),z+rz*Math.Sin(t)};}
        public void Disk(double x,double y,double z,double r,double h,Color c){
            for(int i=0;i<24;i++){double a=i*Math.PI/12,b=(i+1)*Math.PI/12;var p=new[]{x+r*Math.Cos(a),y+r*Math.Sin(a),z};var q=new[]{x+r*Math.Cos(b),y+r*Math.Sin(b),z};var pp=new[]{p[0],p[1],z+h};var qq=new[]{q[0],q[1],z+h};Poly(c,p,q,qq,pp);Poly(c,new[]{x,y,z+h},pp,qq);}
        }
        public void Slab(double x,double y,double z,double w,double h,double d,Color c){
            double[][] p={new[]{x-w/2,y-h/2,z},new[]{x+w/2,y-h/2,z},new[]{x+w/2,y+h/2,z},new[]{x-w/2,y+h/2,z}};
            var top=new double[4][];for(int i=0;i<4;i++)top[i]=new[]{p[i][0],p[i][1],z+d};
            Poly(c,top);Poly(c,p[3],p[2],p[1],p[0]);for(int i=0;i<4;i++)Poly(c,p[i],p[(i+1)%4],top[(i+1)%4],top[i]);
        }
    }
    static bool On(State s,int bit){return s!=null&&s.Down(bit);}
    static Color Active(State s,int bit,Color c){return On(s,bit)?Mint:c;}
    public static void Draw(Graphics g,double[] orientation,State s){
        var mesh=new Mesh();
        // Three shell rings form a bevel rather than a flat extruded silhouette.
        double[,] outline={{-1.8,.65},{-1.65,1.0},{-1.2,1.12},{-.55,1.05},{.55,1.05},{1.2,1.12},{1.65,1.0},{1.8,.65},{1.95,-.75},{1.78,-1.18},{1.4,-1.28},{1.13,-.98},{.9,-.52},{-.9,-.52},{-1.13,-.98},{-1.4,-1.28},{-1.78,-1.18},{-1.95,-.75}};
        int n=outline.GetLength(0);var rings=new double[3][][];
        for(int r=0;r<3;r++){rings[r]=new double[n][];double scale=r==1?1:.92,z=r==0?-.32:r==1?-.02:.25;for(int i=0;i<n;i++)rings[r][i]=new[]{outline[i,0]*scale,outline[i,1]*scale,z};}
        for(int i=0;i<n;i++){int j=(i+1)%n;mesh.Poly(Shell,new[]{0.0,0,.28},rings[2][i],rings[2][j]);mesh.Poly(Edge,new[]{0.0,0,-.34},rings[0][j],rings[0][i]);for(int r=0;r<2;r++)mesh.Poly(r==0?Edge:Shell,rings[r][i],rings[r][j],rings[r+1][j],rings[r+1][i]);}
        foreach(int side in new[]{-1,1}){
            int k=side<0?0:1;double x=side*1.42;
            mesh.Oval(x,-.53,-.08,.45,.72,.39,Shell);
            mesh.Oval(x,-.60,-.29,.34,.55,.16,Rubber);
            mesh.Slab(side*1.18,.92,.27,.66,.21,.15,Active(s,side<0?19:9,Edge));
            mesh.Slab(side*1.18,1.01,-.33,.60,.35,.27,Color.FromArgb(80,88,100));
            // Trackpad rim, recessed surface, and moving touch point.
            mesh.Slab(side*1.16,-.18,.28,.75,.59,.055,Color.FromArgb(100,109,122));
            mesh.Slab(side*1.16,-.18,.337,.68,.52,.012,Active(s,side<0?26:22,Rubber));
            if(On(s,side<0?25:21))mesh.Disk(side*1.16+s.Pads[k*2]/32768.0*.28,-.18+s.Pads[k*2+1]/32768.0*.21,.35,.04,.01,Mint);
            double sx=side*.63,sy=.49;mesh.Disk(sx,sy,.28,.28,.055,Edge);
            double dx=s==null?0:s.Sticks[k*2]/32768.0*.09,dy=s==null?0:s.Sticks[k*2+1]/32768.0*.09;
            mesh.Disk(sx+dx,sy+dy,.32,.10,.19,Color.FromArgb(105,113,127));
            mesh.Oval(sx+dx,sy+dy,.52,.23,.23,.065,Active(s,side<0?15:5,Rubber));
            // Rear grip buttons protrude from the underside.
            mesh.Slab(side*1.23,-.36,-.48,.22,.42,.075,Active(s,side<0?17:7,Color.FromArgb(102,112,127)));
            mesh.Slab(side*1.55,-.56,-.48,.20,.37,.075,Active(s,side<0?18:8,Color.FromArgb(82,92,106)));
        }
        int[] bits={3,1,0,2};Color[] colors={Color.FromArgb(220,188,96),Color.FromArgb(207,107,110),Color.FromArgb(120,190,142),Color.FromArgb(108,160,221)};
        for(int i=0;i<4;i++){double a=Math.PI/2-i*Math.PI/2;mesh.Disk(1.34+.19*Math.Cos(a),.57+.19*Math.Sin(a),.29,.095,.07,Active(s,bits[i],colors[i]));}
        mesh.Slab(-1.34,.57,.29,.16,.59,.075,Active(s,13,Rubber));mesh.Slab(-1.34,.57,.29,.59,.16,.08,Active(s,11,Rubber));
        mesh.Disk(-.23,.52,.28,.067,.035,Active(s,14,Edge));mesh.Disk(.23,.52,.28,.067,.035,Active(s,6,Edge));
        mesh.Disk(0,.12,.29,.14,.045,Active(s,16,Color.FromArgb(149,163,181)));mesh.Disk(0,-.22,.29,.09,.035,Active(s,4,Edge));
        // USB port makes the shoulder edge and its orientation easy to identify.
        mesh.Slab(0,1.058,-.08,.22,.022,.10,Rubber);
        var camera=Rotation.Multiply(new[]{Math.Cos(.36),Math.Sin(.36),0.0,0.0},orientation);
        foreach(var f in mesh.Faces){for(int i=0;i<f.V.Length;i++)f.V[i]=Rotation.Apply(camera,f.V[i][0],f.V[i][1],f.V[i][2]);}
        double extentX=1,extentY=1;foreach(var f in mesh.Faces)foreach(var v in f.V){double k=7/(7-v[2]);extentX=Math.Max(extentX,Math.Abs(v[0]*k));extentY=Math.Max(extentY,Math.Abs(v[1]*k));}double viewScale=Math.Min(91,Math.Min(235/extentX,108/extentY));
        const int width=503,height=226;var pixels=new int[width*height];var depth=new double[pixels.Length];for(int i=0;i<depth.Length;i++)depth[i]=double.NegativeInfinity;
        foreach(var f in mesh.Faces){
            var a=f.V[0];var b=f.V[1];var c=f.V[2];double ux=b[0]-a[0],uy=b[1]-a[1],uz=b[2]-a[2],vx=c[0]-a[0],vy=c[1]-a[1],vz=c[2]-a[2];
            double nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx;double norm=Math.Sqrt(nx*nx+ny*ny+nz*nz);
            double light=norm<1e-8?.65:.46+.54*Math.Abs((-.35*nx+.55*ny+.76*nz)/norm);
            int color=Color.FromArgb((int)(f.C.R*light),(int)(f.C.G*light),(int)(f.C.B*light)).ToArgb();
            var p=new double[f.V.Length][];for(int i=0;i<p.Length;i++){var v=f.V[i];double k=7/(7-v[2]);p[i]=new[]{248+v[0]*viewScale*k,112-v[1]*viewScale*k,k};}
            for(int i=1;i<p.Length-1;i++)Triangle(p[0],p[i],p[i+1],color,pixels,depth,width,height);
        }
        using(var bitmap=new Bitmap(width,height,System.Drawing.Imaging.PixelFormat.Format32bppArgb)){
            var locked=bitmap.LockBits(new Rectangle(0,0,width,height),System.Drawing.Imaging.ImageLockMode.WriteOnly,bitmap.PixelFormat);
            try{System.Runtime.InteropServices.Marshal.Copy(pixels,0,locked.Scan0,pixels.Length);}finally{bitmap.UnlockBits(locked);}
            g.DrawImage(bitmap,992,213,width,height);
        }
    }
    static void Triangle(double[] a,double[] b,double[] c,int color,int[] pixels,double[] depth,int width,int height){
        double area=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1]);if(Math.Abs(area)<1e-7)return;
        int x0=Math.Max(0,(int)Math.Floor(Math.Min(a[0],Math.Min(b[0],c[0])))),x1=Math.Min(width-1,(int)Math.Ceiling(Math.Max(a[0],Math.Max(b[0],c[0]))));
        int y0=Math.Max(0,(int)Math.Floor(Math.Min(a[1],Math.Min(b[1],c[1])))),y1=Math.Min(height-1,(int)Math.Ceiling(Math.Max(a[1],Math.Max(b[1],c[1]))));
        for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++){
            double u=((b[1]-c[1])*(x+.5-c[0])+(c[0]-b[0])*(y+.5-c[1]))/area;
            double v=((c[1]-a[1])*(x+.5-c[0])+(a[0]-c[0])*(y+.5-c[1]))/area,w=1-u-v;
            if(u<0||v<0||w<0)continue;double z=u*a[2]+v*b[2]+w*c[2];int i=y*width+x;if(z>depth[i]){depth[i]=z;pixels[i]=color;}
        }
    }
}
}
