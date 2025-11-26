# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2024-11-24

### Added
- Initial release of Prometheus Remote MCP Server CDK sample
- CDK deployment infrastructure with three stacks (Cognito, Lambda, API Gateway)
- Lambda function with 5 MCP tools for Prometheus queries
- OAuth 2.0 authentication with Amazon Cognito
- JWT authorization for API Gateway
- Integration with Amazon Managed Prometheus
- Comprehensive README with deployment instructions
- Python test script for validation
- Security best practices implementation

### Features
- **GetAvailableWorkspaces** - List Prometheus workspaces
- **ExecuteQuery** - Run instant PromQL queries
- **ExecuteRangeQuery** - Run time-range PromQL queries  
- **ListMetrics** - Get available metrics
- **GetServerInfo** - Server configuration details

### Security
- Cognito User Pool with OAuth client credentials flow
- API Gateway JWT authorizer
- IAM roles with least privilege access
- Secure Lambda deployment
