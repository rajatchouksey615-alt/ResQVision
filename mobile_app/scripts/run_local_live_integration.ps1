[CmdletBinding()]
param(
    [switch]$RotateManagedTestPasswords
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$backendRoot = Join-Path $repositoryRoot 'backend'
$mobileRoot = Join-Path $repositoryRoot 'mobile_app'
$python = Join-Path $backendRoot '.venv\Scripts\python.exe'
$flutter = (Get-Command flutter.bat -ErrorAction Stop).Source
$variableNames = @(
    'RESQVISION_LOCAL_TEST_DATA_OPT_IN',
    'RESQVISION_TEST_API_BASE_URL',
    'RESQVISION_TEST_EMAIL',
    'RESQVISION_TEST_PASSWORD',
    'RESQVISION_TEST_ADMIN_EMAIL',
    'RESQVISION_TEST_ADMIN_PASSWORD',
    'RESQVISION_TEST_POLICE_EMAIL',
    'RESQVISION_TEST_POLICE_PASSWORD',
    'RESQVISION_TEST_HOSPITAL_EMAIL',
    'RESQVISION_TEST_HOSPITAL_PASSWORD'
)
$originalEnvironment = @{}
foreach ($name in $variableNames) {
    $originalEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}

$server = $null
$stdoutPath = Join-Path ([IO.Path]::GetTempPath()) "resqvision-phase5c-$PID.out.log"
$stderrPath = Join-Path ([IO.Path]::GetTempPath()) "resqvision-phase5c-$PID.err.log"

function New-ProcessOnlyPassword {
    $bytes = New-Object byte[] 36
    $random = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($bytes)
        return [Convert]::ToBase64String($bytes)
    }
    finally {
        $random.Dispose()
        [Array]::Clear($bytes, 0, $bytes.Length)
    }
}

function Set-TestAccount {
    param(
        [Parameter(Mandatory = $true)][string]$EmailVariable,
        [Parameter(Mandatory = $true)][string]$PasswordVariable,
        [Parameter(Mandatory = $true)][string]$DefaultEmail
    )

    $email = [Environment]::GetEnvironmentVariable($EmailVariable, 'Process')
    $password = [Environment]::GetEnvironmentVariable($PasswordVariable, 'Process')
    if ([string]::IsNullOrWhiteSpace($email) -and [string]::IsNullOrEmpty($password)) {
        $email = $DefaultEmail
        $password = New-ProcessOnlyPassword
        [Environment]::SetEnvironmentVariable($EmailVariable, $email, 'Process')
        [Environment]::SetEnvironmentVariable($PasswordVariable, $password, 'Process')
    }
    elseif ([string]::IsNullOrWhiteSpace($email) -or [string]::IsNullOrEmpty($password)) {
        throw "Provide both $EmailVariable and $PasswordVariable, or neither; values are not displayed."
    }

    if (-not $email.Trim().ToLowerInvariant().EndsWith('.test')) {
        throw "$EmailVariable must use a reserved .test domain."
    }
}

function Get-AnonymousStatus {
    param([Parameter(Mandatory = $true)][string]$Url)

    $request = [Net.HttpWebRequest]::Create($Url)
    $request.Method = 'GET'
    $request.Timeout = 2000
    try {
        $response = $request.GetResponse()
        try { return [int]$response.StatusCode }
        finally { $response.Dispose() }
    }
    catch [Net.WebException] {
        if ($null -eq $_.Exception.Response) { return 0 }
        try { return [int]$_.Exception.Response.StatusCode }
        finally { $_.Exception.Response.Dispose() }
    }
}

