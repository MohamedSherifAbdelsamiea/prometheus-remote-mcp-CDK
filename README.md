# Prometheus MCP Lambda Server - CDK Deployment

Production-ready Prometheus MCP (Model Context Protocol) server deployed as AWS Lambda with API Gateway and Cognito authentication.

## 🚀 **Quick Deploy**

```bash
# 1. Install dependencies
npm install

# 2. Set AWS profile (replace 'your-profile' with your AWS profile name)
export AWS_PROFILE=your-profile

# 3. Bootstrap CDK (first time only)
cdk bootstrap

# 4. Deploy all stacks
cdk deploy --app 'npx ts-node bin/lambda-app.ts' --all

# 5. Update config with client secret (use same profile)
./scripts/update-mcp-config.sh your-profile

# 6. Test deployment
curl $(jq -r '.endpoint' mcp-server-config.json | sed 's/mcp$/health/')
```

## 📋 **Prerequisites**

- **Node.js 18+** and npm
- **AWS CLI** configured with appropriate permissions
- **CDK CLI** installed: `npm install -g aws-cdk`
- **jq** for JSON processing: `brew install jq` (macOS)
- **AWS Profile** configured with deployment permissions

## 🔧 **Step-by-Step Deployment**

### 1. AWS Profile Configuration

**IMPORTANT**: This project requires an AWS profile to avoid conflicts with existing resources.

```bash
# Configure a new AWS profile (recommended)
aws configure --profile your-profile-name
# Enter your AWS Access Key ID, Secret, Region, and output format

# Or use existing profile
export AWS_PROFILE=your-existing-profile

# Verify profile works
aws sts get-caller-identity --profile your-profile-name
```

**Why profiles matter**: Without specifying a profile, the deployment might conflict with existing Cognito User Pools or other resources in your default AWS account.

### 2. Setup Environment
### 2. Setup Environment
```bash
# Clone/navigate to project
cd lambda-mcp-cdk

# Install dependencies
npm install

# Set AWS profile for this session
export AWS_PROFILE=your-profile-name
```

### 3. Bootstrap CDK (First Time Only)
```bash
# Bootstrap CDK in your AWS account/region
cdk bootstrap

# Verify bootstrap
aws ssm get-parameter --name /cdk-bootstrap/hnb659fds/version
```

### 4. Deploy Infrastructure
```bash
# Deploy all stacks at once
cdk deploy --app 'npx ts-node bin/lambda-app.ts' --all

# OR deploy individually
cdk deploy --app 'npx ts-node bin/lambda-app.ts' PrometheusLambdaMCPCognitoStack
cdk deploy --app 'npx ts-node bin/lambda-app.ts' PrometheusLambdaMCPStack
cdk deploy --app 'npx ts-node bin/lambda-app.ts' PrometheusLambdaMCPAPIGatewayStack
```

### 5. Configure Client Secret
```bash
# Make script executable
chmod +x scripts/update-mcp-config.sh

# Update config with real client secret (use same profile as deployment)
./scripts/update-mcp-config.sh your-profile-name

# Verify config file
cat mcp-server-config.json
```

### 6. Test Deployment
```bash
# Test health endpoint
curl $(jq -r '.endpoint' mcp-server-config.json | sed 's/mcp$/health/')

# Test MCP endpoint (requires token)
CLIENT_ID=$(jq -r '.authorization_configuration.client_id' mcp-server-config.json)
CLIENT_SECRET=$(jq -r '.authorization_configuration.client_secret' mcp-server-config.json)
TOKEN_URL=$(jq -r '.authorization_configuration.exchange_url' mcp-server-config.json)

# Get token
TOKEN=$(curl -s -X POST "$TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&scope=prometheus-mcp-server/read prometheus-mcp-server/write" \
  -u "$CLIENT_ID:$CLIENT_SECRET" | jq -r '.access_token')

# Test MCP tools/list
curl -X POST $(jq -r '.endpoint' mcp-server-config.json) \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

## ⚙️ **Environment Variables**

The CDK deployment supports the following environment variables for customization:

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_PROFILE` | AWS profile to use for deployment | Required |
| `CDK_DEFAULT_REGION` | AWS region for deployment | Required |
| `COGNITO_DOMAIN_PREFIX` | Cognito domain prefix | `prometheus-mcp-{random}` |
| `USER_POOL_NAME` | Cognito User Pool name | `prometheus-mcp-oauth-pool` |
| `RESOURCE_SERVER_ID` | OAuth resource server identifier | `prometheus-mcp-server` |
| `CALLBACK_URL` | OAuth callback URL | `https://localhost:3000/oauth2/idpresponse` |
| `LOGOUT_URL` | OAuth logout URL | `https://localhost:3000/` |
| `OAUTH_SCOPE` | OAuth scopes | `prometheus-mcp-server/read prometheus-mcp-server/write` |

