# Deployment Tracking Log

## v0.2.0-cognito-complete - 2025-11-19T14:51:00+04:00

### Status: ✅ SUCCESSFUL DEPLOYMENT

### Changes Made:
- Removed hardcoded values from Cognito stack
- Added environment variable support for:
  - `COGNITO_DOMAIN_PREFIX` (defaults to random string)
  - `USER_POOL_NAME` (defaults to 'prometheus-mcp-oauth-pool')
  - `RESOURCE_SERVER_ID` (defaults to 'prometheus-mcp-server')
  - `CALLBACK_URL` (defaults to 'https://localhost:3000/oauth2/idpresponse')
  - `LOGOUT_URL` (defaults to 'https://localhost:3000/')

### Deployed Resources:
- **Cognito User Pool**: us-west-2_ugryDczEK
- **Domain**: prometheus-mcp-si618c
- **M2M Client ID**: 1krhi8ratf7605nt06aq7oo7hc
- **Lambda Function**: PrometheusLambdaMCPStack-MCPFunction073462F8-aiDlyhp6h6T7
- **API Gateway**: 0ixu8aqtkc
- **MCP Endpoint**: https://0ixu8aqtkc.execute-api.us-west-2.amazonaws.com/prod/mcp
- **Health Endpoint**: https://0ixu8aqtkc.execute-api.us-west-2.amazonaws.com/prod/health

### Verification:
- ✅ Health endpoint responding correctly
- ✅ OAuth token retrieval working
- ✅ MCP configuration file generated with actual client secret
- ✅ All CDK stacks deployed successfully

### Git Tags:
- v0.1.0-init: Initial project state
- v0.2.0-cognito: Removed hardcoded values
- v0.2.0-cognito-complete: Successful deployment

### Next Steps:
- Ready for MCP client integration
- Can be used with Strands Agent, Cursor, Cline, etc.
- Monitor CloudWatch logs for usage

### Rollback Commands:
```bash
# Emergency rollback to previous working state
git reset --hard v0.1.0-init

# Destroy current deployment
AWS_PROFILE=amp cdk destroy --app 'npx ts-node bin/lambda-app.ts' --all
```

### Cost Estimate:
- Lambda: ~$2-5/month (1M requests)
- API Gateway: ~$3-4/month (1M requests)  
- Cognito: $0 (free tier <50K users)
- CloudWatch: ~$1/month (logs)
- **Total**: ~$5-10/month
