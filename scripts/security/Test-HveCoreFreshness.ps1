#!/usr/bin/env pwsh
# Copyright (c) Microsoft Corporation.
# SPDX-License-Identifier: MIT
#Requires -Version 7.0

<#
.SYNOPSIS
    Checks the pinned hve-core RPI bootstrap ref and hve-core-derived files against
    the latest upstream release.

.DESCRIPTION
    Resolves the newest non-draft microsoft/hve-core release, compares the pinned
    UPSTREAM_REF in the RPI bootstrap workflow against that release commit, and
    compares each hve-core-derived file's upstream blob SHA at the pinned ref against
    the same upstream path at the latest release. Writes a JSON results file consumed
    by the tracking-issue steps and, when running under GitHub Actions, emits the
    stale item count to GITHUB_OUTPUT.

.PARAMETER ResultsFile
    Output JSON results path. Default: hve-core-freshness-results.json.

.PARAMETER ConfigPreview
    Print configuration and exit without performing checks.

.PARAMETER RepoRoot
    Repository root. Defaults to `git rev-parse --show-toplevel`.

.EXAMPLE
    ./Test-HveCoreFreshness.ps1
    Run all checks and write results to the default path.

.EXAMPLE
    ./Test-HveCoreFreshness.ps1 -ConfigPreview
    Print configuration and exit.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$ResultsFile = 'hve-core-freshness-results.json',

    [Parameter(Mandatory = $false)]
    [switch]$ConfigPreview,

    [Parameter(Mandatory = $false)]
    [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'

# ============================================================
# Constants
# ============================================================
$script:UpstreamRepo = 'microsoft/hve-core'
$script:SetupWorkflow = '.github/workflows/copilot-setup-steps.yml'
$script:IssueMarker = 'automation:hve-core-freshness'
$script:IssueSearch = "in:body $script:IssueMarker is:open"

# These are hve-core-derived modules; the check compares each file's UPSTREAM blob SHA
# at the pinned ref vs the latest release, so local adaptations never cause false drift.
# "drift" means upstream changed the file since the pinned ref and the change should
# be reviewed and ported.
$script:DerivedFiles = @(
    'scripts/security/Modules/SecurityHelpers.psm1'
    'scripts/security/Modules/SecurityClasses.psm1'
    'scripts/linting/Modules/LintingHelpers.psm1'
    'scripts/tests/Mocks/GitMocks.psm1'
    'scripts/lib/Modules/CIHelpers.psm1'
    'scripts/linting/Modules/FrontmatterValidation.psm1'
)

# ============================================================
# Pure helpers
# ============================================================

function Get-PinnedHveCoreRef {
    <#
    .SYNOPSIS
        Extract the pinned hve-core UPSTREAM_REF SHA, release tag, and RPI persona paths
        (umbrella agent and subagents directory) from the RPI bootstrap workflow file.
        Returns null when the file is absent; individual members are null when the
        corresponding key is not present.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Path
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    $content = Get-Content -Path $Path -Raw
    $sha = if ($content -match 'UPSTREAM_REF:\s*([0-9a-fA-F]{7,40})') { $Matches[1] } else { $null }
    $tag = if ($content -match 'hve-core release:\s*(\S+)') { $Matches[1] } else { 'unknown' }
    $umbrella = if ($content -match 'UPSTREAM_UMBRELLA_PATH:\s*(\S+)') { $Matches[1] } else { $null }
    $subagents = if ($content -match 'UPSTREAM_SUBAGENTS_PATH:\s*(\S+)') { $Matches[1] } else { $null }

    return [ordered]@{ Tag = $tag; Sha = $sha; UmbrellaPath = $umbrella; SubagentsPath = $subagents }
}

function Select-LatestRelease {
    <#
    .SYNOPSIS
        Pick the newest non-draft release from a GitHub releases API payload.
        hve-core publishes rolling prereleases and rarely flags a stable one, so
        'releases/latest' lags; the newest non-draft tag is authoritative here.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Releases
    )

    return @($Releases |
            Where-Object { -not $_.draft } |
            Sort-Object { [datetime]$_.created_at } -Descending)[0]
}

