param(
    [string]$ProjectId,
    [string]$Region = "us-central1",
    [string]$ServiceName = "boq-auto-api",
    [string]$Repository = "boq-auto",
    [string]$ImageName = "boq-auto-api",
    [string]$ServiceAccount = "",
    [string]$BucketName = "",
    [string]$DatabaseGcsUri = "",
    [string]$DatabaseSidecarGcsUri = "",
    [string]$CloudSqlConnectionName = "",
    [string]$DbName = "",
    [string]$DbUser = "",
    [string]$DbPasswordSecret = ""
)

$ErrorActionPreference = "Stop"

if (-not $ProjectId) {
    throw "ProjectId is required."
}

$ImageUri = "$Region-docker.pkg.dev/$ProjectId/$Repository/$ImageName`:latest"

gcloud config set project $ProjectId
gcloud artifacts repositories create $Repository --repository-format=docker --location=$Region 2>$null
gcloud builds submit --config cloudbuild.yaml `
    --substitutions "_SERVICE_NAME=$ServiceName,_REGION=$Region,_IMAGE_URI=$ImageUri"

$updateArgs = @(
    "run", "services", "update", $ServiceName,
    "--region", $Region
)

$hasServiceUpdate = $false
$envVars = @()
if ($BucketName) {
    $envVars += "BOQ_AUTO_GCS_BUCKET=$BucketName"
}
if ($DatabaseGcsUri) {
    $envVars += "BOQ_AUTO_API_DB_GCS_URI=$DatabaseGcsUri"
}
if ($DatabaseSidecarGcsUri) {
    $envVars += "BOQ_AUTO_API_DB_SIDECAR_GCS_URI=$DatabaseSidecarGcsUri"
}
if ($CloudSqlConnectionName) {
    $envVars += "BOQ_AUTO_CLOUD_SQL_CONNECTION_NAME=$CloudSqlConnectionName"
}
if ($DbName) {
    $envVars += "BOQ_AUTO_DB_NAME=$DbName"
}
if ($DbUser) {
    $envVars += "BOQ_AUTO_DB_USER=$DbUser"
}
if ($envVars.Count -gt 0) {
    $updateArgs += @("--update-env-vars", ($envVars -join ","))
    $hasServiceUpdate = $true
}
if ($CloudSqlConnectionName) {
    $updateArgs += @("--add-cloudsql-instances", $CloudSqlConnectionName)
    $hasServiceUpdate = $true
}
if ($ServiceAccount) {
    $updateArgs += @("--service-account", $ServiceAccount)
    $hasServiceUpdate = $true
}
if ($hasServiceUpdate) {
    & gcloud @updateArgs
}
if ($DbPasswordSecret) {
    gcloud run services update $ServiceName `
        --region $Region `
        --update-secrets "BOQ_AUTO_DB_PASSWORD=$DbPasswordSecret:latest"
}

Write-Host "Deployment submitted for service $ServiceName in $Region"
