using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using System.IO;

namespace FastWelcome
{
    public static class Program
    {
        public static void Log(string msg) { File.AppendAllText(@"C:\Users\magic\WelcomeAPI\fw_log.txt", DateTime.Now.ToString("HH:mm:ss.fff") + " " + msg + Environment.NewLine); }
        
        [STAThread]
        static void Main(string[] args)
        {
            Log("=== Starting FastWelcome (STAThread) ===");
            bool createdNew;
            using (Mutex mutex = new Mutex(true, "FastWelcome_Mutex", out createdNew))
            {
                if (!createdNew)
                {
                    Log("Mutex blocked.");
                    Environment.Exit(1);
                }

                if (args.Length < 2)
                {
                    Log("Missing args: " + args.Length);
                    Environment.Exit(1);
                }

                string base64Text = args[0];
                string audioFile = args[1];
                string decodedText = "";
                Log("Arg0: " + base64Text);
                Log("Arg1: " + audioFile);

                try
                {
                    byte[] data = Convert.FromBase64String(base64Text);
                    decodedText = Encoding.UTF8.GetString(data);
                }
                catch (Exception e)
                {
                    Log("Base64 error: " + e.Message);
                    decodedText = "家人... 歡迎回家";
                }
                
                Log("Decoded text: " + decodedText);
                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);
                Application.Run(new WelcomeForm(decodedText, audioFile));
            }
        }
    }

    public class SystemAudio
    {
        [DllImport("winmm.dll")]
        public static extern int waveOutSetVolume(IntPtr hwo, uint dwVolume);

        public static void ForceVolumeMax()
        {
            try { waveOutSetVolume(IntPtr.Zero, 0xFFFFFFFF); } catch {}
        }
    }

    public class WelcomeForm : Form
    {
        private string audioFile;
        private System.Windows.Forms.Timer safetyTimer;
        private System.Windows.Forms.Timer pollTimer;
        private object wmp;
        private bool startedPlaying = false;

        public WelcomeForm(string text, string audioPath)
        {
            this.audioFile = audioPath;
            this.FormBorderStyle = FormBorderStyle.None;
            this.BackColor = Color.Black;
            this.Opacity = 0.85;
            this.TopMost = true;
            this.ShowInTaskbar = false;
            this.WindowState = FormWindowState.Maximized;

            Label label = new Label();
            label.Text = text;
            label.ForeColor = Color.White;
            label.Font = new Font("Microsoft JhengHei", 120, FontStyle.Bold);
            label.Dock = DockStyle.Fill;
            label.TextAlign = ContentAlignment.MiddleCenter;
            this.Controls.Add(label);

            safetyTimer = new System.Windows.Forms.Timer();
            safetyTimer.Interval = 25000;
            safetyTimer.Tick += new EventHandler(SafetyTimeout);

            pollTimer = new System.Windows.Forms.Timer();
            pollTimer.Interval = 500;
            pollTimer.Tick += new EventHandler(CheckAudioStatus);

            this.Shown += new EventHandler(OnFormShown);
            this.FormClosed += new FormClosedEventHandler(OnFormClosed);
        }

        protected override void SetVisibleCore(bool value) { base.SetVisibleCore(true); }

        private void SafetyTimeout(object sender, EventArgs e)
        {
            Program.Log("Safety timeout reached (25s).");
            Environment.Exit(9);
        }

        private void OnFormShown(object sender, EventArgs e)
        {
            safetyTimer.Start();
            SystemAudio.ForceVolumeMax();

            Program.Log("Checking if audio file exists: " + audioFile);
            if (System.IO.File.Exists(audioFile))
            {
                Program.Log("File EXISTS. Init WMPlayer.OCX");
                try
                {
                    Type wmpType = Type.GetTypeFromProgID("WMPlayer.OCX");
                    if (wmpType != null)
                    {
                        Program.Log("WMPlayer COM Type found.");
                        wmp = Activator.CreateInstance(wmpType);
                        Program.Log("WMPlayer instance created.");
                        object settings = wmpType.InvokeMember("settings", BindingFlags.GetProperty, null, wmp, null);
                        settings.GetType().InvokeMember("volume", BindingFlags.SetProperty, null, settings, new object[] { 100 });
                        wmpType.InvokeMember("URL", BindingFlags.SetProperty, null, wmp, new object[] { audioFile });
                        object controls = wmpType.InvokeMember("controls", BindingFlags.GetProperty, null, wmp, null);
                        controls.GetType().InvokeMember("play", BindingFlags.InvokeMethod, null, controls, null);
                        Program.Log("Play commanded. Starting pollTimer.");
                        pollTimer.Start();
                    }
                    else
                    {
                        Program.Log("WMPlayer.OCX Type == null.");
                        FallbackClose();
                    }
                }
                catch (Exception ex)
                {
                    Program.Log("COM Exception: " + ex.ToString());
                    FallbackClose();
                }
            }
            else
            {
                Program.Log("File.Exists returned FALSE!");
                FallbackClose();
            }
        }

        private void FallbackClose()
        {
            Program.Log("FallbackClose initiated (4s wait).");
            System.Windows.Forms.Timer fallbackTimer = new System.Windows.Forms.Timer();
            fallbackTimer.Interval = 4000;
            fallbackTimer.Tick += new EventHandler(CloseFormTimer);
            fallbackTimer.Start();
        }

        private void CloseFormTimer(object sender, EventArgs e) { this.Close(); }

        private void CheckAudioStatus(object sender, EventArgs e)
        {
            if (wmp != null)
            {
                try
                {
                    int playState = (int)wmp.GetType().InvokeMember("playState", BindingFlags.GetProperty, null, wmp, null);
                    if (playState == 3) { if(!startedPlaying) { Program.Log("playState == 3 (Playing)"); } startedPlaying = true; }
                    else if (startedPlaying && playState == 1)
                    {
                        Program.Log("playState == 1 (Stopped). Closing.");
                        pollTimer.Stop();
                        this.Close();
                    }
                }
                catch (Exception ex) { Program.Log("CheckAudioStatus error: " + ex.Message); }
            }
        }

        private void OnFormClosed(object sender, FormClosedEventArgs e)
        {
            Program.Log("FormClosed event fired. Clean exit.");
            Environment.Exit(0);
        }
    }
}
