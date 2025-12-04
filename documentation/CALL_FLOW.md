# Lambda MCP Server - Complete Call Flow Documentation

## Overview

This document details the complete request flow from MCP client to Lambda MCP server, including OAuth 2.0 authentication, JWT validation, and MCP protocol handling.

## Architecture Components

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│ MCP Client  │────▶│   Cognito    │     │  API Gateway    │────▶│ JWT Authorizer│────▶│ MCP Lambda  │
│  (Python)   │     │  User Pool   │     │ (REST API)      │     │   Lambda      │     │  Function   │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘     └─────────────┘
                           │                      │                       │                     │
                           │                      │                       │                     │
                           ▼                      ▼                       ▼                     ▼
                    OAuth Token              HTTP Endpoint         Signature              MCP Protocol
                    Generation               /prod/mcp             Verification           Handler
```

## Phase 1: OAuth Authentication

### Step 1: Client Reads Configuration

**File**: `mcp-server-config.json`

```json
{
  "authorization_configuration": {
    "client_id": "3hifr4ho59ivsvrvqnt1bt3efu",
    "client_secret": "jpnq9jsr...",
    "exchange_url": "https://mcp-uswest2-....auth.us-west-2.amazoncognito.com/oauth2/token"
  }
}
```

### Step 2: Token Request

**Request**:
```http
POST /oauth2/token HTTP/1.1
Host: mcp-uswest2-93206254-1764351429299-voq6g9xy-1of9.auth.us-west-2.amazoncognito.com
Content-Type: application/x-www-form-urlencoded
Authorization: Basic M2hpZnI0aG81OWl2c3ZydnFudDFidDNlZnU6anBucTlqc3I...

