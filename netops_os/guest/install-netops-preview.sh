#!/bin/sh
set -eu
mkdir -p /opt/netops /opt/netops/windows-source /var/lib/netops /etc/netops /etc/profile.d /etc/xdg/autostart /usr/share/applications /usr/share/xsessions /etc/lightdm/lightdm.conf.d
cp /tmp/netops-payload/netops_shell.py /opt/netops/netops_shell.py
cp /tmp/netops-payload/netops_app.py /opt/netops/netops_app.py
cp /tmp/netops-payload/netops-splash.png /opt/netops/netops-splash.png
if [ -d /tmp/netops-payload/netops-app ]; then
    cp -a /tmp/netops-payload/netops-app/. /opt/netops/windows-source/
fi
cp /tmp/netops-payload/axvord-daemon.py /opt/netops/axvord-daemon.py
cp /tmp/netops-payload/netops-system-agent.py /opt/netops/netops-system-agent.py
cp /tmp/netops-payload/netops_remote_agent.py /opt/netops/netops_remote_agent.py
cp /tmp/netops-payload/netopsctl.py /opt/netops/netopsctl.py
cp /tmp/netops-payload/configure-xfce-netops.sh /opt/netops/configure-xfce-netops.sh
cp /tmp/netops-payload/netops-axvord.service /etc/systemd/system/netops-axvord.service
cp /tmp/netops-payload/netops-system-agent.service /etc/systemd/system/netops-system-agent.service
cp /tmp/netops-payload/netops-remote-agent.service /etc/systemd/system/netops-remote-agent.service
cp /tmp/netops-payload/netops-shell.desktop /etc/xdg/autostart/netops-shell.desktop
cp /tmp/netops-payload/netops-shell.desktop /usr/share/applications/netops.desktop
chmod 755 /opt/netops/*.py /opt/netops/configure-xfce-netops.sh
chmod 644 /opt/netops/netops-splash.png /usr/share/applications/netops.desktop
ln -sf /opt/netops/netopsctl.py /usr/local/bin/netopsctl

cat > /etc/netops/os-release <<'EOF'
NAME="NetOps OS"
ID=netops
ID_LIKE=debian
PRETTY_NAME="NetOps OS Preview"
VARIANT="Axvord system edition"
EOF
rm -f /etc/os-release
ln -s /etc/netops/os-release /etc/os-release
cat > /etc/profile.d/netops-system.sh <<'EOF'
export NETOPS_OS=1
export NETOPS_CORE=Axvord
EOF
cat > /etc/issue <<'EOF'
NetOps OS | Axvord system core\n\l
EOF

cat > /usr/share/xsessions/netops.desktop <<'EOF'
[Desktop Entry]
Name=NetOps OS
Comment=NetOps native control center
Exec=/usr/bin/python3 /opt/netops/netops_app.py
TryExec=/usr/bin/python3
Type=Application
DesktopNames=NetOps
EOF

cat > /etc/lightdm/lightdm.conf.d/50-netops.conf <<'EOF'
[Seat:*]
autologin-user=netops
autologin-user-timeout=0
autologin-session=netops
user-session=netops
EOF

# Replace the visible boot text with the NetOps OS splash.
mkdir -p /usr/share/plymouth/themes/netops
cp /tmp/netops-payload/netops-splash.png /usr/share/plymouth/themes/netops/netops-splash.png
cp /tmp/netops-payload/netops.plymouth /usr/share/plymouth/themes/netops/netops.plymouth
cp /tmp/netops-payload/netops.script /usr/share/plymouth/themes/netops/netops.script
update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth /usr/share/plymouth/themes/netops/netops.plymouth 200
update-alternatives --set default.plymouth /usr/share/plymouth/themes/netops/netops.plymouth

# Keep the same visual present even on firmware/GRUB paths where Plymouth
# starts late or is skipped by the virtual display adapter.
mkdir -p /boot/grub
cp /tmp/netops-payload/netops-splash.png /boot/grub/netops-splash.png

cat > /etc/default/grub <<'EOF'
GRUB_DEFAULT=0
GRUB_TIMEOUT=0
GRUB_TIMEOUT_STYLE=hidden
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash loglevel=0 systemd.show_status=false rd.systemd.show_status=false plymouth.ignore-serial-consoles console=tty3"
GRUB_CMDLINE_LINUX=""
GRUB_GFXMODE=1024x768
GRUB_GFXPAYLOAD_LINUX=keep
GRUB_TERMINAL_OUTPUT=gfxterm
GRUB_BACKGROUND=/boot/grub/netops-splash.png
GRUB_DISABLE_RECOVERY=true
GRUB_RECORDFAIL_TIMEOUT=0
EOF
update-grub
if command -v plymouth-set-default-theme >/dev/null 2>&1; then
    plymouth-set-default-theme -R netops || true
else
    update-initramfs -u
fi
systemctl daemon-reload
systemctl enable netops-axvord.service netops-system-agent.service netops-remote-agent.service
systemctl restart netops-axvord.service || true
systemctl restart netops-system-agent.service || true
systemctl restart netops-remote-agent.service || true
NETOPS_XFCE_USER=netops /bin/sh /opt/netops/configure-xfce-netops.sh

# Keep the preview image small without deleting package databases or runtime
# assets. Apt can recreate its lists on the next update.
apt-get clean || true
rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/netops-payload /tmp/netops-payload.tar.gz
