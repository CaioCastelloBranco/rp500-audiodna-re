using System;
using System.Runtime.InteropServices;
using System.Text;

// Probe every hub port with IOCTL_USB_GET_DESCRIPTOR_FROM_NODE_CONNECTION.
// This IOCTL is available on USB 3.0 root hubs even though the legacy
// GET_NODE_CONNECTION_INFORMATION_EX is not. Read-only.

class UsbDesc2
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

    static void DumpConfig(byte[] d)
    {
        if (d == null || d.Length < 9) { Console.WriteLine("    short config"); return; }
        int total = d[2] | (d[3] << 8);
        Console.WriteLine(string.Format("    config: total={0} ifs={1} value={2} attr=0x{3:X2} maxPower={4}",
            total, d[4], d[5], d[7], d[8]));
        int i = 0;
        while (i + 2 <= d.Length)
        {
            int bl = d[i];
            int bt = d[i + 1];
            if (bl < 2 || i + bl > d.Length) break;
            if (bt == 0x04 && bl >= 9)
                Console.WriteLine(string.Format("      IF {0} alt {1} eps {2} class={3:X2}/{4:X2}/{5:X2} iStr={6}",
                    d[i + 2], d[i + 3], d[i + 4], d[i + 5], d[i + 6], d[i + 7], d[i + 8]));
            else if (bt == 0x05 && bl >= 7)
                Console.WriteLine(string.Format("      EP 0x{0:X2} attr=0x{1:X2} max={2} interval={3}",
                    d[i + 2], d[i + 3], d[i + 4] | (d[i + 5] << 8), d[i + 6]));
            else if (bt == 0x21)
            {
                Console.WriteLine("      DFU FUNCTIONAL: " + Hex(Slice(d, i, bl)));
                if (bl >= 7)
                    Console.WriteLine(string.Format("        bmAttributes=0x{0:X2} detachTimeout={1} transferSize={2} bcdDFU=0x{3:X4}",
                        d[i + 2], d[i + 3] | (d[i + 4] << 8), d[i + 5] | (d[i + 6] << 8),
                        bl >= 9 ? (d[i + 7] | (d[i + 8] << 8)) : -1));
            }
            else
                Console.WriteLine(string.Format("      desc type=0x{0:X2} len={1}: {2}", bt, bl, Hex(Slice(d, i, bl))));
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
        string[] paths = (new string(buf)).Split('\0');
        bool found = false;
        foreach (string p in paths)
        {
            if (p == null || p.Length == 0) continue;
            IntPtr h = OpenHub(p);
            if (h == new IntPtr(-1)) continue;
            for (int port = 1; port <= 15; port++)
            {
                byte[] dd;
                int err;
                if (!GetDescriptor(h, port, 1, 0, 0, 18, out dd, out err) || dd == null || dd.Length < 18)
                    continue;
                if (dd[0] != 18 || dd[1] != 1) continue;
                ushort vid = BitConverter.ToUInt16(dd, 8);
                ushort pid = BitConverter.ToUInt16(dd, 10);
                Console.WriteLine(string.Format("HUB {0} PORT {1}: VID={2:X4} PID={3:X4}", p, port, vid, pid));
                Console.WriteLine("  device: " + Hex(dd));
                Console.WriteLine(string.Format("  bcdUSB=0x{0:X4} class={1:X2}/{2:X2}/{3:X2} ep0={4} bcdDev=0x{5:X4} iMfr={6} iProd={7} iSer={8} cfgs={9}",
                    BitConverter.ToUInt16(dd, 2), dd[4], dd[5], dd[6], dd[7], BitConverter.ToUInt16(dd, 12), dd[13], dd[14], dd[15], dd[16]));
                byte[] cfg;
                if (GetDescriptor(h, port, 2, 0, 0, 0x1000, out cfg, out err) && cfg != null)
                    DumpConfig(cfg);
                else
                    Console.WriteLine("  config failed, win32=" + err);
                byte[] s0;
                ushort lang = 0x0409;
                if (GetDescriptor(h, port, 3, 0, 0, 255, out s0, out err) && s0 != null && s0.Length >= 4)
                    lang = BitConverter.ToUInt16(s0, 2);
                Console.WriteLine(string.Format("  LANGID=0x{0:X4}", lang));
                for (int si = 1; si <= 8; si++)
                {
                    byte[] s;
                    if (GetDescriptor(h, port, 3, (ushort)si, lang, 255, out s, out err) && s != null && s.Length > 2)
                    {
                        int l = s[0];
                        if (l > s.Length) l = s.Length;
                        Console.WriteLine(string.Format("  string[{0}] = \"{1}\"", si,
                            Encoding.Unicode.GetString(s, 2, Math.Max(0, l - 2)).TrimEnd('\0')));
                    }
                }
                if (vid == 0xFFFF && pid == 0xFFFE) found = true;
            }
            CloseHandle(h);
        }
        if (!found) Console.WriteLine("VID_FFFF/PID_FFFE not found");
    }
}
