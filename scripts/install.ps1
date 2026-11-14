<#
.SYNOPSIS
  Install the blender-live-rigging skill for one or more agent harnesses.

.DESCRIPTION
  Copies by default because creating symlinks on Windows requires Developer Mode or
  administrator rights. Only ever manages the skill named blender-live-rigging.

.EXAMPLE
  .\scripts\install.ps1 -Agent opencode

.EXAMPLE
  .\scripts\install.ps1 -Agent all -Copy

.EXAMPLE
  .\scripts\install.ps1 -Agent opencode -Uninstall
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("opencode", "claude", "agents", "codex", "gemini", "copilot", "cursor", "all")]
    [string]$Agent,

    [ValidateSet("user", "project")]
    [string]$Scope = "user",

    [string]$Project,

    [switch]$Copy,

    [switch]$Uninstall,

    [switch]$Force
)

$ErrorActionPreference = "Stop"

$SkillName = "blender-live-rigging"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Source = Join-Path $RepoRoot "skills\$SkillName"

if (-not (Test-Path $Source)) {
    throw "skill source missing: $Source"
}

if ($Scope -eq "project") {
    if (-not $Project) { throw "-Scope project requires -Project DIR" }
    if (-not (Test-Path $Project)) { throw "project directory not found: $Project" }
    $Project = (Resolve-Path $Project).Path
}

function Get-Targets([string]$Name) {
    switch ($Name) {
        "opencode" { return @("opencode") }
        "claude" { return @("claude") }
        { $_ -in @("agents", "codex", "gemini", "copilot") } { return @("agents") }
        "cursor" { return @("cursor") }
        "all" { return @("opencode", "claude", "agents", "cursor") }
    }
}

function Get-SkillDir([string]$Name) {
    if ($Scope -eq "project") {
        switch ($Name) {
            "opencode" { return Join-Path $Project ".opencode\skills" }
            "claude" { return Join-Path $Project ".claude\skills" }
            "agents" { return Join-Path $Project ".agents\skills" }
            "cursor" { return Join-Path $Project ".cursor\skills" }
        }
    }
    switch ($Name) {
        "opencode" { return Join-Path $env:USERPROFILE ".config\opencode\skills" }
        "claude" { return Join-Path $env:USERPROFILE ".claude\skills" }
        "agents" { return Join-Path $env:USERPROFILE ".agents\skills" }
        "cursor" { return Join-Path $env:USERPROFILE ".cursor\skills" }
    }
}

function Install-One([string]$Name) {
    $Dir = Get-SkillDir $Name
    $Dest = Join-Path $Dir $SkillName
    New-Item -ItemType Directory -Force -Path $Dir | Out-Null

    if (Test-Path $Dest) {
        $Item = Get-Item $Dest -Force
        if ($Item.LinkType -eq "SymbolicLink" -and $Item.Target -eq $Source) {
            Write-Host "ok        $Dest already points at this repo ($Name)"
            return
        }
        if (-not $Force) {
            throw "$Dest exists and is not a link to this repo; inspect it or re-run with -Force"
        }
        Remove-Item $Dest -Recurse -Force
    }

    if ($Copy) {
        Copy-Item $Source $Dest -Recurse -Force
        Write-Host "installed $SkillName -> $Dir ($Name, copy)"
    }
    else {
        try {
            New-Item -ItemType SymbolicLink -Path $Dest -Target $Source | Out-Null
            Write-Host "installed $SkillName -> $Dir ($Name, symlink)"
        }
        catch {
            Copy-Item $Source $Dest -Recurse -Force
            Write-Host "installed $SkillName -> $Dir ($Name, copy fallback)"
        }
    }
}

function Uninstall-One([string]$Name) {
    $Dir = Get-SkillDir $Name
    $Dest = Join-Path $Dir $SkillName
    if (Test-Path $Dest) {
        Remove-Item $Dest -Recurse -Force
        Write-Host "removed   $Dest ($Name)"
    }
    else {
        Write-Host "absent    $Dest ($Name)"
    }
}

foreach ($Target in Get-Targets $Agent) {
    if ($Uninstall) { Uninstall-One $Target } else { Install-One $Target }
}

if (-not $Uninstall) {
    Write-Host ""
    Write-Host "next: python `"$RepoRoot\scripts\doctor.py`""
}
