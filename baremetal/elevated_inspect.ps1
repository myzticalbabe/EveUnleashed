# elevated_inspect.ps1 -- READ-ONLY elevated inspection. Writes nothing but the report.
# Run: powershell -Verb RunAs -File elevated_inspect.ps1  (approve the UAC prompt)
# Report: C:\Azazael\EveUnleashed\baremetal\elevated_report.txt
$ErrorActionPreference = 'Continue'
$Report = 'C:\Azazael\EveUnleashed\baremetal\elevated_report.txt'
"== elevated inspection $(Get-Date -Format o) ==" | Out-File $Report -Encoding utf8

"`n--- bcdedit /enum firmware ---" | Out-File $Report -Append -Encoding utf8
bcdedit /enum firmware 2>&1 | Out-File $Report -Append -Encoding utf8

"`n--- ESP partitions on disk 0 ---" | Out-File $Report -Append -Encoding utf8
Get-Partition -DiskNumber 0 | Where-Object { $_.Type -eq 'System' } |
  Format-Table PartitionNumber, DriveLetter, @{n='SizeMB';e={[int]($_.Size/1MB)}} -AutoSize |
  Out-File $Report -Append -Encoding utf8

$letters = @('S','T')
$i = 0
foreach ($p in (Get-Partition -DiskNumber 0 | Where-Object { $_.Type -eq 'System' -and -not $_.DriveLetter })) {
  $L = $letters[$i]; $i++
  if (-not $L) { continue }
  $p | Set-Partition -NewDriveLetter $L
  "`n--- EFI tree on ESP (was partition $($p.PartitionNumber), now ${L}:) ---" | Out-File $Report -Append -Encoding utf8
  Get-ChildItem "${L}:\EFI" -Recurse -ErrorAction SilentlyContinue |
    Select-Object FullName, Length | Out-File $Report -Append -Encoding utf8
  Remove-PartitionAccessPath -DiskNumber 0 -PartitionNumber $p.PartitionNumber -AccessPath "${L}:\" 
  "`n--- unmounted ${L}: again ---" | Out-File $Report -Append -Encoding utf8
}
"`nDONE" | Out-File $Report -Append -Encoding utf8