function Get-DriftState {
    <#
    .SYNOPSIS
        Classify a derived file's state from its pinned and latest upstream blob SHAs.
        Returns 'missing-upstream', 'drift', or 'current'.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$PinnedUpstreamSha,
        [Parameter(Mandatory = $false)][AllowEmptyString()][string]$LatestUpstreamSha
    )

    $p = $PinnedUpstreamSha.ToLowerInvariant()
    $l = $LatestUpstreamSha.ToLowerInvariant()
    if (-not $l) { return 'missing-upstream' }
    if ($p -ne $l) { return 'drift' }
    return 'current'
}

function Get-HveCoreBlobSha {
    <#
    .SYNOPSIS
        Gets the git blob SHA for a specific path and ref from the remote repository.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Repo,
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Ref
    )

    $out = gh api "repos/$Repo/contents/$Path`?ref=$Ref" --jq '.sha' 2>&1
    if ($LASTEXITCODE -eq 0) { return ("$out").Trim() }

    # A genuine 404 means the file is absent at that ref (a real 'missing-upstream').
    # Any other failure (transient, auth, rate limit) must fail loudly rather than
    # masquerade as drift and file a false tracking issue.
    if ("$out" -match 'HTTP 404|Not Found') { return '' }
    throw "gh api failed for ${Path}@${Ref}: $out"
}

function Get-HveCoreSubagentNames {
    <#
    .SYNOPSIS
        Lists the *.agent.md subagent file names under a directory at a given ref,
        mirroring the RPI bootstrap's discovery filter. Returns an empty array when the
        directory is absent (HTTP 404); any other failure throws so a transient error
        never masquerades as a removed subagent.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Repo,
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Ref
    )

    $out = gh api "repos/$Repo/contents/$Path`?ref=$Ref" --jq '.[] | select(.type=="file") | select(.name | endswith(".agent.md")) | .name' 2>&1
    $text = ($out | Out-String)
    if ($LASTEXITCODE -eq 0) {
        return @($text -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    }
    if ($text -match 'HTTP 404|Not Found') { return @() }
    throw "gh api directory listing failed for ${Path}@${Ref}: $text"
}

function Get-HveCoreFileDrift {
    <#
    .SYNOPSIS
        Compares a single upstream path's blob SHA at the pinned ref against the latest
        release and returns a drift record. Local copies are never consulted, so local
        adaptations cannot cause false drift.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Repo,
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$PinnedRef,
        [Parameter(Mandatory)][string]$LatestRef
    )

    $pinnedUp = Get-HveCoreBlobSha -Repo $Repo -Path $Path -Ref $PinnedRef
    $latestUp = Get-HveCoreBlobSha -Repo $Repo -Path $Path -Ref $LatestRef
    $state = Get-DriftState -PinnedUpstreamSha $pinnedUp -LatestUpstreamSha $latestUp

    return [ordered]@{
        Path              = $Path
        PinnedUpstreamSha = if ($pinnedUp) { $pinnedUp } else { '' }
        LatestUpstreamSha = if ($latestUp) { $latestUp } else { '' }
        Drift             = ($state -ne 'current')
        State             = $state
    }
}

function Get-HveCorePersonaDrift {
    <#
    .SYNOPSIS
        Computes drift for the RPI bootstrap persona files - the umbrella agent plus every
        discovered subagent - between the pinned ref and the latest release. A subagent
        present at only one ref surfaces as drift (added or removed upstream). The pin is
        thus stale only when persona content actually changed, not on every release.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Repo,
        [Parameter(Mandatory)][string]$UmbrellaPath,
        [Parameter(Mandatory)][string]$SubagentsPath,
        [Parameter(Mandatory)][string]$PinnedRef,
        [Parameter(Mandatory)][string]$LatestRef
    )

    $results = @(Get-HveCoreFileDrift -Repo $Repo -Path $UmbrellaPath -PinnedRef $PinnedRef -LatestRef $LatestRef)

    $pinnedNames = Get-HveCoreSubagentNames -Repo $Repo -Path $SubagentsPath -Ref $PinnedRef
    $latestNames = Get-HveCoreSubagentNames -Repo $Repo -Path $SubagentsPath -Ref $LatestRef
    # Wrap each operand in @() so a single-element result (which PowerShell unrolls to a
    # scalar) still unions as an array instead of string-concatenating.
    $allNames = @(@($pinnedNames) + @($latestNames) | Sort-Object -Unique)

    foreach ($name in $allNames) {
        $results += Get-HveCoreFileDrift -Repo $Repo -Path "$SubagentsPath/$name" -PinnedRef $PinnedRef -LatestRef $LatestRef
    }

    return @($results)
}

