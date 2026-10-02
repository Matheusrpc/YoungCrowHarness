param(
    [ValidateSet('private-create','private-apply','private-check','profile-check','parent-check','restore-inheritance')]
    [string]$Mode,
    [Parameter(Mandatory=$true)][string]$LiteralPath
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$sidType = [System.Security.Principal.SecurityIdentifier]
function PrivateAcl($directory) {
    if ($directory) { $acl = New-Object System.Security.AccessControl.DirectorySecurity }
    else { $acl = New-Object System.Security.AccessControl.FileSecurity }
    $acl.SetOwner($sid)
    $acl.SetAccessRuleProtection($true, $false)
    $inheritance = if ($directory) { 'ContainerInherit,ObjectInherit' } else { 'None' }
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($sid, 'FullControl', $inheritance, 'None', 'Allow')
    $acl.AddAccessRule($rule)
    return $acl
}
function ParentPolicy {
    $parent = [System.IO.Path]::GetDirectoryName($LiteralPath.TrimEnd('\','/'))
    $parentAcl = Get-Acl -LiteralPath $parent
    return @{platform='windows';parent_sddl=$parentAcl.GetSecurityDescriptorSddlForm('Access,Owner,Group')}
}
function ApplyAcl($item, $acl) {
    if ($item.PSIsContainer) { [System.IO.Directory]::SetAccessControl($item.FullName, $acl) }
    else { [System.IO.File]::SetAccessControl($item.FullName, $acl) }
}
try {
    if ($Mode -eq 'private-create') {
        if (Test-Path -LiteralPath $LiteralPath) { throw 'exists' }
        [void][System.IO.Directory]::CreateDirectory($LiteralPath, (PrivateAcl $true))
    }
    if ($Mode -eq 'parent-check') { ParentPolicy | ConvertTo-Json -Compress; exit 0 }
    $items = New-Object 'System.Collections.Generic.List[System.IO.FileSystemInfo]'
    if (Test-Path -LiteralPath $LiteralPath) {
        $queue = New-Object 'System.Collections.Generic.Queue[System.IO.FileSystemInfo]'
        $queue.Enqueue((Get-Item -LiteralPath $LiteralPath -Force))
        while ($queue.Count) {
            $item = $queue.Dequeue()
            if (($item.Attributes -band 0x400) -ne 0) { throw 'reparse' }
            # Only readonly, hidden, system, directory, archive, normal, not-content-indexed.
            if (([int]$item.Attributes -band (-bnot 0x20b7)) -ne 0) { throw 'attributes' }
            $items.Add($item)
            if ($items.Count -gt 100001) { throw 'limit' }
            if ($item.PSIsContainer) {
                Get-ChildItem -LiteralPath $item.FullName -Force | ForEach-Object { $queue.Enqueue($_) }
            }
        }
    }
    foreach ($item in $items) {
        if ($Mode -eq 'private-apply') {
            ApplyAcl $item (PrivateAcl $item.PSIsContainer)
        } elseif ($Mode -eq 'restore-inheritance') {
            $acl = Get-Acl -LiteralPath $item.FullName
            foreach ($rule in @($acl.GetAccessRules($true, $false, $sidType))) {
                [void]$acl.RemoveAccessRuleSpecific($rule)
            }
            $acl.SetAccessRuleProtection($false, $false)
            ApplyAcl $item $acl
        }
        $acl = Get-Acl -LiteralPath $item.FullName
        if ($acl.GetOwner($sidType).Value -ne $sid.Value) { throw 'owner' }
        $rules = @($acl.GetAccessRules($true, $true, $sidType))
        if (-not $rules.Count) { throw 'empty_acl' }
        foreach ($rule in $rules) {
            if ($Mode -in @('private-create','private-apply','private-check')) {
                if ($rule.IdentityReference.Value -ne $sid.Value -or $rule.AccessControlType -ne 'Allow' -or
                    ([int]$rule.FileSystemRights -band 0x1f01ff) -ne 0x1f01ff) { throw 'not_private' }
            } elseif ($rule.IsInherited -eq $false) { throw 'custom_acl' }
        }
        if ($Mode -in @('profile-check','restore-inheritance') -and $acl.AreAccessRulesProtected) { throw 'custom_acl' }
        if (-not $item.PSIsContainer) {
            $streams = @(Get-Item -LiteralPath $item.FullName -Stream '*' -ErrorAction Stop)
            if (@($streams | Where-Object { $_.Stream -ne ':$DATA' }).Count) { throw 'ads' }
        }
    }
    if ($Mode -in @('profile-check','restore-inheritance')) { ParentPolicy | ConvertTo-Json -Compress }
    else { @{private=$true} | ConvertTo-Json -Compress }
} catch {
    # No path, file content, ACL principal or user data in diagnostics.
    [Console]::Error.WriteLine('unsupported_permissions')
    exit 2
}
