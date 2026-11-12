using System;
using System.Runtime.InteropServices;
using System.Text;

// Read-only USB descriptor dump for a device that has no function driver.
// Uses the USB hub IOCTLs (usbioctl.h) so it works on the "Unknown"
// VID_FFFF/PID_FFFE node without installing any driver and without
// sending anything to the device.

class UsbDesc
{
    const int CM_GET_DEVICE_INTERFACE_LIST_PRESENT = 0x1;

    [DllImport("cfgmgr32.dll", CharSet = CharSet.Unicode)]
    static extern int CM_Get_Device_Interface_List_SizeW(out int pulLen, ref Guid guid, string pDeviceID, int flags);
    [DllImport("cfgmgr32.dll", CharSet = CharSet.Unicode)]
    static extern int CM_Get_Device_Interface_ListW(ref Guid guid, string pDeviceID, [Out] char[] buffer, int bufferLen, int flags);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern IntPtr CreateFileW(string name, uint access, uint share, IntPtr sec, uint disp, uint flags, IntPtr tmpl);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool DeviceIoControl(IntPtr h, uint code, byte[] inBuf, int inLen, byte[] outBuf, int outLen, out int ret, IntPtr overlapped);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool CloseHandle(IntPtr h);

    const uint GENERIC_READ = 0x80000000;
    const uint GENERIC_WRITE = 0x40000000;
    const uint FILE_SHARE_READ = 1;
    const uint FILE_SHARE_WRITE = 2;
    const uint OPEN_EXISTING = 3;

    static uint USB_CTL(int fn) { return (uint)((0x22 << 16) | (fn << 2)); }

    static IntPtr OpenHub(string path)
    {
        IntPtr h = CreateFileW(path, GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE, IntPtr.Zero, OPEN_EXISTING, 0, IntPtr.Zero);
        if (h == new IntPtr(-1))
            h = CreateFileW(path, GENERIC_READ,
                FILE_SHARE_READ | FILE_SHARE_WRITE, IntPtr.Zero, OPEN_EXISTING, 0, IntPtr.Zero);
        return h;
    }

    static bool GetConnInfo(IntPtr h, int port, out byte[] data, out int err)
    {
        int size = 4096;
        byte[] buf = new byte[size];
        BitConverter.GetBytes((uint)port).CopyTo(buf, 0);
        int ret;
        bool ok = DeviceIoControl(h, USB_CTL(266), buf, 4, buf, size, out ret, IntPtr.Zero);
        err = ok ? 0 : Marshal.GetLastWin32Error();
        data = buf;
        return ok;
    }

    static bool GetDescriptor(IntPtr h, int port, byte type, ushort index, ushort lang, int len, out byte[] data, out int err)
    {
        int total = 12 + len;
        byte[] buf = new byte[total];
        BitConverter.GetBytes((uint)port).CopyTo(buf, 0);
        buf[4] = 0x80;
        buf[5] = 0x06;
        BitConverter.GetBytes((ushort)((type << 8) | index)).CopyTo(buf, 6);
        BitConverter.GetBytes(lang).CopyTo(buf, 8);
        BitConverter.GetBytes((ushort)len).CopyTo(buf, 10);
        int ret;
        bool ok = DeviceIoControl(h, USB_CTL(260), buf, 12, buf, total, out ret, IntPtr.Zero);
        err = ok ? 0 : Marshal.GetLastWin32Error();
        if (!ok) { data = null; return false; }
        int dlen = ret - 12;
        if (dlen < 0) dlen = 0;
        if (dlen > len) dlen = len;
        data = new byte[dlen];
        Array.Copy(buf, 12, data, 0, dlen);
        return true;
    }

