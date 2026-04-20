$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$netconvert = $null
$cmd = Get-Command netconvert -ErrorAction SilentlyContinue
if ($cmd) {
	$netconvert = $cmd.Source
}

if (-not $netconvert) {
	$sumoHome = $env:SUMO_HOME
	if (-not $sumoHome) {
		$sumoHome = [Environment]::GetEnvironmentVariable("SUMO_HOME", "User")
	}
	if (-not $sumoHome) {
		$sumoHome = [Environment]::GetEnvironmentVariable("SUMO_HOME", "Machine")
	}

	if ($sumoHome) {
		$candidate = Join-Path $sumoHome "bin\netconvert.exe"
		if (Test-Path $candidate) {
			$netconvert = $candidate
		}
	}
}

if (-not $netconvert) {
	throw "netconvert not found. Set SUMO_HOME and/or add SUMO bin to PATH."
}

& $netconvert --node-files intersection.nod.xml --edge-files intersection.edg.xml --tls.guess true --output-file intersection.net.xml

Write-Host "Built: $PSScriptRoot\intersection.net.xml"
