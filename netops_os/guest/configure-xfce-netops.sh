#!/bin/sh
set -eu

# Configure a Windows-like XFCE session without replacing Debian's packages.
TARGET_USER="${NETOPS_XFCE_USER:-netops}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6 || true)"
if [ -z "$TARGET_HOME" ]; then
    echo "NetOps XFCE: user not found: $TARGET_USER" >&2
    exit 1
fi

CONFIG_DIR="$TARGET_HOME/.config/xfce4"
SKEL_CONFIG_DIR="/etc/skel/.config/xfce4"
WALLPAPER_DIR="/usr/share/backgrounds/netops"
WALLPAPER="$WALLPAPER_DIR/debian-emerald.svg"
WALLPAPER_URL="${NETOPS_WALLPAPER_URL:-https://www.debian.org/Pics/emerald-fg.svg}"

install -d "$CONFIG_DIR/xfconf/xfce-perchannel-xml" \
    "$SKEL_CONFIG_DIR/xfconf/xfce-perchannel-xml" "$WALLPAPER_DIR"

# Prefer the official artwork already shipped by desktop-base. Download only
# when the package does not expose an Emerald wallpaper in this image.
if [ -f /usr/share/desktop-base/emerald-theme/wallpaper/contents/images/1600x1200.svg ]; then
    cp /usr/share/desktop-base/emerald-theme/wallpaper/contents/images/1600x1200.svg "$WALLPAPER"
elif command -v curl >/dev/null 2>&1; then
    curl --fail --location --silent --show-error --max-time 30 "$WALLPAPER_URL" -o "$WALLPAPER" || true
elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$WALLPAPER" "$WALLPAPER_URL" || true
fi

if [ ! -s "$WALLPAPER" ]; then
    cat > "$WALLPAPER" <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#101c3a"/><stop offset="1" stop-color="#087e92"/></linearGradient></defs>
  <rect width="1920" height="1080" fill="url(#g)"/>
  <circle cx="1520" cy="180" r="320" fill="#44d8dc" opacity=".12"/>
  <circle cx="360" cy="900" r="460" fill="#263f7b" opacity=".30"/>
</svg>
EOF
fi

cat > "$CONFIG_DIR/xfconf/xfce-perchannel-xml/xfce4-panel.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="1"/>
    <property name="panel-1" type="empty">
      <property name="position" type="string" value="p=8;x=0;y=0"/>
      <property name="length" type="uint" value="100"/>
      <property name="size" type="uint" value="44"/>
      <property name="mode" type="uint" value="0"/>
      <property name="autohide-behavior" type="uint" value="0"/>
      <property name="icon-size" type="uint" value="24"/>
      <property name="background-style" type="uint" value="0"/>
      <property name="plugin-ids" type="array">
        <value type="int" value="1"/>
        <value type="int" value="2"/>
        <value type="int" value="3"/>
        <value type="int" value="4"/>
        <value type="int" value="5"/>
        <value type="int" value="6"/>
        <value type="int" value="7"/>
        <value type="int" value="8"/>
        <value type="int" value="9"/>
      </property>
    </property>
  </property>
  <property name="plugins" type="empty">
    <property name="plugin-1" type="string" value="whiskermenu"/>
    <property name="plugin-2" type="string" value="separator"/>
    <property name="plugin-3" type="string" value="tasklist"/>
    <property name="plugin-4" type="string" value="separator"/>
    <property name="plugin-5" type="string" value="systray"/>
    <property name="plugin-6" type="string" value="pulseaudio"/>
    <property name="plugin-7" type="string" value="power-manager-plugin"/>
    <property name="plugin-8" type="string" value="clock"/>
    <property name="plugin-9" type="string" value="showdesktop"/>
  </property>
</channel>
EOF

cat > "$CONFIG_DIR/xfconf/xfce-perchannel-xml/xfwm4.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="button_layout" type="string" value="O|HMC"/>
    <property name="theme" type="string" value="Default"/>
  </property>
</channel>
EOF

cat > "$CONFIG_DIR/xfconf/xfce-perchannel-xml/xfce4-desktop.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="$WALLPAPER"/>
          <property name="image-style" type="int" value="5"/>
          <property name="color-style" type="int" value="0"/>
        </property>
      </property>
    </property>
  </property>
</channel>
EOF

cat > "$CONFIG_DIR/xfconf/xfce-perchannel-xml/xsettings.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xsettings" version="1.0">
  <property name="Net" type="empty">
    <property name="ThemeName" type="string" value="Greybird"/>
    <property name="IconThemeName" type="string" value="elementary-xfce"/>
  </property>
  <property name="Gtk" type="empty">
    <property name="FontName" type="string" value="Noto Sans 10"/>
    <property name="MenuImages" type="bool" value="true"/>
    <property name="ButtonImages" type="bool" value="true"/>
  </property>
</channel>
EOF

cp -a "$CONFIG_DIR/." "$SKEL_CONFIG_DIR/"
chown -R "$TARGET_USER:$TARGET_USER" "$CONFIG_DIR"
echo "NetOps XFCE: Windows-like panel, Emerald wallpaper and window controls configured."
