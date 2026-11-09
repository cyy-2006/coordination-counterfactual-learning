param(
    [string]$OutputPath = "C:\Users\pyke\Desktop\上交\local_runs\datasets\generated\two_arm_threading.hdf5"
)

$ErrorActionPreference = "Stop"
$url = "https://hf-mirror.com/datasets/MimicGen/dexmimicgen_datasets/resolve/main/generated/two_arm_threading.hdf5"
$expectedSize = 3913396274
$expectedSha256 = "83ffc06f7bf2d11e83295252d7ec2b1ae50e93c96b12d0739078a371f3875b08"
$fullOutput = [System.IO.Path]::GetFullPath($OutputPath)
$partPath = "$fullOutput.download"
$parent = Split-Path -Parent $fullOutput
New-Item -ItemType Directory -Force -Path $parent | Out-Null

function Test-DatasetFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    if ((Get-Item -LiteralPath $Path).Length -ne $expectedSize) { return $false }
    $hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    return $hash -eq $expectedSha256
}

if (Test-DatasetFile $fullOutput) {
    Write-Output "Dataset is already complete and checksum-valid: $fullOutput"
    exit 0
}

if ((Test-Path -LiteralPath $partPath) -and (Get-Item -LiteralPath $partPath).Length -gt $expectedSize) {
    Remove-Item -LiteralPath $partPath -Force
}

if (-not (Test-DatasetFile $partPath)) {
    & curl.exe -L --fail --retry 8 --retry-delay 5 --continue-at - --output $partPath $url
    if ($LASTEXITCODE -ne 0) { throw "curl failed with exit code $LASTEXITCODE" }
}

if (-not (Test-DatasetFile $partPath)) {
    $actualSize = (Get-Item -LiteralPath $partPath).Length
    throw "Download failed verification (size=$actualSize). Delete the .download file and retry from scratch."
}

if (Test-Path -LiteralPath $fullOutput) {
    Remove-Item -LiteralPath $fullOutput -Force
}
Move-Item -LiteralPath $partPath -Destination $fullOutput
Write-Output "Verified dataset saved to: $fullOutput"
