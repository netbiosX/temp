param (
    [string]$TargetHost = "RemoteHost",           # Target hostname or IP
    [string]$Command = "cmd.exe /c whoami",       # Command to execute
    [string]$Username = "DOMAIN\\Username",       # Domain\Username or local user
    [string]$Password = "YourPassword"            # Password (plaintext)
)

# Convert password to secure string and create PSCredential
$secPassword = ConvertTo-SecureString $Password -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential($Username, $secPassword)

# Execute command remotely using WMI
try {
    Write-Host "[*] Executing '$Command' on $TargetHost..."
    $result = Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList $Command -ComputerName $TargetHost -Credential $cred
    
    if ($result.ReturnValue -eq 0) {
        Write-Host "[+] Command executed successfully. PID: $($result.ProcessId)"
    } else {
        Write-Warning "[-] Command failed. Return code: $($result.ReturnValue)"
    }
}
catch {
    Write-Error "Exception: $_"
}