```bash
# Example with custom values
export COGNITO_DOMAIN_PREFIX=my-custom-prefix
export USER_POOL_NAME=my-mcp-pool
cdk deploy --app 'npx ts-node bin/lambda-app.ts' --all
```

## 🎯 **What Gets Deployed**

| Stack | Resources | Purpose |
|-------|-----------|---------|
| **CognitoStack** | User Pool, M2M Client, Domain | OAuth authentication |
| **LambdaStack** | Lambda Function, IAM Role | MCP server with 5 tools |
| **APIGatewayStack** | REST API, JWT Authorizer | HTTP endpoints + config generation |

## 📄 **Generated Files**

- **`mcp-server-config.json`** - Complete MCP client configuration
- **CDK outputs** - All deployment information and ARNs

## 🔧 **Available Commands**

```bash
# Deployment
npm run deploy:lambda          # Deploy all stacks
npm run deploy:lambda:cognito  # Deploy Cognito only
npm run deploy:lambda:function # Deploy Lambda only  
npm run deploy:lambda:api      # Deploy API Gateway only

# Configuration
npm run update-config          # Update config with client secret

# Development
npm run build                  # Compile TypeScript
npm run synth                  # Synthesize CloudFormation
npm run diff                   # Show deployment diff

# Cleanup
npm run destroy                # Destroy all stacks
```

## 🚨 **Troubleshooting**

### Bootstrap Error
```bash
# Error: SSM parameter /cdk-bootstrap/hnb659fds/version not found
cdk bootstrap
```

### Permission Errors
```bash
# Ensure your AWS credentials have these permissions:
# - CloudFormation full access
# - Lambda full access
# - API Gateway full access
# - Cognito full access
# - IAM role creation
# - S3 bucket access (for CDK assets)
```

### Client Secret Not Found
```bash
# If update-mcp-config.sh fails, make sure to use the correct profile:
./scripts/update-mcp-config.sh your-profile-name

# Or manually retrieve:
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-items 10 --profile your-profile --query "UserPools[?Name=='prometheus-mcp-oauth-pool'].Id" --output text)
CLIENT_ID=$(jq -r '.authorization_configuration.client_id' mcp-server-config.json)
aws cognito-idp describe-user-pool-client --user-pool-id "$USER_POOL_ID" --client-id "$CLIENT_ID" --profile your-profile --query 'UserPoolClient.ClientSecret' --output text
```

### Wrong User Pool Found
```bash
# If script finds wrong user pool, check your AWS profile:
aws sts get-caller-identity --profile your-profile
aws cognito-idp list-user-pools --max-results 10 --profile your-profile --region us-west-2
```

### Lambda Function Not Found
```bash
# Check if Lambda deployed successfully
aws lambda get-function --function-name $(aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'PrometheusLambdaStack-MCPFunction')].FunctionName" --output text)
```

## 💰 **Cost Estimate**

- **Lambda**: ~$2-5/month (1M requests)
- **API Gateway**: ~$3-4/month (1M requests)
- **Cognito**: $0 (free tier <50K users)
- **CloudWatch**: ~$1/month (logs)
- **Total**: ~$5-10/month

## 🗑️ **Cleanup**

```bash
# Destroy all resources
cdk destroy --app 'npx ts-node bin/lambda-app.ts' --all

# Remove generated files
rm mcp-server-config.json
rm -rf cdk.out node_modules
```

## 🎯 **Next Steps**

1. **Use with MCP Clients**: Import `mcp-server-config.json` into your applications
2. **Monitor Usage**: Check CloudWatch metrics and logs
3. **Scale**: Lambda auto-scales, no configuration needed
4. **Integrate**: Use with Strands Agent, Cursor, Cline, etc.

## 📚 **Documentation**

- **[VISUAL_DIAGRAMS.md](VISUAL_DIAGRAMS.md)** - Architecture diagrams
- **[ENHANCED_ARCHITECTURE.md](ENHANCED_ARCHITECTURE.md)** - Detailed technical documentation
- **[LAMBDA_DEPLOYMENT.md](LAMBDA_DEPLOYMENT.md)** - Advanced deployment guide
