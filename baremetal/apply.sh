#!/bin/bash
# apply.sh -- land the bare-metal GRUB entry. Idempotent, re-run safe.
# Usage: sudo bash apply.sh [ROOT_UUID=...] [ESP_UUID=...]
# Auto-detects / and /boot/efi UUIDs; overrides win on conflict.
set -euo pipefail

for kv in "$@"; do case "$kv" in ROOT_UUID=*|ESP_UUID=*) export "$kv";; esac; done
HERE="$(cd "$(dirname "$0")" && pwd)"
TS="$(date +%Y%m%d-%H%M%S)"

if [ "$(id -u)" -ne 0 ]; then echo "run as root: sudo bash apply.sh" >&2; exit 1; fi

ROOT_UUID="${ROOT_UUID:-$(findmnt -no UUID / 2>/dev/null || true)}"
ESP_UUID="${ESP_UUID:-$(findmnt -no UUID /boot/efi 2>/dev/null || true)}"
[ -n "$ROOT_UUID" ] || { echo "cannot detect / UUID; pass ROOT_UUID=<uuid>" >&2; exit 1; }
[ -n "$ESP_UUID" ] || { echo "cannot detect /boot/efi UUID; pass ESP_UUID=<XXXX-XXXX>" >&2; exit 1; }
echo "ROOT_UUID=$ROOT_UUID ESP_UUID=$ESP_UUID"

cp -a /etc/default/grub "/etc/default/grub.bak-$TS"
cp -a /etc/grub.d/40_custom "/etc/grub.d/40_custom.bak-$TS"
echo "backups: /etc/default/grub.bak-$TS /etc/grub.d/40_custom.bak-$TS"

# Enforce each snippet line: replace if key exists, append if absent.
while IFS= read -r line; do
  case "$line" in ""|\#*) continue;; esac
  key="${line%%=*}"
  if grep -q "^${key}=" /etc/default/grub; then
    sed -i "s|^${key}=.*|${line}|" /etc/default/grub
  else
    printf '%s\n' "$line" >> /etc/default/grub
  fi
done < "$HERE/grub-default-snippet"

sed -e "s/@ROOT_UUID@/$ROOT_UUID/g" -e "s/@ESP_UUID@/$ESP_UUID/g" \
  "$HERE/40_custom.template" > /etc/grub.d/40_custom
chmod +x /etc/grub.d/40_custom

update-grub
grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=ubuntu
# Order ubuntu ahead of Windows Boot Manager, keep Windows entry.
if command -v efibootmgr >/dev/null; then
  UBUNTU_NUM="$(efibootmgr | awk '/ubuntu/ {print $1}' | tr -d 'Boot*' | head -1)"
  WIN_NUM="$(efibootmgr | awk '/Windows Boot Manager/ {print $1}' | tr -d 'Boot*' | head -1)"
  if [ -n "$UBUNTU_NUM" ]; then
    if [ -n "$WIN_NUM" ]; then efibootmgr -o "$UBUNTU_NUM,$WIN_NUM" >/dev/null
    else efibootmgr -o "$UBUNTU_NUM" >/dev/null; fi
    echo "boot order: $(efibootmgr | grep BootOrder)"
  fi
fi
echo "APPLIED. Reboot, pick 'Ubuntu 26.04 bare metal', then run verify.sh."
