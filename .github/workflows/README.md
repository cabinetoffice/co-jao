# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automated CI/CD processes.

## Workflows

### 1. Deploy to AWS (`deploy.yml`)

Automatically deploys the application to AWS infrastructure when code is pushed to the main branch.

**Triggers:**
- Push to `main` branch (automatic deployment to dev environment)
- Manual dispatch with custom parameters

**What it does:**
- Builds and pushes Docker images to ECR
- Deploys infrastructure using Terraform
- Updates ECS services with new images
- Uploads deployment logs as artifacts

## Setup Instructions

### Step 1: AWS Credentials

Add the following secrets to your GitHub repository:

1. Go to your repository on GitHub
2. Navigate to **Settings** > **Secrets and variables** > **Actions**
3. Click **"New repository secret"** and add:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key with deployment permissions | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |

### Step 2: AWS Permissions

The AWS credentials should have the following permissions:
- ECR (Elastic Container Registry) - full access
- ECS (Elastic Container Service) - full access
- VPC - read/write access
- IAM - create/manage roles and policies
- S3 - access to Terraform state bucket
- DynamoDB - access to Terraform lock table
- CloudWatch - create/manage log groups
- API Gateway - full access

### Step 3: Environment Protection (Optional)

For production deployments, consider setting up environment protection:

1. Go to **Settings** > **Environments**
2. Click **"New environment"** and name it `production`
3. Configure protection rules:
   - Required reviewers
   - Wait timer
   - Deployment branches (restrict to main)

## Manual Deployment

To manually trigger a deployment:

1. Go to the **Actions** tab in your repository
2. Select **"Deploy to AWS"** workflow
3. Click **"Run workflow"**
4. Configure options:
   - **Environment**: `dev`, `staging`, or `prod`
   - **Image tag**: Docker image tag (default: `latest`)
   - **Skip options**: Choose components to skip if needed

## Monitoring Deployments

### View Deployment Status
- Check the **Actions** tab for real-time status
- Each deployment shows logs for all steps
- Failed deployments will show error details

### Download Logs
- Click on any completed workflow run
- Scroll to **Artifacts** section
- Download `deployment-logs-{run-number}` for debugging

### AWS Console
Monitor deployed resources in AWS Console:
- **ECS**: Check service status and task health
- **ECR**: Verify image pushes
- **CloudWatch**: View application logs
- **API Gateway**: Test API endpoints

## Troubleshooting

### Common Issues

**Authentication Errors**
```
Error: Could not get AWS account ID
```
- Verify AWS secrets are correctly set
- Check AWS credentials have required permissions

**Docker Build Failures**
```
Error: Docker build failed
```
- Check Dockerfile syntax in backend/frontend directories
- Verify all dependencies are properly specified

**Terraform Errors**
```
Error: resource already exists
```
- The deploy script handles most conflicts automatically
- For persistent issues, run manual deployment with `--skip-existing` flag

**ECS Service Update Failures**
```
Error: Failed to update ECS service
```
- Check if ECS cluster and service names match expected values
- Verify ECS services are in a stable state before deployment

### Debug Steps

1. **Check workflow logs**: Look at each step's output in the Actions tab
2. **Download artifacts**: Get detailed deployment logs
3. **Verify AWS resources**: Check AWS Console for resource states
4. **Test locally**: Run `./deploy.sh` locally to isolate issues

## Workflow Configuration

### Environment Variables

The workflow automatically sets these based on trigger type:

| Variable | Auto (push to main) | Manual |
|----------|-------------------|---------|
| Environment | `dev` | User selected |
| Image Tag | `latest` | User specified |
| Skip Backend | `false` | User selected |
| Skip Frontend | `false` | User selected |
| Skip Terraform | `false` | User selected |

### Customization

To modify the workflow behavior, edit `.github/workflows/deploy.yml`:

- Change default AWS region (currently `eu-west-2`)
- Modify Terraform version
- Add additional deployment steps
- Change artifact retention period
- Add notification integrations (Slack, email, etc.)

## Security Best Practices

1. **Limit AWS permissions**: Use least privilege principle
2. **Use environment protection**: Require reviews for production
3. **Rotate credentials**: Regularly update AWS access keys
4. **Monitor deployments**: Set up CloudWatch alarms
5. **Secure secrets**: Never commit AWS credentials to code

## Support

For deployment issues:
1. Check this documentation
2. Review workflow logs in Actions tab
3. Consult AWS documentation for service-specific issues
4. Contact the development team with specific error messages