function Get-HveCoreStateLabel {
    <#
    .SYNOPSIS
        Converts a drift state into a user-friendly label/icon.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$State
    )

    switch ($State) {
        'drift'            { return '⚠️ Upstream advanced' }
        'missing-upstream' { return '❓ Not found at latest release' }
        default            { return '✅ Current' }
    }
}

function Format-HveCoreDriftRow {
    <#
    .SYNOPSIS
        Formats one drift record as a markdown table row: path, short pinned/latest blob
        SHAs, and a status label.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][object]$File
    )

    $status = Get-HveCoreStateLabel -State $File.State
    $pSha = if ($File.PinnedUpstreamSha) { $File.PinnedUpstreamSha.Substring(0, [Math]::Min(7, $File.PinnedUpstreamSha.Length)) } else { '' }
    $lSha = if ($File.LatestUpstreamSha) { $File.LatestUpstreamSha.Substring(0, [Math]::Min(7, $File.LatestUpstreamSha.Length)) } else { '' }
    return "| ``$($File.Path)`` | $pSha | $lSha | $status |"
}

function Format-HveCoreIssueBody {
    <#
    .SYNOPSIS
        Formats the markdown body for the tracking issue.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][object]$Result,
        [Parameter(Mandatory)][string]$RunUrl,
        [Parameter(Mandatory)][string]$CheckDate
    )

    $pin = $Result.Pin
    $files = @($Result.Files)
    $personas = @($pin.Personas | Where-Object { $_ })
    $latestLink = "[$($Result.LatestTag)]($($Result.LatestUrl))"

    $personaDrift = @($personas | Where-Object { $_.Drift }).Count
    $pinStatus = if ($pin.IsStale) { "⚠️ $personaDrift persona file(s) changed" } else { '✅ Current' }

    $personaRows = ($personas | ForEach-Object { Format-HveCoreDriftRow -File $_ }) -join "`n"
    $fileRows = ($files | ForEach-Object { Format-HveCoreDriftRow -File $_ }) -join "`n"

    return @"
## hve-core Upstream Freshness Report

Latest reviewed hve-core release: $latestLink

### RPI Bootstrap Persona

Pinned at $($pin.PinnedTag) via ``UPSTREAM_REF`` in ``$($pin.File)`` — $pinStatus

| Persona file | Pinned Upstream blob | Latest Upstream blob | Status |
|--------------|----------------------|----------------------|--------|
$personaRows

### Derived Files

| File | Pinned Upstream blob | Latest Upstream blob | Status |
|------|----------------------|----------------------|--------|
$fileRows

### How to Refresh

**RPI bootstrap pin** (if persona files changed): in ``$($pin.File)``, set ``UPSTREAM_REF`` to the latest release commit (``$($Result.LatestSha)``) and update the adjacent ``# microsoft/hve-core release:`` comment to ``$($Result.LatestTag)``. On a feature branch, confirm the ``Bootstrap hve-core RPI persona`` step still resolves the umbrella and subagents before merging.

**Derived files** (if drifted): Review the upstream changes and port any relevant ones into the locally-adapted copy; do not blindly overwrite (these files carry intentional local adaptations). Compare link: https://github.com/microsoft/hve-core/compare/$($pin.PinnedTag)...$($Result.LatestTag)

Run ``npm run lint:ps`` and ``npm run test:ps`` after changes.

