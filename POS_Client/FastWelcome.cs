using System;
using System.Drawing;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Windows.Forms;

namespace FastWelcome
{
    static class Program
    {
        static void Main(string[] args)
        {
            // 防撞鎖 (Mutex) - 確保同一時間只有一個歡迎畫面
            bool createdNew;
            using (Mutex mutex = new Mutex(true, "FastWelcome_Mutex", out createdNew))
            {
                if (!createdNew)
                {
                    Console.WriteLine("[FastWelcome] Another instance is already running. Exiting.");
                    Environment.Exit(1);
                }

                if (args.Length < 2)
                {
                    Console.WriteLine("[FastWelcome] Usage: FastWelcome.exe <Base64Text> <AudioFilePath>");
                    Environment.Exit(1);
                }

                string base64Text = args[0];
                string audioFile = args[1];
                string decodedText = "";

                try
                {
                    byte[] data = Convert.FromBase64String(base64Text);
                    decodedText = Encoding.UTF8.GetString(data);
                }
                catch
                {
                    decodedText = "家人... 歡迎回家";
                }

                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);
                
                Console.WriteLine("[FastWelcome] Launching UI for: " + decodedText.Replace("\n", " "));
                Application.Run(new WelcomeForm(decodedText, audioFile));
            }
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

            // Form Settings
            this.FormBorderStyle = FormBorderStyle.None;
            this.BackColor = Color.Black;
            this.Opacity = 0.85;
            this.TopMost = true;
            this.ShowInTaskbar = false;
            this.WindowState = FormWindowState.Maximized;

            // Label Settings
            Label label = new Label();
            label.Text = text;
            label.ForeColor = Color.White;
            label.Font = new Font("Microsoft JhengHei", 120, FontStyle.Bold); // 微軟正黑體
            label.Dock = DockStyle.Fill;
            label.TextAlign = ContentAlignment.MiddleCenter;
            this.Controls.Add(label);

            // Safety Timer (25 seconds absolute timeout)
            safetyTimer = new System.Windows.Forms.Timer();
            safetyTimer.Interval = 25000;
            safetyTimer.Tick += new EventHandler(SafetyTimeout);

            // Polling Timer for audio status
            pollTimer = new System.Windows.Forms.Timer();
            pollTimer.Interval = 500;
            pollTimer.Tick += new EventHandler(CheckAudioStatus);

            this.Shown += new EventHandler(OnFormShown);
            this.FormClosed += new FormClosedEventHandler(OnFormClosed);
        }

        private void SafetyTimeout(object sender, EventArgs e)
        {
            Console.WriteLine("[FastWelcome] Safety timeout reached (25s). Force exiting.");
            Environment.Exit(9);
        }

        private void OnFormShown(object sender, EventArgs e)
        {
            safetyTimer.Start();
            
            if (System.IO.File.Exists(audioFile))
            {
                Console.WriteLine("[FastWelcome] Playing audio via WMPlayer.OCX: " + audioFile);
                try
                {
                    Type wmpType = Type.GetTypeFromProgID("WMPlayer.OCX");
                    if (wmpType != null)
                    {
                        wmp = Activator.CreateInstance(wmpType);
                        
                        // wmp.settings.volume = 100
                        object settings = wmpType.InvokeMember("settings", BindingFlags.GetProperty, null, wmp, null);
                        settings.GetType().InvokeMember("volume", BindingFlags.SetProperty, null, settings, new object[] { 100 });
                        
                        // wmp.URL = audioFile
                        wmpType.InvokeMember("URL", BindingFlags.SetProperty, null, wmp, new object[] { audioFile });
                        
                        // wmp.controls.play()
                        object controls = wmpType.InvokeMember("controls", BindingFlags.GetProperty, null, wmp, null);
                        controls.GetType().InvokeMember("play", BindingFlags.InvokeMethod, null, controls, null);
                        
                        pollTimer.Start();
                    }
                    else
                    {
                        Console.WriteLine("[FastWelcome] WMPlayer.OCX not found. Closing in 4s.");
                        FallbackClose();
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine("[FastWelcome] COM Error: " + ex.Message);
                    FallbackClose();
                }
            }
            else
            {
                Console.WriteLine("[FastWelcome] Audio file not found. Waiting 5s then closing.");
                FallbackClose();
            }
        }
        
        private void FallbackClose()
        {
            System.Windows.Forms.Timer fallbackTimer = new System.Windows.Forms.Timer();
            fallbackTimer.Interval = 4000;
            fallbackTimer.Tick += new EventHandler(CloseFormTimer);
            fallbackTimer.Start();
        }

        private void CloseFormTimer(object sender, EventArgs e)
        {
            this.Close();
        }

        private void CheckAudioStatus(object sender, EventArgs e)
        {
            if (wmp != null)
            {
                try
                {
                    int playState = (int)wmp.GetType().InvokeMember("playState", BindingFlags.GetProperty, null, wmp, null);
                    // 3 = Playing, 1 = Stopped
                    if (playState == 3)
                    {
                        startedPlaying = true;
                    }
                    else if (startedPlaying && playState == 1)
                    {
                        pollTimer.Stop();
                        Console.WriteLine("[FastWelcome] Audio finished. Closing UI.");
                        this.Close();
                    }
                }
                catch {}
            }
        }

        private void OnFormClosed(object sender, FormClosedEventArgs e)
        {
            Console.WriteLine("[FastWelcome] Form closed successfully.");
            Environment.Exit(0);
        }
    }
}
