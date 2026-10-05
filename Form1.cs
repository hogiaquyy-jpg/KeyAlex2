using Reborn;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Diagnostics;
using System.Drawing;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using static System.Windows.Forms.VisualStyles.VisualStyleElement.StartPanel;

namespace Aimbotxxx
{
    public partial class Form1 : Form
    {
        IntPtr mainHandle;
        public Form1() : this(IntPtr.Zero)
        {
        }

        public Form1(IntPtr handle)
        {
            InitializeComponent();
            mainHandle = handle;
            this.MouseDown += Drag_MouseDown;
            EnableDrag(this);
        }

        [DllImport("user32.dll")]
        private static extern bool ReleaseCapture();

        [DllImport("user32.dll")]
        private static extern IntPtr SendMessage(IntPtr hWnd, int msg, IntPtr wParam, IntPtr lParam);

        private void EnableDrag(Control root)
        {
            foreach (Control child in root.Controls)
            {
                if (child is Guna.UI2.WinForms.Guna2Button
                    || child is Guna.UI2.WinForms.Guna2CircleButton
                    || child is Guna.UI2.WinForms.Guna2TextBox)
                    continue;
                child.MouseDown += Drag_MouseDown;
                if (child.HasChildren)
                    EnableDrag(child);
            }
        }

        private void Drag_MouseDown(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                ReleaseCapture();
                SendMessage(Handle, 161, (IntPtr)2, IntPtr.Zero);
            }
        }

        private void btnCloseLogin_Click(object sender, EventArgs e)
        {
            Application.Exit();
        }

        private void Form1_Load(object sender, EventArgs e)
        {
        }

        private async void guna2Button1_Click(object sender, EventArgs e)
        {
            if (string.IsNullOrWhiteSpace(keytxt.Text))
            {
                statuslabel.Text = "Nhap key truoc!";
                statuslabel.ForeColor = Color.Red;
                return;
            }

            statuslabel.Text = " Loading!!";
            statuslabel.ForeColor = Color.Lime;

            var check = await AlexCheatShop.KeyAPI.CheckKey(keytxt.Text.Trim());
            bool alreadyActivated = false;
            if (!check.valid && IsDeviceNotActive(check.reason))
            {
                // Key dung nhung may nay chua kich hoat -> goi activate roi kiem tra lai
                statuslabel.Text = " Dang kich hoat may...";
                alreadyActivated = await AlexCheatShop.KeyAPI.UseKey(keytxt.Text.Trim());
                if (alreadyActivated)
                    check = await AlexCheatShop.KeyAPI.CheckKey(keytxt.Text.Trim());
            }
            if (!check.valid)
            {
                statuslabel.Text = ToFriendlyReason(check.reason);
                statuslabel.ForeColor = Color.Red;
                return;
            }
            if (!alreadyActivated)
            {
                bool used = await AlexCheatShop.KeyAPI.UseKey(keytxt.Text.Trim());
                if (!used)
                {
                    statuslabel.Text = "Key khong kich hoat duoc!";
                    statuslabel.ForeColor = Color.Red;
                    return;
                }
            }

            MainForm ML = new MainForm();
            ML.Show();
            this.Hide();
        }

        private static bool IsDeviceNotActive(string reason)
        {
            if (string.IsNullOrEmpty(reason))
                return false;
            string r = reason.ToLowerInvariant();
            return r.Contains("device") || r.Contains("activat") || r.Contains("kích hoạt");
        }

        private static string ToFriendlyReason(string reason)
        {
            if (string.IsNullOrEmpty(reason))
                return "Key khong hop le!";
            string r = reason.ToLowerInvariant();
            if (r.Contains("not_found") || r.Contains("khong ton tai") || r.Contains("không tồn tại"))
                return "Key khong ton tai!";
            if (r.Contains("revok") || r.Contains("thu hoi") || r.Contains("thu hồi"))
                return "Key da bi thu hoi!";
            if (r.Contains("expir") || r.Contains("het han") || r.Contains("hết hạn"))
                return "Key da het han!";
            if (r.Contains("max") || r.Contains("het luot") || r.Contains("hết lượt"))
                return "Key da het luot kich hoat!";
            return reason;
        }

        private void guna2PictureBox1_Click(object sender, EventArgs e)
        {
            {
                try
                {
                    // Replace the URL with your Discord invite link
                    string discordLink = "https://discord.com/invite/a48pYPuxUu";

                    // Open the link in the default browser
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = discordLink,
                        UseShellExecute = true // Ensures the default browser is used
                    });
                }
                catch (Exception ex)
                {
                    MessageBox.Show("Error opening Discord link: " + ex.Message);
                }
            }
        }
    }
}