    static string Hex(byte[] b)
    {
        if (b == null) return "<null>";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < b.Length; i++) sb.Append(b[i].ToString("X2")).Append(' ');
        return sb.ToString().Trim();
    }

    static string Str(byte[] b, int off, int len)
    {
        if (b == null || off + len > b.Length) return "";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < len; i++)
        {
            byte c = b[off + i];
            sb.Append(c >= 32 && c < 127 ? (char)c : '.');
        }
        return sb.ToString();
    }

    static void DumpConfig(byte[] d)
    {
        Console.WriteLine("  config raw: " + Hex(d));
        if (d.Length < 9) return;
        int total = d[2] | (d[3] << 8);
        Console.WriteLine(string.Format("  config: total={0} ifs={1} value={2} attr=0x{3:X2} maxPower={4}",
            total, d[4], d[5], d[7], d[8]));
        int i = 0;
        while (i + 2 <= d.Length)
        {
            int bl = d[i];
            int bt = d[i + 1];
            if (bl < 2 || i + bl > d.Length) break;
            if (bt == 0x04 && bl >= 9)
            {
                Console.WriteLine(string.Format("    IF {0} alt {1} eps {2} class={3:X2}/{4:X2}/{5:X2} iStr={6}",
                    d[i + 2], d[i + 3], d[i + 4], d[i + 5], d[i + 6], d[i + 7], d[i + 8]));
            }
            else if (bt == 0x05 && bl >= 7)
            {
                Console.WriteLine(string.Format("      EP 0x{0:X2} attr=0x{1:X2} max={2} interval={3}",
                    d[i + 2], d[i + 3], d[i + 4] | (d[i + 5] << 8), d[i + 6]));
            }
            else if (bt == 0x21)
            {
                Console.WriteLine("      DFU FUNCTIONAL: " + Hex(Slice(d, i, bl)));
                if (bl >= 7)
                {
                    int attrs = d[i + 2];
                    int detach = d[i + 3] | (d[i + 4] << 8);
                    int xfer = d[i + 5] | (d[i + 6] << 8);
                    int ver = bl >= 9 ? (d[i + 7] | (d[i + 8] << 8)) : -1;
                    Console.WriteLine(string.Format("        bmAttributes=0x{0:X2} detachTimeout={1} transferSize={2} bcdDFU=0x{3:X4}",
                        attrs, detach, xfer, ver));
                }
            }
            else
            {
                Console.WriteLine(string.Format("      desc type=0x{0:X2} len={1}: {2}  |{3}|",
                    bt, bl, Hex(Slice(d, i, bl)), Str(d, i, bl)));
            }
            i += bl;
        }
    }

    static byte[] Slice(byte[] b, int off, int len)
    {
        if (off + len > b.Length) len = b.Length - off;
        byte[] r = new byte[len];
        Array.Copy(b, off, r, 0, len);
        return r;
    }

    static void Main()
    {
        Guid hubGuid = new Guid("F18A0E88-C30C-11D0-8815-00A0C906BED8");
        int len;
        int cr = CM_Get_Device_Interface_List_SizeW(out len, ref hubGuid, null, CM_GET_DEVICE_INTERFACE_LIST_PRESENT);
        if (cr != 0) { Console.WriteLine("CM size failed " + cr); return; }
        char[] buf = new char[len];
        cr = CM_Get_Device_Interface_ListW(ref hubGuid, null, buf, len, CM_GET_DEVICE_INTERFACE_LIST_PRESENT);
        if (cr != 0) { Console.WriteLine("CM list failed " + cr); return; }
        string all = new string(buf);
        string[] paths = all.Split('\0');
        bool found = false;
        for (int pi = 0; pi < paths.Length; pi++)
        {
            string p = paths[pi];
            if (p == null || p.Length == 0) continue;
            Console.WriteLine("HUB: " + p);
            IntPtr h = OpenHub(p);
            if (h == new IntPtr(-1))
            {
                Console.WriteLine("  open failed, win32=" + Marshal.GetLastWin32Error());
                continue;
            }
            for (int port = 1; port <= 15; port++)
            {
                byte[] ci;
                int cerr;
                if (!GetConnInfo(h, port, out ci, out cerr))
                {
                    if (port <= 4) Console.WriteLine(string.Format("  port {0}: IOCTL failed win32={1}", port, cerr));
                    continue;
                }
                int status = BitConverter.ToInt32(ci, 32);
                Console.WriteLine(string.Format("  port {0}: status={1} raw={2}", port, status, Hex(Slice(ci, 0, 36))));
                if (status != 1) continue;
                ushort vid = BitConverter.ToUInt16(ci, 12);
                ushort pid = BitConverter.ToUInt16(ci, 14);
                Console.WriteLine(string.Format("  PORT {0}: VID={1:X4} PID={2:X4} speed={3} addr={4} status={5}",
                    port, vid, pid, ci[23], BitConverter.ToUInt16(ci, 26), status));
                if (vid != 0xFFFF || pid != 0xFFFE) continue;
                found = true;
                Console.WriteLine("  DEVICE: " + Hex(Slice(ci, 4, 18)));
                Console.WriteLine(string.Format("    bcdUSB=0x{0:X4} class={1:X2}/{2:X2}/{3:X2} ep0={4}",
                    BitConverter.ToUInt16(ci, 6), ci[8], ci[9], ci[10], ci[11]));
                byte[] cfg;
                int derr;
                if (GetDescriptor(h, port, 2, 0, 0, 0x1000, out cfg, out derr))
                    DumpConfig(cfg);
                else
                    Console.WriteLine("  config descriptor failed, win32=" + derr);
                byte[] s0;
                ushort lang = 0x0409;
                if (GetDescriptor(h, port, 3, 0, 0, 255, out s0, out derr) && s0.Length >= 4)
                    lang = BitConverter.ToUInt16(s0, 2);
                Console.WriteLine(string.Format("  LANGID=0x{0:X4}", lang));
                for (int si = 1; si <= 8; si++)
                {
                    byte[] s;
                    if (GetDescriptor(h, port, 3, (ushort)si, lang, 255, out s, out derr) && s.Length > 2)
                    {
                        int l = s[0];
                        if (l > s.Length) l = s.Length;
                        string str = Encoding.Unicode.GetString(s, 2, Math.Max(0, l - 2));
                        Console.WriteLine(string.Format("  string[{0}] = \"{1}\"", si, str.TrimEnd('\0')));
                    }
                }
            }
            CloseHandle(h);
        }
        if (!found) Console.WriteLine("VID_FFFF/PID_FFFE not found on any hub port");
    }
}