grant_type=client_credentials&scope=prometheus-mcp-server/read prometheus-mcp-server/write
```

**Cognito Processing**:
1. Validates `client_id` and `client_secret`
2. Checks requested scopes are allowed for this client
3. Generates JWT token:
   - Signs with Cognito private key (RS256)
   - Sets expiration to 1 hour
   - Includes claims: `client_id`, `scope`, `iss`, `exp`, `token_use`

**Response**:
```json
{
  "access_token": "eyJraWQiOiJSQnl2QXBuc1hlVnpHTDVWODJBK0pKMTJNbG9qMGVSdEZNSDJtdGdob0prPSIsImFsZyI6IlJTMjU2In0...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**JWT Token Structure**:
```json
{
  "header": {
    "kid": "RByvApnsXeVzGL5V82A+JJ12Mloj0eRtFMH2mtghoJk=",
    "alg": "RS256"
  },
  "payload": {
    "sub": "3hifr4ho59ivsvrvqnt1bt3efu",
    "token_use": "access",
    "scope": "prometheus-mcp-server/read prometheus-mcp-server/write",
    "auth_time": 1764829903,
    "iss": "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_BXDXcVh5V",
    "exp": 1764833503,
    "iat": 1764829903,
    "client_id": "3hifr4ho59ivsvrvqnt1bt3efu"
  },
  "signature": "f-kWgrQMSJkOeaRDoaN9SiiKAOTPjsOSPscz9CdwfVm7..."
}
```

## Phase 2: MCP Request

### Step 3: Client Makes MCP Request

**Request**:
```http
POST /prod/mcp HTTP/1.1
Host: xlakxojll5.execute-api.us-west-2.amazonaws.com
Authorization: Bearer eyJraWQiOiJSQnl2QXBuc1hlVnpHTDVWODJBK0pKMTJNbG9qMGVSdEZNSDJtdGdob0prPSIsImFsZyI6IlJTMjU2In0...
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 1
}
```

### Step 4: API Gateway Processing

**API Gateway Actions**:
1. Receives POST request to `/prod/mcp`
2. Extracts `Authorization` header
3. Checks route configuration:
   - Method: POST
   - Path: /mcp
   - Authorizer: MCPJWTAuthorizer (Lambda)
4. Invokes JWT Authorizer Lambda

**Authorizer Invocation Event**:
```json
{
  "type": "TOKEN",
  "authorizationToken": "Bearer eyJraWQiOiJSQnl2...",
  "methodArn": "arn:aws:execute-api:us-west-2:338293206254:xlakxojll5/prod/POST/mcp"
}
```

## Phase 3: JWT Authorization

### Step 5: JWT Authorizer Lambda Processing

**File**: `lambda/jwt-authorizer.py`

#### 5.1: Extract Token
```python
token = event['authorizationToken'].replace('Bearer ', '')
```

#### 5.2: Get Token Header (Unverified)
```python
header = jwt.get_unverified_header(token)
# Returns: {"kid": "RByvApnsXeVzGL5V82A+JJ...", "alg": "RS256"}
```

#### 5.3: Fetch Cognito Public Keys (JWKS)
```python
@lru_cache(maxsize=1)
def get_jwks(region, user_pool_id):
    url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())

jwks = get_jwks('us-west-2', 'us-west-2_BXDXcVh5V')
```

**JWKS Response**:
```json
{
  "keys": [
    {
      "kid": "RByvApnsXeVzGL5V82A+JJ12Mloj0eRtFMH2mtghoJk=",
      "alg": "RS256",
      "kty": "RSA",
      "use": "sig",
      "n": "xGOr-H7A...",
      "e": "AQAB"
    }
  ]
}
```

#### 5.4: Find Matching Public Key
```python
key = next((k for k in jwks['keys'] if k['kid'] == header['kid']), None)
if not key:
    raise Exception('Public key not found in JWKS')

public_key = RSAAlgorithm.from_jwk(key)
```

#### 5.5: Verify Signature & Decode
```python
claims = jwt.decode(
    token,
    public_key,
    algorithms=['RS256'],
    issuer="https://cognito-idp.us-west-2.amazonaws.com/us-west-2_BXDXcVh5V",
    options={
        "verify_signature": True,  # ✅ RSA signature verification
        "verify_exp": True,        # ✅ Token not expired
        "verify_iss": True         # ✅ Correct Cognito pool
    }
)
```

**Security Validations**:
- **Signature**: Verifies token signed by Cognito private key using RSA-256
- **Expiration**: Checks `exp` claim < current time
- **Issuer**: Validates `iss` matches expected Cognito User Pool

#### 5.6: Validate Token Use
```python
if claims.get('token_use') != 'access':
    raise Exception(f"Invalid token_use: {claims.get('token_use')}")
```

#### 5.7: Validate Scopes
```python
token_scopes = set(claims.get('scope', '').split())
required_scopes = {'prometheus-mcp-server/read', 'prometheus-mcp-server/write'}

if not required_scopes.issubset(token_scopes):
    raise Exception(f'Insufficient scopes. Required: {required_scopes}, Got: {token_scopes}')
```

#### 5.8: Generate IAM Policy
```python
policy = {
    'principalId': claims['client_id'],
    'policyDocument': {
        'Version': '2012-10-17',
        'Statement': [{
            'Action': 'execute-api:Invoke',
            'Effect': 'Allow',
            'Resource': event['methodArn']
        }]
    },
    'context': {
        'clientId': claims['client_id'],
        'scope': claims.get('scope', ''),
        'issuer': claims['iss'],
        'expiresAt': str(claims['exp'])
    }
}
return policy
```

**CloudWatch Logs**:
```
✅ Token signature verified. Issuer: https://cognito-idp.us-west-2.amazonaws.com/us-west-2_BXDXcVh5V
✅ Token expiration validated. Expires: 1764833503
✅ Scopes validated: {'prometheus-mcp-server/read', 'prometheus-mcp-server/write'}
✅ Authorization successful for client: 3hifr4ho59ivsvrvqnt1bt3efu
```

### Step 6: API Gateway Receives Policy

**Policy Response**:
```json
{
  "principalId": "3hifr4ho59ivsvrvqnt1bt3efu",
  "policyDocument": {
    "Version": "2012-10-17",
    "Statement": [{
      "Action": "execute-api:Invoke",
      "Effect": "Allow",
      "Resource": "arn:aws:execute-api:us-west-2:338293206254:xlakxojll5/prod/POST/mcp"
    }]
  },
  "context": {
    "clientId": "3hifr4ho59ivsvrvqnt1bt3efu",
    "scope": "prometheus-mcp-server/read prometheus-mcp-server/write"
  }
}
```

**API Gateway Actions**:
1. Receives Allow policy
2. Caches policy for 5 minutes (keyed by `principalId`)
3. Proceeds with Lambda invocation

## Phase 4: MCP Lambda Execution

### Step 7: API Gateway Invokes MCP Lambda

**Lambda Invocation Event**:
```json
{
  "httpMethod": "POST",
  "path": "/prod/mcp",
  "body": "{\"jsonrpc\":\"2.0\",\"method\":\"tools/list\",\"id\":1}",
  "headers": {
    "Authorization": "Bearer eyJ...",
    "Content-Type": "application/json"
  },
  "requestContext": {
    "authorizer": {
      "clientId": "3hifr4ho59ivsvrvqnt1bt3efu",
      "scope": "prometheus-mcp-server/read prometheus-mcp-server/write",
      "issuer": "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_BXDXcVh5V",
      "expiresAt": "1764833503"
    }
  }
}
```

### Step 8: MCP Lambda Processing

**File**: `lambda-mcp-wrapper/lambda/lambda_function.py`

#### 8.1: Parse Event
```python
def handler(event, context):
    if 'httpMethod' in event:
        # API Gateway format
        body = event.get('body', '{}')
        mcp_request = json.loads(body)
```

#### 8.2: Route to MCP Handler
```python
method = mcp_request.get('method')  # "tools/list"

if method == 'tools/list':
    return handle_tools_list(mcp_request)
```

#### 8.3: Handle tools/list
```python
def handle_tools_list(request):
    return {
        'jsonrpc': '2.0',
        'id': request.get('id'),
        'result': {
            'tools': [
                {
                    'name': 'GetAvailableWorkspaces',
                    'description': 'List available Prometheus workspaces',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'region': {'type': 'string', 'description': 'AWS region'}
                        }
                    }
                },
                {
                    'name': 'ExecuteQuery',
                    'description': 'Execute PromQL instant queries',
                    'inputSchema': {...}
                },
                {
                    'name': 'ExecuteRangeQuery',
                    'description': 'Execute PromQL range queries',
                    'inputSchema': {...}
                },
                {
                    'name': 'ListMetrics',
                    'description': 'Get sorted list of metric names',
                    'inputSchema': {...}
                },
                {
                    'name': 'GetServerInfo',
                    'description': 'Get Prometheus server info',
                    'inputSchema': {...}
                }
            ]
        }
    }
```

#### 8.4: Wrap in API Gateway Response
```python
return {
    'statusCode': 200,
    'headers': {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    },
    'body': json.dumps(mcp_response)
}
```

### Step 9: API Gateway Returns Response

**HTTP Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Access-Control-Allow-Origin: *

{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "GetAvailableWorkspaces",
        "description": "List available Prometheus workspaces",
        "inputSchema": {...}
      },
      {
        "name": "ExecuteQuery",
        "description": "Execute PromQL instant queries",
        "inputSchema": {...}
      },
      {
        "name": "ExecuteRangeQuery",
        "description": "Execute PromQL range queries",
        "inputSchema": {...}
      },
      {
        "name": "ListMetrics",
        "description": "Get sorted list of metric names",
        "inputSchema": {...}
      },
      {
        "name": "GetServerInfo",
        "description": "Get Prometheus server info",
        "inputSchema": {...}
      }
    ]
  }
}
```

### Step 10: Client Receives Response

**Client Processing**:
```python
response = requests.post(mcp_url, json=payload, headers=headers)
data = response.json()

