using System;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;

namespace SimpleLeap
{
    public static class Input
    {
        [DllImport("user32.dll")]
        static extern bool GetCursorPos(out POINT point);

        public struct POINT
        {
            public int x;
            public int y;
        }
        public static POINT GetMousePosition()
        {
            POINT pos;
            GetCursorPos(out pos);
            return pos;
        }

        [DllImport("user32.dll")]
        public static extern bool GetAsyncKeyState(int button);
        public static bool IsMouseButtonPressed(MouseButton button)
        {
            return GetAsyncKeyState((int)button);
        }
        public enum MouseButton
        {
            LeftMouseButton = 0x01,
            RightMouseButton = 0x02,
            MiddleMouseButton = 0x04,
        }

        [DllImport("user32.dll")]
        public static extern bool EnumDisplaySettings(string deviceName, int modeNum, ref DEVMODE devMode);

        [StructLayout(LayoutKind.Sequential)]
        public struct DEVMODE
        {
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 0x20)]
            public string dmDeviceName;
            public short dmSpecVersion;
            public short dmDriverVersion;
            public short dmSize;
            public short dmDriverExtra;
            public int dmFields;
            public int dmPositionX;
            public int dmPositionY;
            public int dmDisplayOrientation;
            public int dmDisplayFixedOutput;
            public short dmColor;
            public short dmDuplex;
            public short dmYResolution;
            public short dmTTOption;
            public short dmCollate;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 0x20)]
            public string dmFormName;
            public short dmLogPixels;
            public int dmBitsPerPel;
            public int dmPelsWidth;
            public int dmPelsHeight;
            public int dmDisplayFlags;
            public int dmDisplayFrequency;
            public int dmICMMethod;
            public int dmICMIntent;
            public int dmMediaType;
            public int dmDitherType;
            public int dmReserved1;
            public int dmReserved2;
            public int dmPanningWidth;
            public int dmPanningHeight;
        }
    }

    class Program
    {
        static void Main(string[] args)
        {
            int bLevel = 0;
            int tLevel = 0;
            Console.WriteLine("Hello Leap Relay!");
            const int ENUM_CURRENT_SETTINGS = -1;

            Input.DEVMODE devMode = default;
            devMode.dmSize = (short)Marshal.SizeOf(devMode);
            Input.EnumDisplaySettings(null, ENUM_CURRENT_SETTINGS, ref devMode);

            int screenWidth = devMode.dmPelsWidth;
            int screenHeight = devMode.dmPelsHeight;

            Console.WriteLine("Resolution: {0} by {1}", devMode.dmPelsWidth, devMode.dmPelsHeight);

            System.Threading.Thread.Sleep(500);

            bool lightOn = false;
            string lampIP = "192.168.15.10";
            int lampPort = 6819;

            Input.POINT myPoint;
            bool leftButton = false;

            Socket sock = new Socket(AddressFamily.InterNetwork, SocketType.Dgram,ProtocolType.Udp);

            IPAddress serverAddr = IPAddress.Parse(lampIP);

            IPEndPoint endPoint = new IPEndPoint(serverAddr, lampPort);

            string text = "Hello Lamp!";
            byte[] send_buffer = Encoding.ASCII.GetBytes(text);
            sock.SendTo(send_buffer, endPoint);

            while (true)
            {
                myPoint = Input.GetMousePosition();
                leftButton = Input.IsMouseButtonPressed(Input.MouseButton.LeftMouseButton);
                //Console.WriteLine("X: {0}, Y: {1}, Button: {2}", myPoint.x, myPoint.y, leftButton);
                float relW = (float)myPoint.x / (float)screenWidth;
                float relH = (float)myPoint.y / (float)screenHeight;

                //Console.WriteLine("relW: {0}, relH: {1}", relW, relH);

                if (leftButton)
                {
                    text = "ON";
                    byte[] lbuffer = Encoding.ASCII.GetBytes(text);
                    sock.SendTo(lbuffer, endPoint);

                    //lightOn = !lightOn;
                    //if(lightOn)
                    //{
                    //    text = "ON";
                    //    byte[] lbuffer = Encoding.ASCII.GetBytes(text);
                    //    sock.SendTo(lbuffer, endPoint);
                    //}
                    //else
                    //{
                    //    text = "OFF";
                    //    byte[] lbuffer = Encoding.ASCII.GetBytes(text);
                    //    sock.SendTo(lbuffer, endPoint);
                    //}
                    System.Threading.Thread.Sleep(1000);
                }
                // Top to bottom brightness
                if (0 <= relH && relH < 0.2 && bLevel != 5)
                {
                    text = "BPLUS";
                    byte[] lbuffer = Encoding.ASCII.GetBytes(text);
                    for (int i = 0; i<15; i++)
                    {
                        sock.SendTo(lbuffer, endPoint);
                    }
                    bLevel = 5;
                    Console.WriteLine("Change Brightness: {0}", bLevel);
                }
                else if (0.2 <= relH && relH < 0.4 && bLevel != 4)
                {
                    text = "B80";
                    byte[] lbuffer = Encoding.ASCII.GetBytes(text);
                    sock.SendTo(lbuffer, endPoint);
                    bLevel = 4;
                    Console.WriteLine("Change Brightness: {0}", bLevel);
                }
                else if (0.4 <= relH && relH < 0.6 && bLevel != 3)
                {
                    text = "B60";
                    byte[] lbuffer = Encoding.ASCII.GetBytes(text);
                    sock.SendTo(lbuffer, endPoint);
                    bLevel = 3;
                    Console.WriteLine("Change Brightness: {0}", bLevel);
                }
                else if (0.6 <= relH && relH < 0.8 && bLevel != 2)
                {
                    text = "B30";
                    byte[] lbuffer = Encoding.ASCII.GetBytes(text);
                    sock.SendTo(lbuffer, endPoint);
                    bLevel = 2;
                    Console.WriteLine("Change Brightness: {0}", bLevel);
                }
                else if (0.8 <= relH && relH < 1.0 && bLevel != 1)
                {
                    text = "BMINUS";
                    byte[] lbuffer = Encoding.ASCII.GetBytes(text);
                    for (int i = 0; i < 15; i++)
                    {
                        sock.SendTo(lbuffer, endPoint);
                    }
                    bLevel = 1;
                    Console.WriteLine("Change Brightness: {0}", bLevel);
                }


                // Color temperature
                if (0 <= relW && relW < 0.2 && tLevel != 5)
                {
                    text = "TPLUS";
                    byte[] lbuffer = Encoding.ASCII.GetBytes(text);
                    for (int i = 0; i < 15; i++)
                    {
                        sock.SendTo(lbuffer, endPoint);
                    }
                    tLevel = 5;
                    Console.WriteLine("Change Temperature: {0}", tLevel);
                }
                else if (0.2 <= relW && relW < 0.4 && tLevel != 4)
                {
                    text = "T5600";
                    byte[] lbuffer = Encoding.ASCII.GetBytes(text);
                    sock.SendTo(lbuffer, endPoint);
                    tLevel = 4;
                    Console.WriteLine("Change Temperature: {0}", tLevel);
                }
                else if (0.4 <= relW && relW < 0.6 && tLevel != 3)
                {
                    text = "T4400";
                    byte[] lbuffer = Encoding.ASCII.GetBytes(text);
                    sock.SendTo(lbuffer, endPoint);
                    tLevel = 3;
                    Console.WriteLine("Change Temperature: {0}", tLevel);
                }
                else if (0.6 <= relW && relW < 0.8 && tLevel != 2)
                {
                    text = "T3200";
                    byte[] lbuffer = Encoding.ASCII.GetBytes(text);
                    sock.SendTo(lbuffer, endPoint);
                    tLevel = 2;
                    Console.WriteLine("Change Temperature: {0}", tLevel);
                }
                else if (0.8 <= relW && relW < 1.0 && tLevel != 1)
                {
                    text = "TMINUS";
                    byte[] lbuffer = Encoding.ASCII.GetBytes(text);
                    for (int i = 0; i < 15; i++)
                    {
                        sock.SendTo(lbuffer, endPoint);
                    }
                    tLevel = 1;
                    Console.WriteLine("Change Temperature: {0}", tLevel);
                }
                System.Threading.Thread.Sleep(100);
            }
        }
    }
}