function Invoke-FlutterTest {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    Push-Location $mobileRoot
    try {
        & $flutter --suppress-analytics @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Flutter validation failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

try {
    if ($env:RESQVISION_LOCAL_TEST_DATA_OPT_IN -ne '1') {
        throw 'Set RESQVISION_LOCAL_TEST_DATA_OPT_IN=1 explicitly before running local fixture setup.'
    }
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw 'The repository backend virtualenv was not found at backend\.venv.'
    }

    if ([string]::IsNullOrWhiteSpace($env:RESQVISION_TEST_API_BASE_URL)) {
        $env:RESQVISION_TEST_API_BASE_URL = 'http://127.0.0.1:8001/api/v1/'
    }
    $apiUri = [Uri]$env:RESQVISION_TEST_API_BASE_URL
    $apiAddress = $null
    $isLoopback = $apiUri.Host -eq 'localhost' -or
        ([Net.IPAddress]::TryParse($apiUri.Host, [ref]$apiAddress) -and
            [Net.IPAddress]::IsLoopback($apiAddress))
    if ($apiUri.Scheme -ne 'http' -or -not $isLoopback -or $apiUri.UserInfo) {
        throw 'The live integration runner accepts only a local HTTP API URL; value is not displayed.'
    }
    if ($apiUri.Port -lt 1024 -or $apiUri.Port -gt 65535) {
        throw 'Configure a local API port between 1024 and 65535.'
    }
    $serverPort = $apiUri.Port

    Set-TestAccount 'RESQVISION_TEST_EMAIL' 'RESQVISION_TEST_PASSWORD' 'phase5c.auth@resqvision.test'
    Set-TestAccount 'RESQVISION_TEST_ADMIN_EMAIL' 'RESQVISION_TEST_ADMIN_PASSWORD' 'phase5c.admin@resqvision.test'
    Set-TestAccount 'RESQVISION_TEST_POLICE_EMAIL' 'RESQVISION_TEST_POLICE_PASSWORD' 'phase5c.police@resqvision.test'
    Set-TestAccount 'RESQVISION_TEST_HOSPITAL_EMAIL' 'RESQVISION_TEST_HOSPITAL_PASSWORD' 'phase5c.hospital@resqvision.test'

    $configuredEmails = @(
        $env:RESQVISION_TEST_EMAIL,
        $env:RESQVISION_TEST_ADMIN_EMAIL,
        $env:RESQVISION_TEST_POLICE_EMAIL,
        $env:RESQVISION_TEST_HOSPITAL_EMAIL
    ) | ForEach-Object { $_.Trim().ToLowerInvariant() }
    if (($configuredEmails | Select-Object -Unique).Count -ne 4) {
        throw 'All four local integration identities must be distinct.'
    }

    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $serverPort)
    try {
        $listener.Start()
    }
    catch {
        throw "Local port $serverPort is already in use; the runner will not reuse or stop another process."
    }
    finally {
        $listener.Stop()
    }

    $setupArguments = @('manage.py', 'setup_local_dashboard_test_data')
    if ($RotateManagedTestPasswords) {
        $setupArguments += '--rotate-managed-test-passwords'
    }
    Push-Location $backendRoot
    try {
        & $python @setupArguments
        if ($LASTEXITCODE -ne 0) {
            throw "Local fixture setup failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }

    $server = Start-Process -FilePath $python `
        -ArgumentList @('manage.py', 'runserver', "127.0.0.1:$serverPort", '--noreload') `
        -WorkingDirectory $backendRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -PassThru

    $anonymousUrl = "$($env:RESQVISION_TEST_API_BASE_URL.TrimEnd('/'))/incidents/?limit=1&offset=0"
    $ready = $false
    for ($attempt = 0; $attempt -lt 50; $attempt++) {
        if ($server.HasExited) { break }
        if ((Get-AnonymousStatus -Url $anonymousUrl) -eq 401) {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 300
    }
    if (-not $ready) {
        throw 'The local Django API did not return the expected anonymous 401 response.'
    }

    Write-Host 'Running live dashboard tests against local Django and PostgreSQL.'
    Invoke-FlutterTest @('test', 'test/integration/live_dashboard_test.dart', '--reporter', 'expanded')

    Write-Host 'Waiting for the documented login throttle window before the integration-directory run.'
    Start-Sleep -Seconds 61
    Invoke-FlutterTest @('test', 'test/integration', '--reporter', 'expanded')

    Write-Host 'Waiting for the documented login throttle window before Phase 5B authentication regression.'
    Start-Sleep -Seconds 61
    foreach ($name in @(
        'RESQVISION_TEST_ADMIN_EMAIL', 'RESQVISION_TEST_ADMIN_PASSWORD',
        'RESQVISION_TEST_POLICE_EMAIL', 'RESQVISION_TEST_POLICE_PASSWORD',
        'RESQVISION_TEST_HOSPITAL_EMAIL', 'RESQVISION_TEST_HOSPITAL_PASSWORD'
    )) {
        [Environment]::SetEnvironmentVariable($name, $null, 'Process')
    }
    Invoke-FlutterTest @('test', 'test/integration/live_backend_auth_test.dart', '--reporter', 'expanded')

    Write-Host 'All configured live integration validations completed.'
}
finally {
    if ($null -ne $server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
        $server.WaitForExit()
    }
    foreach ($name in $variableNames) {
        [Environment]::SetEnvironmentVariable($name, $originalEnvironment[$name], 'Process')
    }
    Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
}