tools = data['result']['tools']
print(f"✅ Found {len(tools)} tools")
for tool in tools:
    print(f"   - {tool['name']}: {tool['description']}")
```

## Performance Metrics

### Cold Start (First Request)
```
Total: ~2000ms
├─ JWT Authorizer Lambda init: 267ms
├─ JWKS fetch: 1500ms
├─ Token verification: 179ms
└─ MCP Lambda execution: 54ms
```

### Warm Request (Cached)
```
Total: ~2ms
├─ JWT Authorizer (cached policy): 0ms
├─ Token verification: 1.72ms
└─ MCP Lambda execution: 0.28ms
```

### Caching Strategy
1. **JWKS Cache**: `@lru_cache` in Lambda (lifetime of container)
2. **Policy Cache**: API Gateway (5 minutes, keyed by `principalId`)
3. **Token Cache**: Client-side (59 minutes, refresh before expiry)

## Error Scenarios

### 1. Invalid Token Signature

**Flow**:
```
Client → API Gateway → JWT Authorizer
                       ↓
                    jwt.decode() fails
                    jwt.InvalidSignatureError
                       ↓
                    raise Exception('Unauthorized')
                       ↓
API Gateway ← 401 Unauthorized
```

**Response**:
```json
{
  "message": "Unauthorized"
}
```

### 2. Expired Token

**Flow**:
```
JWT Authorizer checks exp claim
    ↓
exp (1764829903) < current_time (1764833600)
    ↓
jwt.ExpiredSignatureError
    ↓
401 Unauthorized
```

**CloudWatch Log**:
```
❌ Authorization failed: Token expired
```

### 3. Missing Scopes

**Flow**:
```
JWT Authorizer validates scopes
    ↓
token_scopes = {'prometheus-mcp-server/read'}  # Missing write
required_scopes = {'prometheus-mcp-server/read', 'prometheus-mcp-server/write'}
    ↓
not required_scopes.issubset(token_scopes)
    ↓
raise Exception('Insufficient scopes')
    ↓
401 Unauthorized
```

**CloudWatch Log**:
```
❌ Authorization failed: Insufficient scopes. Required: {'prometheus-mcp-server/read', 'prometheus-mcp-server/write'}, Got: {'prometheus-mcp-server/read'}
```

### 4. Wrong Issuer

**Flow**:
```
JWT Authorizer validates issuer
    ↓