---
**Workflow Run:** $RunUrl
**Detection Date:** $CheckDate

<!-- $($script:IssueMarker) -->
"@
}

function Format-HveCoreJobSummary {
    <#
    .SYNOPSIS
        Formats the markdown body for the GitHub Actions job summary.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][object]$Result
    )

    $pin = $Result.Pin
    $files = @($Result.Files)
    $personas = @($pin.Personas | Where-Object { $_ })

    $personaDrift = @($personas | Where-Object { $_.Drift }).Count
    $pinStatus = if ($pin.IsStale) { "⚠️ $personaDrift persona file(s) changed" } else { '✅ Current' }
    $fileRows = foreach ($f in $files) {
        $fStatus = Get-HveCoreStateLabel -State $f.State
        "| $($f.Path) | $fStatus |"
    }

    return @"
## hve-core Upstream Freshness

Latest release: $($Result.LatestTag)

**RPI persona pin:** $($pin.PinnedTag) → $($Result.LatestTag) — $pinStatus

| Derived File | Status |
|--------------|--------|
$($fileRows -join "`n")
"@
}

function Get-HveCoreTrackingIssue {
    <#
    .SYNOPSIS
        Retrieves the issue number of an existing open freshness tracking issue.
    #>
    [CmdletBinding()]
    param()

    $n = gh issue list --search $script:IssueSearch --limit 1 --json number --jq '.[0].number // empty'
    if ($LASTEXITCODE -ne 0) { return $null }
    return $(if ($n) { $n.Trim() } else { $null })
}

# ============================================================
# Upstream queries
# ============================================================

function Get-HveCoreReleases {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Repo)

    $raw = gh api "repos/$Repo/releases?per_page=30"
    if ($LASTEXITCODE -ne 0 -or -not $raw) {
        throw "Could not fetch releases for $Repo - freshness check cannot produce reliable results"
    }
    return @($raw | ConvertFrom-Json)
}

function Resolve-HveCoreCommitSha {
    <#
    .SYNOPSIS
        Resolves a ref (tag or SHA) to a full commit SHA in the remote repository.
        Throws when the ref does not resolve, so an invalid tag or pinned ref fails
        loudly instead of silently degrading blob lookups to false drift.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Repo,
        [Parameter(Mandatory)][string]$Ref
    )

    $sha = gh api "repos/$Repo/commits/$Ref" --jq '.sha' 2>&1
    if ($LASTEXITCODE -ne 0 -or -not $sha) {
        throw "Could not resolve ref '$Ref' in ${Repo}: $sha"
    }
    return ("$sha").Trim()
}

# ============================================================
# Orchestration
# ============================================================

