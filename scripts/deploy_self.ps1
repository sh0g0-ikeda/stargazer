param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectId,

  [string]$Region = "asia-northeast1",

  [string]$Service = "castorops",

  [string]$TargetProjectId = "demo-gcp-project"
)

$ErrorActionPreference = "Stop"

gcloud builds submit `
  --project $ProjectId `
  --config pipelines/deploy-self.cloudbuild.yaml `
  --substitutions "_REGION=$Region,_SERVICE=$Service,_TARGET_PROJECT_ID=$TargetProjectId" `
  .