claims['iss'] = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXX"
expected_issuer = "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_BXDXcVh5V"
    ↓
jwt.InvalidIssuerError
    ↓
401 Unauthorized
```

**CloudWatch Log**:
```
❌ Authorization failed: Invalid issuer - Token issuer does not match expected issuer
```

## Security Features

### 1. Signature Verification (RSA-256)
- **Purpose**: Prevents token forgery
- **Implementation**: Verifies token signed by Cognito private key
- **Protection**: Only Cognito can create valid tokens

### 2. Token Expiration
- **Purpose**: Limits token lifetime
- **Implementation**: Validates `exp` claim
- **Configuration**: 1 hour (3600 seconds)

### 3. Issuer Validation
- **Purpose**: Prevents token reuse across pools
- **Implementation**: Validates `iss` claim matches User Pool
- **Protection**: Tokens from other Cognito pools rejected

### 4. Scope Validation
- **Purpose**: Enforces least privilege
- **Implementation**: Checks required scopes present
- **Required**: `prometheus-mcp-server/read` + `prometheus-mcp-server/write`

### 5. Token Use Validation
- **Purpose**: Ensures correct token type
- **Implementation**: Validates `token_use` = "access"
- **Protection**: Rejects ID tokens or refresh tokens

## Configuration Files

### mcp-server-config.json
```json
{
  "name": "Prometheus MCP Lambda Server",
  "endpoint": "https://xlakxojll5.execute-api.us-west-2.amazonaws.com/prod/mcp",
  "authorization_flow": "OAuth Client Credentials",
  "authorization_configuration": {
    "client_id": "3hifr4ho59ivsvrvqnt1bt3efu",
    "client_secret": "jpnq9jsrco7brkqruol8nds7cmde44ato23ja17k6m86nq55gmf",
    "exchange_url": "https://mcp-uswest2-93206254-1764351429299-voq6g9xy-1of9.auth.us-west-2.amazoncognito.com/oauth2/token",
    "exchange_parameters": [
      {"key": "grant_type", "value": "client_credentials"},
      {"key": "scope", "value": "prometheus-mcp-server/read prometheus-mcp-server/write"}
    ]
  }
}
```

### Environment Variables (JWT Authorizer)
```bash
USER_POOL_ID=us-west-2_BXDXcVh5V
COGNITO_ISSUER=https://cognito-idp.us-west-2.amazonaws.com/us-west-2_BXDXcVh5V
REQUIRED_SCOPES=prometheus-mcp-server/read prometheus-mcp-server/write
AWS_REGION=us-west-2  # Set by Lambda runtime
```

## Testing

### Test with curl
```bash
# Get token
TOKEN=$(curl -s -X POST "https://mcp-uswest2-93206254-1764351429299-voq6g9xy-1of9.auth.us-west-2.amazoncognito.com/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&scope=prometheus-mcp-server/read prometheus-mcp-server/write" \
  -u "3hifr4ho59ivsvrvqnt1bt3efu:jpnq9jsrco7brkqruol8nds7cmde44ato23ja17k6m86nq55gmf" | jq -r '.access_token')

# Test MCP endpoint
curl -X POST "https://xlakxojll5.execute-api.us-west-2.amazonaws.com/prod/mcp" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' | jq .
```

### Test with Python
```bash
python3 test_lambda_mcp_endpoint.py
```

### Test with Interactive Script
```bash
python3 test_mcp_interactive.py
```

## Monitoring

### CloudWatch Logs

**JWT Authorizer**:
```bash
aws logs tail /aws/lambda/PrometheusLambdaMCPAPIGatewa-JWTAuthorizerE8D8D90E-cVQK42dNjp4R \
  --region us-west-2 --follow
```

**MCP Lambda**:
```bash
aws logs tail /aws/lambda/PrometheusLambdaMCPStack-MCPFunction073462F8-PNSas4IktDmz \
  --region us-west-2 --follow
```

### Key Metrics
- Authorization success rate
- Token validation latency
- JWKS fetch latency
- MCP request latency
- Error rates by type

## Troubleshooting

### Issue: 401 Unauthorized
**Check**:
1. Token not expired: `jwt.io` to decode and check `exp`
2. Correct scopes: Check `scope` claim
3. Valid signature: Verify `kid` matches JWKS
4. Correct issuer: Check `iss` claim

### Issue: 403 Forbidden
**Check**:
1. API Gateway resource policy
2. Lambda execution role permissions
3. Cognito User Pool configuration

### Issue: Slow responses
**Check**:
1. Cold start (first request after idle)
2. JWKS fetch latency
3. Lambda memory configuration
4. Network latency

## References

- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [JWT RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519)
- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [API Gateway Lambda Authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html)
- [MCP Specification](https://modelcontextprotocol.io/specification/)
