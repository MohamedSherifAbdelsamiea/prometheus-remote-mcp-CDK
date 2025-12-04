# Design Document

## Overview

This design covers the completion of the MCP SDK migration for the Lambda MCP wrapper. The migration replaces manual JSON-RPC handling with the official MCP SDK, using a custom STDIO adapter to bridge between Lambda's HTTP-based API Gateway and the SDK's STDIO transport expectations.

The core implementation is complete:
- **STDIO Adapter** (`stdio_adapter.py`) - Bridges MCP SDK to Lambda HTTP
- **New Lambda Handler** (`lambda_function_v2.py`) - Entry point using the adapter
- **Test Suite** (`test_migration.py`) - Unit tests for validation

This design focuses on the remaining work: testing, integration validation, deployment, and cleanup.

## Architecture

### System Components

```
┌─────────────────┐
│  API Gateway    │
└────────┬────────┘
         │ HTTP POST /mcp
         ▼
┌─────────────────────────────────────┐
│  Lambda Function                    │
│  (lambda_function_v2.py)            │
│                                     │
│  ┌───────────────────────────────┐ │
│  │  STDIO Adapter                │ │
│  │  (stdio_adapter.py)           │ │
│  │                               │ │
│  │  ┌─────────────────────────┐ │ │
│  │  │  FastMCP ToolManager    │ │ │
│  │  │                         │ │ │
│  │  │  ┌───────────────────┐ │ │ │
│  │  │  │ Prometheus MCP    │ │ │ │
│  │  │  │ Server Tools      │ │ │ │
│  │  │  │ - GetWorkspaces   │ │ │ │
│  │  │  │ - ExecuteQuery    │ │ │ │
│  │  │  │ - ExecuteRange    │ │ │ │
│  │  │  │ - ListMetrics     │ │ │ │
│  │  │  │ - GetServerInfo   │ │ │ │
│  │  │  └───────────────────┘ │ │ │
│  │  └─────────────────────────┘ │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  AWS Services   │
│  - AMP          │
│  - Prometheus   │
└─────────────────┘
```

### Request Flow

1. **API Gateway** receives HTTP POST to `/mcp` endpoint
2. **Lambda Handler** extracts JSON-RPC request from API Gateway event body
3. **STDIO Adapter** routes request based on JSON-RPC method:
   - `initialize` → Returns server capabilities
   - `tools/list` → Extracts tool definitions from ToolManager
   - `tools/call` → Invokes tool via ToolManager
4. **ToolManager** executes the requested tool function
5. **Tool Function** interacts with AWS services (AMP, Prometheus)
6. **Response** flows back through adapter → handler → API Gateway

## Components and Interfaces

### StdioAdapter Class

**Purpose**: Bridge between Lambda HTTP and MCP SDK STDIO transport

**Key Methods**:

```python
async def handle_jsonrpc_request(request: Dict[str, Any]) -> Dict[str, Any]
```
- Routes JSON-RPC requests to appropriate handlers
- Returns JSON-RPC formatted responses

```python
async def _handle_initialize(request_id: Any) -> Dict[str, Any]
```
- Handles MCP protocol handshake
- Returns server capabilities and version

```python
async def _handle_tools_list(request_id: Any) -> Dict[str, Any]
```
- Extracts tool definitions from FastMCP ToolManager
- Returns tool schemas in MCP format

```python
async def _handle_tools_call(request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]
```
- Invokes tools through ToolManager
- Handles parameter passing and result formatting
- Wraps results in MCP content format

### Lambda Handler Function

**Purpose**: AWS Lambda entry point for API Gateway events

**Signature**:
```python
def handler(event, context) -> Dict[str, Any]
```

**Responsibilities**:
- Parse API Gateway events
- Handle health check endpoint (`GET /health`)
- Extract MCP requests from POST body
- Invoke adapter asynchronously using `asyncio.run()`
- Format responses for API Gateway
- Handle errors and return appropriate HTTP status codes

### Test Suite

**Purpose**: Validate adapter and MCP integration

**Test Functions**:
- `test_initialize()` - Verify handshake protocol
- `test_tools_list()` - Verify all 5 tools are listed
- `test_tool_schema()` - Verify tool schemas are valid

## Data Models

