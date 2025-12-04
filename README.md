# Prometheus MCP Lambda Server - CDK Deployment

Production-ready Prometheus MCP (Model Context Protocol) server deployed as AWS Lambda with API Gateway and Cognito authentication.

**✅ MCP SDK Migration Complete** - Now using official MCP SDK with STDIO adapter (December 2024)

## 🏗️ **Architecture Overview**

```
┌─────────────────┐    ┌─────────────────────────────────────────────────────────┐
│   MCP Client    │    │                    AWS Cloud                           │
│ (Strands/Cursor │    │                                                         │
│    /Cline)      │    │  ┌─────────────────┐  ┌─────────────────────────────┐  │
└─────────────────┘    │  │   Cognito       │  │        API Gateway          │  │
         │              │  │   User Pool     │  │                             │  │
         │              │  │ + OAuth Client  │  │  ┌─────────────────────────┐ │  │
         │              │  └─────────────────┘  │  │   JWT Authorizer        │ │  │
         │              │           │           │  │      Lambda             │ │  │
         │              │           │           │  └─────────────────────────┘ │  │
         │              │           │           │                             │  │
         ├──────────────┼───────────┘           │  /mcp (POST) - Protected    │  │
         │              │                       │  /health (GET) - Public     │  │
         └──────────────┼───────────────────────┤                             │  │
                        │                       └─────────────────────────────┘  │
                        │                                       │                 │
                        │                       ┌─────────────────────────────┐  │
                        │                       │     Prometheus MCP          │  │
                        │                       │    Lambda Function          │  │
                        │                       │                             │  │
                        │                       │  • GetAvailableWorkspaces   │  │
                        │                       │  • ExecuteQuery             │  │
                        │                       │  • ExecuteRangeQuery        │  │
                        │                       │  • ListMetrics              │  │
                        │                       │  • GetServerInfo            │  │
                        │                       └─────────────────────────────┘  │
                        │                                       │                 │
                        │                       ┌─────────────────────────────┐  │
                        │                       │    Amazon Managed           │  │
                        │                       │    Prometheus (AMP)         │  │
                        │                       │                             │  │
                        │                       │  • Metrics Storage          │  │
                        │                       │  • PromQL Query Engine      │  │
                        │                       │  • 748+ Available Metrics   │  │
                        │                       └─────────────────────────────┘  │
                        └─────────────────────────────────────────────────────────┘

Flow:
1. MCP Client requests OAuth token from Cognito
2. Client sends MCP request with JWT token to API Gateway
3. API Gateway validates token via JWT Authorizer Lambda
4. Authorized requests invoke Prometheus MCP Lambda
5. Lambda queries Amazon Managed Prometheus
6. Metrics data returned through the chain back to client
```

## 🏗️ **CDK Deployment Architecture**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CDK Application (lambda-app.ts)                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐ │
│  │   CognitoStack      │  │   LambdaStack       │  │  APIGatewayStack        │ │
│  │                     │  │                     │  │                         │ │
│  │ • User Pool         │  │ • Lambda Function   │  │ • REST API              │ │
│  │ • M2M OAuth Client  │  │ • IAM Role          │  │ • JWT Authorizer        │ │
│  │ • Resource Server   │  │ • AMP Permissions   │  │ • /mcp & /health        │ │
│  │ • Cognito Domain    │  │ • 5 MCP Tools       │  │ • Config Generation     │ │
│  │                     │  │                     │  │                         │ │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────────┘ │
│           │                         │                         │                │
│           └─────────────────────────┼─────────────────────────┘                │
│                                     │                                          │
│                    Dependencies: APIGatewayStack depends on both               │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                              Generated Outputs                                  │
│                                                                                 │
│  • mcp-server-config.json - Complete MCP client configuration                  │
│  • CloudFormation outputs - All resource ARNs and endpoints                    │
│  • Environment variables - Configurable deployment parameters                  │
└─────────────────────────────────────────────────────────────────────────────────┘

Deployment Order:
1. CognitoStack - Creates authentication infrastructure
2. LambdaStack - Deploys MCP server function (parallel with Cognito)
3. APIGatewayStack - Creates API endpoints and generates config (depends on both)
```

## 🚀 **Quick Deploy**

```bash
# 1. Install dependencies
npm install

# 2. Set AWS profile (replace with your values)
export AWS_PROFILE=your-profile

# 3. Bootstrap CDK (first time only) - specify region explicitly
cdk bootstrap --region us-west-2

# 4. Deploy all stacks - ALWAYS use --region flag to avoid conflicts
cdk deploy --app 'npx ts-node bin/lambda-app.ts' --all --region us-west-2

# 5. Update config with client secret (use same profile)
./update-mcp-config.sh

# 6. Test deployment
curl $(jq -r '.endpoint' mcp-server-config.json | sed 's/mcp$/health/')

# 7. Test MCP endpoint (optional - requires authentication)
# See test_lambda_mcp_endpoint.py for comprehensive testing
```

**Note**: The Lambda function now uses `lambda_function_v2.handler` with the official MCP SDK.

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
export CDK_DEFAULT_REGION=us-west-2  # Optional: override profile region

# Verify profile works
aws sts get-caller-identity --profile your-profile-name
```

**Why profiles matter**: Without specifying a profile, the deployment might conflict with existing Cognito User Pools or domains in your default AWS account. Cognito domains are globally unique across all AWS accounts.

