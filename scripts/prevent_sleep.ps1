$signature = @"
[System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
"@

Add-Type -MemberDefinition $signature -Name NativeMethods -Namespace Win32

$ES_CONTINUOUS = [uint32]2147483648
$ES_SYSTEM_REQUIRED = [uint32]1
$ES_DISPLAY_REQUIRED = [uint32]2

try {
    while ($true) {
        $flags = [uint32]($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED -bor $ES_DISPLAY_REQUIRED)
        [void][Win32.NativeMethods]::SetThreadExecutionState($flags)
        Start-Sleep -Seconds 30
    }
}
finally {
    [void][Win32.NativeMethods]::SetThreadExecutionState($ES_CONTINUOUS)
}
