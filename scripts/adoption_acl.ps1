param(
    [ValidateSet('private-create','private-apply','private-check','profile-check','parent-check','restore-inheritance','transition-check')]
    [string]$Mode,
    [Parameter(Mandatory=$true)][string]$LiteralPath,
    [switch]$AwaitParent
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
function ReadAcl($path) {
    # Native reads avoid the measured Get-Acl overhead; retain DACL/owner/group semantics.
    if ([System.IO.Directory]::Exists($path)) { return [System.IO.Directory]::GetAccessControl($path) }
    return [System.IO.File]::GetAccessControl($path)
}
function ParentPolicy {
    $parent = [System.IO.Path]::GetDirectoryName($LiteralPath.TrimEnd('\','/'))
    $parentAcl = ReadAcl $parent
    return @{platform='windows';parent_sddl=$parentAcl.GetSecurityDescriptorSddlForm('Access,Owner,Group')}
}
function ApplyAcl($item, $acl) {
    if ($item -is [System.IO.DirectoryInfo]) { [System.IO.Directory]::SetAccessControl($item.FullName, $acl) }
    else { [System.IO.File]::SetAccessControl($item.FullName, $acl) }
}
try {
    if ($AwaitParent -and [Console]::ReadLine() -ne 'ready') { throw 'parent_not_ready' }
    if ($Mode -eq 'private-create') {
        if ([System.IO.Directory]::Exists($LiteralPath) -or [System.IO.File]::Exists($LiteralPath)) { throw 'exists' }
        [void][System.IO.Directory]::CreateDirectory($LiteralPath, (PrivateAcl $true))
    }
    if ($Mode -eq 'parent-check') { ParentPolicy | ConvertTo-Json -Compress; exit 0 }
    $items = New-Object 'System.Collections.Generic.List[System.IO.FileSystemInfo]'
    if ([System.IO.Directory]::Exists($LiteralPath) -or [System.IO.File]::Exists($LiteralPath)) {
        $queue = New-Object 'System.Collections.Generic.Queue[System.IO.FileSystemInfo]'
        if ([System.IO.Directory]::Exists($LiteralPath)) { $queue.Enqueue([System.IO.DirectoryInfo]::new($LiteralPath)) }
        else { $queue.Enqueue([System.IO.FileInfo]::new($LiteralPath)) }
        while ($queue.Count) {
            $item = $queue.Dequeue()
            if (($item.Attributes -band 0x400) -ne 0) { throw 'reparse' }
            # Only readonly, hidden, system, directory, archive, normal, not-content-indexed.
            if (([int]$item.Attributes -band (-bnot 0x20b7)) -ne 0) { throw 'attributes' }
            $items.Add($item)
            if ($items.Count -gt 100001) { throw 'limit' }
            if ($item -is [System.IO.DirectoryInfo]) {
                foreach ($entry in $item.EnumerateFileSystemInfos()) { $queue.Enqueue($entry) }
            }
        }
    }
    foreach ($item in $items) {
        if ($Mode -eq 'private-apply') {
            ApplyAcl $item (PrivateAcl ($item -is [System.IO.DirectoryInfo]))
        } elseif ($Mode -eq 'restore-inheritance') {
            $acl = ReadAcl $item.FullName
            foreach ($rule in @($acl.GetAccessRules($true, $false, $sidType))) {
                [void]$acl.RemoveAccessRuleSpecific($rule)
            }
            $acl.SetAccessRuleProtection($false, $false)
            ApplyAcl $item $acl
        }
        $acl = ReadAcl $item.FullName
        if ($acl.GetOwner($sidType).Value -ne $sid.Value) { throw 'owner' }
        $rules = @($acl.GetAccessRules($true, $true, $sidType))
        if (-not $rules.Count) { throw 'empty_acl' }
        if ($Mode -eq 'transition-check') {
            $private = @($rules | Where-Object { $_.IdentityReference.Value -ne $sid.Value -or
                $_.AccessControlType -ne 'Allow' -or ([int]$_.FileSystemRights -band 0x1f01ff) -ne 0x1f01ff }).Count -eq 0
            $inherited = -not $acl.AreAccessRulesProtected -and @($rules | Where-Object { -not $_.IsInherited }).Count -eq 0
            if (-not ($private -or $inherited)) { throw 'unexpected_acl' }
        }
        foreach ($rule in $rules) {
            if ($Mode -in @('private-create','private-apply','private-check')) {
                if ($rule.IdentityReference.Value -ne $sid.Value -or $rule.AccessControlType -ne 'Allow' -or
                    ([int]$rule.FileSystemRights -band 0x1f01ff) -ne 0x1f01ff) { throw 'not_private' }
            } elseif ($Mode -ne 'transition-check' -and $rule.IsInherited -eq $false) { throw 'custom_acl' }
        }
        if ($Mode -in @('profile-check','restore-inheritance') -and $acl.AreAccessRulesProtected) { throw 'custom_acl' }
        # The Python caller checks file and directory streams before starting this helper.
    }
    if ($Mode -in @('profile-check','restore-inheritance','transition-check')) { ParentPolicy | ConvertTo-Json -Compress }
    else { @{private=$true} | ConvertTo-Json -Compress }
} catch {
    # No path, file content, ACL principal or user data in diagnostics.
    [Console]::Error.WriteLine('unsupported_permissions')
    exit 2
}