### JSON-RPC Request Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "ExecuteQuery",
    "arguments": {
      "workspace_id": "ws-abc123",
      "query": "up"
    }
  }
}
```

### JSON-RPC Response Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"status\": \"success\", \"data\": [...]}"
    }]
  }
}
```

### JSON-RPC Error Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Tool execution failed: ..."
  }
}
```

### API Gateway Event Structure

```json
{
  "httpMethod": "POST",
  "path": "/mcp",
  "body": "{\"jsonrpc\": \"2.0\", ...}",
  "headers": {...},
  "isBase64Encoded": false
}
```

### Tool Schema Format

```json
{
  "name": "ExecuteQuery",
  "description": "Execute a PromQL query",
  "inputSchema": {
    "type": "object",
    "properties": {
      "workspace_id": {"type": "string"},
      "query": {"type": "string"}
    },
    "required": ["workspace_id", "query"]
  }
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Initialize response structure

*For any* initialize request with any request ID, the adapter should return a response containing protocolVersion "2024-11-05", capabilities object with tools key, and serverInfo with name and version fields.

**Validates: Requirements 1.2**

### Property 2: Tools list completeness

*For any* tools/list request, the adapter should return exactly 5 tools (GetAvailableWorkspaces, ExecuteQuery, ExecuteRangeQuery, ListMetrics, GetServerInfo), each with name, description, and inputSchema fields.

**Validates: Requirements 1.3**

### Property 3: Health check availability

*For any* GET request to the /health endpoint, the Lambda handler should return HTTP 200 with a JSON body containing status, service, version, and timestamp fields.

**Validates: Requirements 3.4**

### Property 4: JSON-RPC request routing

*For any* valid JSON-RPC request with a supported method (initialize, tools/list, tools/call, notifications/initialized), the adapter should correctly extract the method and parameters and route to the appropriate handler.

**Validates: Requirements 7.1**

### Property 5: JSON-RPC response formatting

*For any* successful tool execution result, the adapter should format the response as a valid JSON-RPC 2.0 response with jsonrpc field "2.0", matching id field, and result object containing content array with text type.

**Validates: Requirements 7.3, 4.2**

### Property 6: Error response formatting

*For any* tool execution failure or invalid request, the adapter should return a valid JSON-RPC 2.0 error response with jsonrpc field "2.0", matching id field, and error object containing code and message fields.

**Validates: Requirements 6.2, 6.4, 2.6**

### Property 7: Parameter passing integrity

*For any* tools/call request with tool name and arguments, the adapter should pass the arguments to ToolManager without modification or loss of data.

**Validates: Requirements 7.2**

### Property 8: Notification handling

*For any* JSON-RPC notification method (method without id or with null id), the adapter should process the request without returning a result field in the response.

**Validates: Requirements 7.4**

### Property 9: Request-response correlation

*For any* sequence of JSON-RPC requests with distinct IDs, each response should have an id field that matches exactly the id from its corresponding request.

**Validates: Requirements 7.5**

### Property 10: Exception logging

*For any* exception raised during adapter execution, the system should log the full stack trace to stdout/stderr before returning an error response.

**Validates: Requirements 6.1**

### Property 11: Tool execution response format

*For any* valid tool call that completes successfully, the response content should be parseable JSON text wrapped in an MCP content array structure.

**Validates: Requirements 1.4**

## Error Handling

### Error Categories

1. **Protocol Errors** (JSON-RPC level)
   - Invalid JSON in request body → HTTP 400, JSON parse error
   - Missing required fields → JSON-RPC error code -32602 (Invalid params)
   - Unknown method → JSON-RPC error code -32601 (Method not found)

2. **Tool Execution Errors**
   - Tool not found → JSON-RPC error code -32602
   - Invalid tool arguments → JSON-RPC error code -32602
   - Tool execution exception → JSON-RPC error code -32603 (Internal error)

3. **AWS Service Errors**
   - Missing credentials → Authentication error in tool result
   - Invalid workspace ID → Tool-specific error in result
   - Prometheus query error → Tool-specific error in result

4. **Lambda Errors**
   - Timeout → Lambda timeout (handled by AWS)
   - Out of memory → Lambda OOM (handled by AWS)
   - Cold start → Transparent to caller

### Error Response Format

All errors follow JSON-RPC 2.0 error format:

```json
{
  "jsonrpc": "2.0",
  "id": <request_id>,
  "error": {
    "code": <error_code>,
    "message": "<error_message>",
    "data": "<optional_additional_info>"
  }
}
```

### Error Codes

- `-32700`: Parse error (invalid JSON)
- `-32600`: Invalid request (malformed JSON-RPC)
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error (tool execution failure)

### Logging Strategy

- All exceptions print full stack trace via `traceback.print_exc()`
- Request/response pairs logged at DEBUG level
- Errors logged at ERROR level with context
- AWS CloudWatch captures all stdout/stderr

## Testing Strategy

### Unit Testing

**Framework**: Python `asyncio` with assertions

**Test Coverage**:
- Initialize handshake protocol
- Tools list extraction from ToolManager
- Tool schema validation
- JSON-RPC request parsing
- Response formatting
- Error handling paths

**Test Files**:
- `test_migration.py` - Core adapter tests

**Execution**:
```bash
cd lambda-mcp-wrapper/lambda
python test_migration.py
```

### Property-Based Testing

**Framework**: Python `hypothesis` library

**Property Tests**:
Each correctness property should be implemented as a property-based test that generates random inputs and verifies the property holds.

**Configuration**:
- Minimum 100 iterations per property test
- Random seed for reproducibility
- Shrinking enabled for minimal failing examples

**Test Tagging**:
Each property test must include a comment with this format:
```python
# Feature: mcp-sdk-migration, Property 1: Initialize response structure
```

**Property Test Examples**:

```python
from hypothesis import given, strategies as st

# Feature: mcp-sdk-migration, Property 1: Initialize response structure
@given(request_id=st.integers())
async def test_initialize_response_structure(request_id):
    adapter = StdioAdapter(prometheus_mcp_server)
    response = await adapter._handle_initialize(request_id)
    
    assert response['jsonrpc'] == '2.0'
    assert response['id'] == request_id
    assert 'result' in response
    assert response['result']['protocolVersion'] == '2024-11-05'
    assert 'capabilities' in response['result']
    assert 'tools' in response['result']['capabilities']
    assert 'serverInfo' in response['result']
    assert 'name' in response['result']['serverInfo']
    assert 'version' in response['result']['serverInfo']

# Feature: mcp-sdk-migration, Property 9: Request-response correlation
@given(request_ids=st.lists(st.integers(), min_size=1, max_size=10, unique=True))
async def test_request_response_correlation(request_ids):
    adapter = StdioAdapter(prometheus_mcp_server)
    
    for req_id in request_ids:
        request = {
            'jsonrpc': '2.0',
            'id': req_id,
            'method': 'initialize',
            'params': {}
        }
        response = await adapter.handle_jsonrpc_request(request)
        assert response['id'] == req_id
```

### Integration Testing

**Purpose**: Validate interaction with real AWS services

**Prerequisites**:
- AWS credentials configured
- At least one AMP workspace available
- Prometheus workspace accessible

**Test Cases**:
1. GetAvailableWorkspaces with real AWS account
2. ExecuteQuery with valid PromQL query
3. ExecuteRangeQuery with time range
4. ListMetrics from real workspace
5. GetServerInfo from real workspace
6. Error handling with invalid credentials
7. Error handling with invalid workspace ID

**Execution**: Manual testing or automated with AWS test account

### End-to-End Testing

**Purpose**: Validate complete flow through API Gateway

**Test Steps**:
1. Deploy Lambda function to AWS
2. Send HTTP POST to API Gateway /mcp endpoint
3. Verify JSON-RPC responses
4. Test all 5 tools via HTTP
5. Verify health check endpoint
6. Test error conditions

**Tools**: `curl`, `httpie`, or custom test script

### Deployment Validation

**Checklist**:
- [ ] Lambda function deploys successfully
- [ ] API Gateway endpoint responds
- [ ] Health check returns 200 OK
- [ ] Initialize handshake works
- [ ] Tools list returns 5 tools
- [ ] At least one tool executes successfully
- [ ] Error responses are properly formatted
- [ ] CloudWatch logs show expected output

## Deployment Plan

### CDK Stack Updates

**File**: `lib/lambda-stack.ts`

**Changes Required**:
1. Update Lambda handler reference from `lambda_function.handler` to `lambda_function_v2.handler`
2. Verify runtime is Python 3.11 or later
3. Ensure all dependencies are included in deployment package
4. Verify environment variables for AWS credentials

**Example**:
```typescript
const lambdaFunction = new lambda.Function(this, 'PrometheusLambda', {
  runtime: lambda.Runtime.PYTHON_3_11,
  handler: 'lambda_function_v2.handler',  // Updated
  code: lambda.Code.fromAsset('lambda-mcp-wrapper/lambda'),
  // ... other config
});
```

### Deployment Steps

1. **Update CDK Stack**
   ```bash
   # Edit lib/lambda-stack.ts to reference lambda_function_v2.handler
   ```

2. **Synthesize CDK**
   ```bash
   npm run build
   cdk synth
   ```

3. **Deploy to AWS**
   ```bash
   cdk deploy
   ```

4. **Verify Deployment**
   ```bash
   # Test health check
   curl https://<api-gateway-url>/health
   
   # Test MCP initialize
   curl -X POST https://<api-gateway-url>/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
   ```

### Rollback Plan

If issues are discovered:
1. Revert CDK stack to reference `lambda_function.handler`
2. Redeploy: `cdk deploy`
3. Verify old implementation works
4. Debug issues in new implementation
5. Redeploy when fixed

### Monitoring

**CloudWatch Metrics**:
- Lambda invocation count
- Lambda error rate
- Lambda duration
- API Gateway 4xx/5xx errors

**CloudWatch Logs**:
- Lambda execution logs
- Error stack traces
- Request/response debugging

**Alarms**:
- Error rate > 5%
- Duration > 10 seconds
- Throttling events

## Cleanup Tasks

### Files to Remove

After successful validation:
1. `lambda-mcp-wrapper/lambda/lambda_function.py` - Old manual implementation
2. Any unused manual JSON-RPC helper code
3. Old test files if superseded

### Documentation Updates

1. Update README.md with new architecture
2. Update AGENT.md to mark migration complete
3. Add deployment instructions for new handler
4. Document STDIO adapter design
5. Update API documentation if needed

### Code Review Checklist

- [ ] No imports of old `lambda_function.py`
- [ ] No references to manual JSON-RPC code
- [ ] All tests pass
- [ ] Documentation reflects new implementation
- [ ] CDK stack uses new handler
- [ ] Old files removed from repository

## Performance Considerations

### Cold Start

**Impact**: First request after deployment or idle period
**Mitigation**:
- Keep Lambda warm with periodic health checks
- Optimize import statements
- Lazy load heavy dependencies

### Memory Usage

**Current**: Default Lambda memory allocation
**Monitoring**: CloudWatch memory metrics
**Optimization**: Adjust Lambda memory if needed

### Latency

**Expected**:
- Health check: < 100ms
- Initialize: < 200ms
- Tools list: < 200ms
- Tool execution: 500ms - 5s (depends on AWS API calls)

**Bottlenecks**:
- AWS API calls (AMP, Prometheus)
- Network latency to Prometheus
- Query complexity

## Security Considerations

### Authentication

- Lambda uses IAM role for AWS service access
- API Gateway can use API keys, IAM auth, or Cognito
- Prometheus uses SigV4 authentication

### Input Validation

- JSON-RPC request validation
- Tool parameter validation via Pydantic
- Query injection prevention in PromQL

### Error Information Disclosure

- Error messages should not expose sensitive data
- Stack traces only in development/logs
- Generic errors to external callers

### Secrets Management

- AWS credentials from IAM role (not hardcoded)
- Prometheus endpoints from environment variables
- No secrets in code or logs

## Future Enhancements

### Potential Improvements

1. **Caching**: Cache workspace lists and metric names
2. **Batching**: Support multiple tool calls in one request
3. **Streaming**: Stream large query results
4. **Metrics**: Add custom CloudWatch metrics for tool usage
5. **Tracing**: Add X-Ray tracing for debugging
6. **Validation**: Add request/response schema validation
7. **Rate Limiting**: Implement per-client rate limits
8. **Retry Logic**: Add automatic retries for transient failures

### SDK Updates

Monitor MCP SDK releases for:
- New protocol features
- Performance improvements
- Bug fixes
- Breaking changes

Update adapter as needed to support new SDK versions.
