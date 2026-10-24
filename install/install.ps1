# Instala, actualiza (volver a ejecutar) o desinstala JhFastYT. Todo lo variable vive en manifest.json.
# ponytail: URLs "latest" sin sha256; para fijar versiones, poner url versionada + "sha256" en el manifiesto.
param(
    [string]$Repo = "21harley/JhFastYT",
    [string]$Dir = "$env:LOCALAPPDATA\JhFastYT",
    [string]$Manifest = "https://raw.githubusercontent.com/$Repo/main/manifest.json",
    [switch]$NoShortcut,
    [switch]$Uninstall
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$lnk = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\JhFastYT.lnk"

if ($Uninstall) {
    Remove-Item $lnk -ErrorAction SilentlyContinue
    Remove-Item "$Dir\app", "$Dir\tools" -Recurse -Force -ErrorAction SilentlyContinue
    "Desinstalado. Tus datos siguen en $Dir\data"
    return
}

$m = if (Test-Path $Manifest) { Get-Content $Manifest -Raw | ConvertFrom-Json } else { Invoke-RestMethod $Manifest }
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("dd-" + [guid]::NewGuid())
New-Item -ItemType Directory $tmp | Out-Null
try {
    foreach ($c in $m.components.PSObject.Properties) {
        $n, $v = $c.Name, $c.Value
        "Descargando $n..."
        $zip = Join-Path $tmp "$n.zip"
        Invoke-WebRequest $v.url.Replace("{repo}", $Repo) -OutFile $zip
        if ($v.sha256 -and (Get-FileHash $zip).Hash -ne $v.sha256) { throw "sha256 no coincide en $n" }
        $x = Join-Path $tmp $n
        Expand-Archive $zip $x -Force
        $dest = Join-Path $Dir $v.dest
        New-Item -ItemType Directory -Force $dest | Out-Null
        if ($v.files) {
            foreach ($f in $v.files) {
                Get-ChildItem $x -Recurse -Filter $f | Select-Object -First 1 | Copy-Item -Destination $dest -Force
            }
        } else {
            Get-ChildItem $dest | Remove-Item -Recurse -Force
            Get-ChildItem $x | Copy-Item -Destination $dest -Recurse -Force
        }
    }
} finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

if (-not $NoShortcut) {
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
    $s.TargetPath = "$Dir\app\JhFastYT.exe"
    $s.WorkingDirectory = "$Dir\app"
    $s.Save()
}
"Listo: $Dir"
