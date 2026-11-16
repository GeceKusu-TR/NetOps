# NetOps OS Preview (NetOps v1.50)

This folder is the isolated operating-system prototype. It does not modify the
host Windows installation. The target is an x86_64 QEMU guest that boots a
Linux base, starts the NetOps shell, and runs Axvord as a local service.

## Host safety

- All disk images stay under `netops_os/artifacts/`.
- The host OS is never repartitioned and no boot entry is changed.
- QEMU is launched with a separate virtual disk and snapshot mode by default.
- NetOps v1.50 uses 1024 MB RAM and 2 vCPUs by default; the launcher clamps
  requests to 512-4096 MB and 1-4 vCPUs.
- The first image is a preview, not a replacement for Windows.

## Boot flow

1. Firmware/GRUB and Plymouth show the NetOps OS splash without Debian text.
2. Linux starts the `netops-axvord` service.
3. The native NetOps Control Center becomes the default graphical session and
   is also registered as the `NetOps` application under `/usr/share/applications`.
4. Axvord runs as a root-owned system service and exposes a named-operation
   bridge to the NetOps session through `/run/netops/agent.sock`.

## System integration

- `netops-axvord.service` is the root-owned local core.
- `netops-system-agent.service` starts at multi-user boot and owns the
  privileged bridge.
- `netopsctl status|start|stop|restart` uses the bridge without exposing an
  arbitrary shell to chat input.
- `netops_shell.py` is the visible NetOps application: a modern operator
  console with Axvord status, system actions, and a controlled restart flow.
- `netops_app.py` is the current native guest application with chat, devices,
  Now Playing, automation, extensions, and settings surfaces.
- The Windows build source and assets are copied to
  `/opt/netops/windows-source`; Windows-only APIs are not executed inside the
  Linux guest.
- `reboot` and `poweroff` remain explicit named operations, not free-form
  command execution.
- `netops-remote-agent.service` exposes the same named operations to a paired
  phone over WebSocket port `8765`; it never accepts an arbitrary shell string.
- The QEMU launcher forwards host port `9876` to guest port `8765`, so Termux
  can pair with `netops pair --host PC_IP:9876 --code KOD`.

## XFCE desktop

- The guest logs the `netops` user directly into XFCE.
- `guest/configure-xfce-netops.sh` creates a repeatable Windows-like bottom
  panel with a Whisker start menu, task buttons, tray, audio, power, clock,
  and show-desktop controls.
- XFWM keeps the window controls on the right (`minimize`, `maximize`,
  `close`) while Debian's Emerald artwork remains the visual identity.
- The script prefers the official `desktop-base` Emerald artwork already in
  the image and downloads a Debian artwork fallback only when needed.
- NetOps remains an XFCE autostart application; the root-owned Axvord bridge
  continues to provide named system operations instead of an unrestricted
  terminal.

## Current state

The first Linux-based NetOps preview image is installed at `C:\NetOpsVM\netops-os.qcow2`.
After changing guest files, rebuild or reinstall the preview image before
expecting the running QCOW2 disk to contain the new XFCE configuration.
The next rebuild applies the video-derived NetOps splash through Plymouth and
keeps the host Windows installation unchanged. WSL is not part of the NetOps
OS path. Use `scripts\run-qemu.ps1` to boot the image. The Windows app also
accepts `sanal masaustu baslat`, `sanal masaustu durumu`, `sanal masaustu
durdur`, and `sanal masaustu yeniden baslat`.

## Remote device commands

After the guest is rebuilt, open the NetOps **Cihazlar** page and copy the
pairing code. From Termux, pair against the host-forwarded port:

```sh
netops pair --host PC_IP:9876 --code KOD --name "Telefonum"
netops agent --background --name "Telefonum"
netops status
netops ram
netops cpu
netops ağ
netops uptime
netops core-restart
netops commands
```

`reboot` and `poweroff` are explicit commands and are not accepted through an
arbitrary shell. The guest must be running with `run-qemu.ps1`; use
`-NoRemotePortForward` only when bridged networking is configured separately.