function Invoke-HveCoreFreshnessCheck {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$ResultsFile
    )

    Push-Location $RepoRoot
    try {
        $latest = Select-LatestRelease -Releases (Get-HveCoreReleases -Repo $script:UpstreamRepo)
        if (-not $latest) {
            throw "No non-draft releases found for $script:UpstreamRepo"
        }
        $latestTag = $latest.tag_name
        $latestUrl = $latest.html_url

        $latestSha = Resolve-HveCoreCommitSha -Repo $script:UpstreamRepo -Ref $latestTag
        Write-Host "Latest hve-core release: $latestTag ($latestSha)"

        # --- Check 1: RPI bootstrap persona drift ---
        $pinRef = Get-PinnedHveCoreRef -Path $script:SetupWorkflow
        if (-not $pinRef -or -not $pinRef.Sha) {
            throw "Could not extract UPSTREAM_REF from $script:SetupWorkflow"
        }
        if (-not $pinRef.UmbrellaPath -or -not $pinRef.SubagentsPath) {
            throw "Could not extract UPSTREAM_UMBRELLA_PATH/UPSTREAM_SUBAGENTS_PATH from $script:SetupWorkflow"
        }

        # Fail loudly if the pinned ref itself does not resolve upstream; otherwise every
        # blob lookup at that ref 404s and is misreported as drift.
        $null = Resolve-HveCoreCommitSha -Repo $script:UpstreamRepo -Ref $pinRef.Sha

        # The pin governs the RPI persona files, not the whole tree, so treat it as stale
        # only when the umbrella agent or a subagent actually changed between the pinned
        # ref and the latest release - not on every unrelated upstream prerelease.
        $personaResults = Get-HveCorePersonaDrift -Repo $script:UpstreamRepo `
            -UmbrellaPath $pinRef.UmbrellaPath -SubagentsPath $pinRef.SubagentsPath `
            -PinnedRef $pinRef.Sha -LatestRef $latestTag
        $personaDrift = @($personaResults | Where-Object { $_.Drift }).Count
        $pinStale = $personaDrift -gt 0
        $status = if ($pinStale) { 'STALE' } else { 'OK' }
        Write-Host "$status RPI persona pin: $($pinRef.Tag) -> $latestTag ($personaDrift / $($personaResults.Count) persona files changed)"

        $pin = [ordered]@{
            PinnedTag = $pinRef.Tag
            PinnedSha = $pinRef.Sha
            IsStale   = $pinStale
            File      = $script:SetupWorkflow
            Personas  = @($personaResults)
        }

        # --- Check 2: derived file drift ---
        $fileResults = foreach ($path in $script:DerivedFiles) {
            if (-not (Test-Path $path)) {
                throw "Derived file not found locally: $path"
            }

            $r = Get-HveCoreFileDrift -Repo $script:UpstreamRepo -Path $path -PinnedRef $pinRef.Sha -LatestRef $latestTag
            $icon = if ($r.Drift) { 'DRIFT' } else { 'OK' }
            Write-Host "$icon $path : $($r.State)"
            $r
        }
        $fileResults = @($fileResults)

        $driftCount = @($fileResults | Where-Object { $_.Drift }).Count
        $staleCount = $driftCount + $(if ($pinStale) { 1 } else { 0 })
        Write-Host "`nStale: pin=$pinStale drift=$driftCount / $($fileResults.Count) files"

        [ordered]@{
            LatestTag = $latestTag
            LatestUrl = $latestUrl
            LatestSha = $latestSha
            Pin       = $pin
            Files     = $fileResults
        } | ConvertTo-Json -Depth 5 | Set-Content $ResultsFile

        return [ordered]@{ StaleCount = $staleCount; LatestTag = $latestTag }
    }
    finally {
        Pop-Location
    }
}

function Resolve-RepoRoot {
    [CmdletBinding()]
    param([string]$Hint)

    if ($Hint) { return (Resolve-Path $Hint).Path }

    try {
        $root = git rev-parse --show-toplevel 2>$null
        if ($LASTEXITCODE -eq 0 -and $root) { return $root.Trim() }
    }
    catch { Write-Verbose "git rev-parse failed: $_" }

    return (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
}

# ============================================================
# Entry point (skipped when dot-sourced by tests)
# ============================================================

if ($MyInvocation.InvocationName -ne '.') {
    $resolvedRoot = Resolve-RepoRoot -Hint $RepoRoot

    if ($ConfigPreview) {
        Write-Host '=== Configuration Preview ==='
        Write-Host "Upstream Repo  : $script:UpstreamRepo"
        Write-Host "Setup Workflow : $script:SetupWorkflow"
        Write-Host "Results File   : $ResultsFile"
        Write-Host "Repo Root      : $resolvedRoot"
        Write-Host 'Derived Files :'
        $script:DerivedFiles | ForEach-Object { Write-Host "  - $_" }
        exit 0
    }

    foreach ($tool in @('gh', 'git')) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
            Write-Error "Required tool not found: $tool"
            exit 2
        }
    }

    try {
        $outcome = Invoke-HveCoreFreshnessCheck -RepoRoot $resolvedRoot -ResultsFile $ResultsFile
        if ($env:GITHUB_OUTPUT) {
            "stale-count=$($outcome.StaleCount)" >> $env:GITHUB_OUTPUT
        }
        exit 0
    }
    catch {
        Write-Error $_
        exit 2
    }
}
