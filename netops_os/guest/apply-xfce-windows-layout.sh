#!/usr/bin/env bash
set -u

# Apply the Windows-like Debian/XFCE layout to the current graphical session.
XFCONF="$(command -v xfconf-query 2>/dev/null || true)"
if [ -z "$XFCONF" ]; then
    printf '%s\n' 'xfconf-query bulunamadı.' >&2
    exit 1
fi

set_property() {
    local channel="$1"
    local property="$2"
    local type="$3"
    local value="$4"
    "$XFCONF" -c "$channel" -p "$property" -n -t "$type" -s "$value" >/dev/null 2>&1 || \
        "$XFCONF" -c "$channel" -p "$property" -s "$value" >/dev/null 2>&1 || true
}

reset_property() {
    "$XFCONF" -c "$1" -p "$2" -r -R >/dev/null 2>&1 || true
}

# Remove the dock and keep one full-width, non-hidden bottom panel.
reset_property xfce4-panel /panels/panel-2
set_property xfce4-panel /panels/panel-1/position string 'p=10;x=0;y=0'
set_property xfce4-panel /panels/panel-1/length uint 100
set_property xfce4-panel /panels/panel-1/autohide-behavior uint 0
set_property xfce4-panel /panels/panel-1/size uint 42

# Use the Debian logo and Turkish start label for the applications menu.
set_property xfce4-panel /plugins/plugin-1/button-icon string 'debian-logo'
set_property xfce4-panel /plugins/plugin-1/button-title string 'Başlat'
set_property xfce4-panel /plugins/plugin-1/show-button-title bool true

BACKGROUND_DIR="$HOME/.local/share/backgrounds"
BACKGROUND="$BACKGROUND_DIR/debian-emerald.svg"
mkdir -p "$BACKGROUND_DIR"

for candidate in \
    /usr/share/desktop-base/emerald-theme/wallpaper/contents/images/1600x1200.svg \
    /usr/share/desktop-base/emerald-theme/wallpaper/contents/images/1920x1080.svg; do
    if [ -s "$candidate" ]; then
        BACKGROUND="$candidate"
        break
    fi
done

if [ "$BACKGROUND" = "$BACKGROUND_DIR/debian-emerald.svg" ] && [ ! -s "$BACKGROUND" ]; then
    WALLPAPER_URL="${NETOPS_WALLPAPER_URL:-https://www.debian.org/Pics/emerald-fg.svg}"
    if command -v curl >/dev/null 2>&1; then
        curl --fail --location --silent --show-error --max-time 30 "$WALLPAPER_URL" -o "$BACKGROUND" || true
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$BACKGROUND" "$WALLPAPER_URL" || true
    fi
fi

if [ -s "$BACKGROUND" ]; then
    set_property xfce4-desktop /backdrop/screen0/monitor0/workspace0/last-image string "$BACKGROUND"
    set_property xfce4-desktop /backdrop/screen0/monitor0/workspace0/image-style int 5
    set_property xfce4-desktop /backdrop/screen0/monitor0/workspace0/color-style int 0

    # Apply the same image to every monitor/workspace exposed by xfconf.
    while IFS= read -r property; do
        case "$property" in
            */last-image)
                set_property xfce4-desktop "$property" string "$BACKGROUND"
                ;;
        esac
    done < <("$XFCONF" -c xfce4-desktop -l 2>/dev/null || true)
fi

xfce4-panel --restart >/dev/null 2>&1 || true
xfdesktop --reload >/dev/null 2>&1 || true

printf '%s\n' 'XFCE Windows düzeni uygulandı.'
