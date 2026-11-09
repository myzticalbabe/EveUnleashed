# elevated_recover.ps1 -- rebuild the wiped GRUB menu from the Windows side.
# READ-ONLY everywhere except one file: S:\EFI\ubuntu\grub.cfg (backed up first).
# Run: powershell -Verb RunAs -File elevated_recover.ps1  (approve the UAC prompt)
# Report: C:\Azazael\EveUnleashed\baremetal\elevated_recover_report.txt
$ErrorActionPreference = 'Stop'
$Report = 'C:\Azazael\EveUnleashed\baremetal\elevated_recover_report.txt'
"== elevated recover $(Get-Date -Format o) ==" | Out-File $Report -Encoding utf8

try {
  $esp = Get-Partition -DiskNumber 0 -PartitionNumber 1
  $esp | Set-Partition -NewDriveLetter S
  "mounted ESP p1 as S:" | Out-File $Report -Append -Encoding utf8

  if (-not (Test-Path 'S:\EFI\ubuntu\grubx64.efi')) { throw 'EFI\ubuntu\grubx64.efi MISSING, aborting (deeper wipe than menu)' }
  if (-not (Test-Path 'S:\EFI\ubuntu\shimx64.efi')) { throw 'EFI\ubuntu\shimx64.efi MISSING, aborting' }
  'grubx64.efi + shimx64.efi present' | Out-File $Report -Append -Encoding utf8

  # Guid stringifies WITH braces; Linux PARTUUID takes none. Strip them.
  $guid = ((Get-Partition -DiskNumber 0 -PartitionNumber 8).Guid).ToString().ToLower().Trim('{}')
  "p8 PARTUUID=$guid" | Out-File $Report -Append -Encoding utf8

  $TS = Get-Date -Format 'yyyyMMdd-HHmmss'
  Copy-Item 'S:\EFI\ubuntu\grub.cfg' "S:\EFI\ubuntu\grub.cfg.bak-$TS"
  "backup: EFI\ubuntu\grub.cfg.bak-$TS" | Out-File $Report -Append -Encoding utf8

  $grub = @"
# recovery written $TS by elevated_recover.ps1; original is grub.cfg.bak-$TS
set timeout=10
set default=0
insmod part_gpt
insmod ext2
insmod gzio

menuentry 'Ubuntu 26.04 bare metal (recovered)' {
    search --no-floppy --file /boot/vmlinuz --set=root
    linux /boot/vmlinuz root=PARTUUID=$guid ro quiet splash mem_sleep_default=deep
    initrd /boot/initrd.img
}
menuentry 'Ubuntu 26.04 fallback (device path)' {
    search --no-floppy --file /boot/vmlinuz --set=root
    linux /boot/vmlinuz root=/dev/nvme0n1p8 ro nomodeset i915.force_probe=!7d51 xe.force_probe=7d51
    initrd /boot/initrd.img
}
menuentry 'Windows 11' {
    search --no-floppy --file /EFI/Microsoft/Boot/bootmgfw.efi --set=root
    chainloader /EFI/Microsoft/Boot/bootmgfw.efi
}
"@
  $grub | Out-File 'S:\EFI\ubuntu\grub.cfg' -Encoding ascii
  'wrote new EFI\ubuntu\grub.cfg' | Out-File $Report -Append -Encoding utf8

  Get-ChildItem 'S:\EFI\ubuntu' | Select-Object Name, Length | Out-File $Report -Append -Encoding utf8
  Get-Content 'S:\EFI\ubuntu\grub.cfg' | Out-File $Report -Append -Encoding utf8
}
catch {
  "FAILED: $($_.Exception.Message)" | Out-File $Report -Append -Encoding utf8
}
finally {
  Remove-PartitionAccessPath -DiskNumber 0 -PartitionNumber 1 -AccessPath 'S:\' -ErrorAction SilentlyContinue
  'unmounted S:' | Out-File $Report -Append -Encoding utf8
  'DONE' | Out-File $Report -Append -Encoding utf8
}