**Domain Conflicts**: If you get a Cognito domain error, set a custom domain prefix:
```bash
export COGNITO_DOMAIN_PREFIX=my-unique-prefix-$(date +%s)
cdk deploy --app 'npx ts-node bin/lambda-app.ts' --all --region us-west-2
```

### 2. Setup Environment
```bash
# Navigate to project directory (if not already there)
# cd path/to/lambda-mcp-cdk

# Install dependencies
npm install

# Set AWS profile for this session
export AWS_PROFILE=your-profile-name
```

### 3. Bootstrap CDK (First Time Only)
```bash
# Bootstrap CDK in your AWS account/region - specify region explicitly
cdk bootstrap --region us-west-2

# Verify bootstrap
aws ssm get-parameter --name /cdk-bootstrap/hnb659fds/version --region us-west-2
```

### 4. Deploy Infrastructure
```bash
# Deploy all stacks at once - ALWAYS use --region flag to avoid conflicts
cdk deploy --app 'npx ts-node bin/lambda-app.ts' --all --region us-west-2

# OR deploy individually
cdk deploy --app 'npx ts-node bin/lambda-app.ts' PrometheusLambdaMCPCognitoStack --region us-west-2
cdk deploy --app 'npx ts-node bin/lambda-app.ts' PrometheusLambdaMCPStack --region us-west-2
cdk deploy --app 'npx ts-node bin/lambda-app.ts' PrometheusLambdaMCPAPIGatewayStack --region us-west-2
```

### 5. Configure Client Secret
```bash
# Make script executable (if needed)
chmod +x update-mcp-config.sh

# Update config with real client secret and ID
./update-mcp-config.sh

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

# Advanced testing with Python script
python3 test_lambda_mcp_endpoint.py
```

### 7. Python Test Script
The included test scripts provide comprehensive testing:

```bash
# Run unit tests
cd lambda-mcp-wrapper/lambda
python3 test_migration.py

# Run property-based tests
python3 test_properties.py

# Run integration tests (requires AWS credentials)
AWS_PROFILE=default AWS_REGION=us-east-1 python3 test_integration.py
```

**Test Coverage**:
- 3 unit tests (initialize, tools/list, tool_schema)
- 8 property-based tests (100+ examples each)
- 7 integration tests (real AWS services)

## ⚙️ **Environment Variables**

The CDK deployment supports the following environment variables for customization:

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_PROFILE` | AWS profile to use for deployment | Required |
| `COGNITO_DOMAIN_PREFIX` | Cognito domain prefix | `prometheus-mcp-{random}` |
| `USER_POOL_NAME` | Cognito User Pool name | `prometheus-mcp-oauth-pool` |
| `RESOURCE_SERVER_ID` | OAuth resource server identifier | `prometheus-mcp-server` |
| `CALLBACK_URL` | OAuth callback URL | `https://localhost:3000/oauth2/idpresponse` |
| `LOGOUT_URL` | OAuth logout URL | `https://localhost:3000/` |
| `OAUTH_SCOPE` | OAuth scopes | `prometheus-mcp-server/read prometheus-mcp-server/write` |

```bash
# Example with custom values - ALWAYS use --region flag
export AWS_PROFILE=my-aws-profile
export COGNITO_DOMAIN_PREFIX=my-custom-prefix
export USER_POOL_NAME=my-mcp-pool
cdk deploy --app 'npx ts-node bin/lambda-app.ts' --all --region us-west-2
```

**⚠️ IMPORTANT**: Always use the `--region` flag with CDK commands to avoid deployment conflicts. The `CDK_DEFAULT_REGION` environment variable is overridden by your AWS profile's default region.

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

### Cognito Domain Conflict Error
```bash
# Error: Domain already associated with another user pool
# This happens when the domain generation creates a conflicting name

# Solution: Set a unique domain prefix before deployment
export COGNITO_DOMAIN_PREFIX=your-unique-prefix-$(date +%s)-$(openssl rand -hex 4)

# Clean up failed stack
cdk destroy PrometheusLambdaMCPCognitoStack --region us-west-2 --profile your-profile

# Deploy with unique domain
cdk deploy --app 'npx ts-node bin/lambda-app.ts' --all --region us-west-2 --profile your-profile
```

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
# If update-mcp-config.sh fails, run it again:
./update-mcp-config.sh

# Or check CloudFormation outputs directly:
aws cloudformation describe-stacks --stack-name PrometheusLambdaMCPCognitoStack --query "Stacks[0].Outputs"
```

### CDK Token Error in Config
```bash
# If you see ${Token[TOKEN.XX]} in config file, run the update script:
./update-mcp-config.sh
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

## 🔄 **MCP SDK Migration**

This project has been migrated from manual JSON-RPC handling to the official MCP SDK:

- **Handler**: `lambda_function_v2.handler` (new) vs `lambda_function.handler` (old)
- **Architecture**: STDIO adapter bridges MCP SDK to Lambda HTTP
- **Testing**: Comprehensive unit, property-based, and integration tests
- **Status**: ✅ Deployed and operational

See `MIGRATION_PROGRESS.md` for detailed migration tracking.

## 📄 **License**

This project is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file for details.

## 🤝 **Contributing**

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute to this project.

## 🔒 **Security**

See [SECURITY.md](SECURITY.md) for security best practices and reporting security issues.

