param(
    [string]$ProjectId,
    [string]$Region = "us-central1",
    [string]$ServiceName = "boq-auto-api",
    [string]$Repository = "boq-auto",
    [string]$ImageName = "boq-auto-api",
    [string]$BucketName = "",
    [string]$DatabaseGcsUri = "",
    [string]$DatabaseSidecarGcsUri = ""
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
if ($envVars.Count -gt 0) {
    gcloud run services update $ServiceName `
        --region $Region `
        --update-env-vars ($envVars -join ",")
}

Write-Host "Deployment submitted for service $ServiceName in $Region"
