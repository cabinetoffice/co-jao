# GitHub Actions Deployment Setup Checklist

This checklist helps you set up automated deployment using GitHub Actions for the co-jao project.

## ✅ Prerequisites Checklist

Before setting up GitHub Actions deployment, ensure you have:

- [ ] AWS account with appropriate permissions
- [ ] GitHub repository with admin access
- [ ] Local deployment working with `./deploy.sh`
- [ ] Docker and AWS CLI installed locally (for testing)

## 🔐 Step 1: AWS IAM Setup

### Create Deployment User

1. **Create IAM User:**
   - [ ] Go to AWS Console > IAM > Users
   - [ ] Click "Create user"
   - [ ] Name: `github-actions-deployer`
   - [ ] Select "Programmatic access"

2. **Attach Policies:**
   - [ ] `AmazonEC2ContainerRegistryFullAccess`
   - [ ] `AmazonECS_FullAccess`
   - [ ] `AmazonVPCFullAccess`
   - [ ] `IAMFullAccess`
   - [ ] `AmazonS3FullAccess`
   - [ ] `AmazonDynamoDBFullAccess`
   - [ ] `CloudWatchFullAccess`
   - [ ] `AmazonAPIGatewayAdministrator`

3. **Get Credentials:**
   - [ ] Save Access Key ID
   - [ ] Save Secret Access Key
   - [ ] ⚠️ **IMPORTANT**: Store these securely, you'll need them for GitHub

## 🔑 Step 2: GitHub Secrets Setup

1. **Navigate to Repository Settings:**
   - [ ] Go to your GitHub repository
   - [ ] Click **Settings** tab
   - [ ] Click **Secrets and variables** > **Actions**

2. **Add Required Secrets:**
   - [ ] Click **"New repository secret"**
   - [ ] Add `AWS_ACCESS_KEY_ID` with your Access Key ID
   - [ ] Add `AWS_SECRET_ACCESS_KEY` with your Secret Access Key

## 📁 Step 3: Verify File Structure

Ensure these files exist in your repository:

- [ ] `.github/workflows/deploy.yml` ✅ (Already created)
- [ ] `deploy.sh` ✅ (Already exists)
- [ ] `iac/` directory with Terraform files ✅ (Already exists)
- [ ] `jao-backend/Dockerfile` (for backend)
- [ ] `jao-web/Dockerfile` (for frontend)

## 🧪 Step 4: Test Local Deployment

Before using GitHub Actions, verify local deployment works:

```bash
# Test the deployment script locally
./deploy.sh --help

# Try a test deployment (optional - will deploy to AWS)
./deploy.sh --skip-service-update
```

- [ ] Local deployment script runs without errors
- [ ] AWS credentials work locally
- [ ] Docker images build successfully

## 🚀 Step 5: First GitHub Actions Deployment

### Option A: Automatic (Push to Main)
1. **Push to Main Branch:**
   - [ ] Commit your changes
   - [ ] Push to `main` branch
   - [ ] GitHub Actions will auto-deploy to `dev` environment

### Option B: Manual Deployment
1. **Manual Trigger:**
   - [ ] Go to GitHub repository
   - [ ] Click **Actions** tab
   - [ ] Select **"Deploy to AWS"** workflow
   - [ ] Click **"Run workflow"**
   - [ ] Choose parameters and click **"Run workflow"**

## 📊 Step 6: Monitor Deployment

1. **Watch Progress:**
   - [ ] Go to **Actions** tab
   - [ ] Click on running workflow
   - [ ] Monitor each step's progress

2. **Check Results:**
   - [ ] All steps complete successfully (green checkmarks)
   - [ ] No error messages in logs
   - [ ] AWS resources created/updated successfully

## 🔍 Step 7: Verify Deployment

1. **Check AWS Console:**
   - [ ] ECS services are running
   - [ ] ECR repositories contain new images
   - [ ] API Gateway endpoints are accessible
   - [ ] CloudWatch logs show application activity

2. **Test Application:**
   - [ ] API endpoints respond correctly
   - [ ] Frontend loads successfully
   - [ ] Application functions as expected

## 🛠️ Troubleshooting

### Common Issues & Solutions

**❌ "Could not get AWS account ID"**
- [ ] Verify AWS secrets are correctly set in GitHub
- [ ] Check AWS user has required permissions
- [ ] Ensure no typos in secret names

**❌ "Docker build failed"**
- [ ] Check Dockerfile syntax in backend/frontend
- [ ] Verify all dependencies are available
- [ ] Test Docker build locally first

**❌ "Terraform resource already exists"**
- [ ] Normal for first-time setup
- [ ] Deploy script handles most conflicts automatically
- [ ] Check AWS Console for resource conflicts

**❌ "ECS service update failed"**
- [ ] Verify ECS cluster exists
- [ ] Check service names match expectations
- [ ] Ensure services are in stable state

## 🔄 Ongoing Operations

### Regular Maintenance
- [ ] Monitor deployment logs regularly
- [ ] Rotate AWS credentials periodically
- [ ] Update Terraform version as needed
- [ ] Review and update IAM permissions

### Environment Management
- [ ] Use manual triggers for staging/prod deployments
- [ ] Set up environment protection rules for production
- [ ] Consider separate AWS accounts for different environments

## 📞 Support

If you encounter issues:

1. **Check Documentation:**
   - [ ] Review `.github/workflows/README.md`
   - [ ] Check main README deployment section
   - [ ] Consult AWS documentation

2. **Debug Steps:**
   - [ ] Download deployment artifacts from Actions
   - [ ] Test deployment locally
   - [ ] Check AWS CloudWatch logs

3. **Get Help:**
   - [ ] Share specific error messages
   - [ ] Include workflow run URL
   - [ ] Provide AWS resource details

## ✅ Final Checklist

Before considering setup complete:

- [ ] GitHub Actions workflow runs successfully
- [ ] Application deploys to AWS correctly
- [ ] All services are healthy and accessible
- [ ] Monitoring and logging are working
- [ ] Team knows how to trigger manual deployments
- [ ] Rollback procedures are understood

---

**🎉 Congratulations!** Your GitHub Actions deployment is now set up and ready to use!

**Next Steps:**
- Set up branch protection rules
- Configure environment-specific deployments
- Add monitoring and alerting
- Document rollback procedures