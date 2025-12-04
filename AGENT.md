# MCP SDK Migration Agent

## Mission
Migrate the Lambda MCP wrapper from manual JSON-RPC implementation to the official MCP SDK with STDIO server adapter.

## Current Progress

### ✅ Completed
1. **Analysis Phase**
   - Analyzed original Prometheus MCP server at `prometheus_mcp_server/server.py`
   - Identified FastMCP SDK usage patterns
   - Documented tool definitions and handlers
   - Verified MCP SDK is already installed in lambda directory

2. **Adapter Implementation**
   - Created `lambda-mcp-wrapper/lambda/stdio_adapter.py`
   - Implements STDIO to HTTP bridge for Lambda
   - Handles JSON-RPC request routing
   - Integrates with FastMCP ToolManager
   - Supports all MCP protocol methods:
     - `initialize` - Server handshake
     - `notifications/initialized` - Initialization complete
     - `tools/list` - List available tools
     - `tools/call` - Execute tool functions

3. **New Lambda Handler**
   - Created `lambda-mcp-wrapper/lambda/lambda_function_v2.py`
   - Uses official `awslabs.prometheus_mcp_server`
   - Routes requests through STDIO adapter
   - Maintains API Gateway compatibility
   - Preserves health check endpoint

4. **Test Suite**
   - Created `lambda-mcp-wrapper/lambda/test_migration.py`
   - Tests initialize handshake
   - Tests tools/list response
   - Validates tool schemas
   - Verifies all 5 expected tools

### 🔄 In Progress
5. **Testing & Validation**
   - Need to run test suite
   - Verify tool execution works
   - Test with actual AWS credentials

### ⏳ Pending
6. **Integration Testing**
   - Test GetAvailableWorkspaces with real AWS account
   - Test ExecuteQuery with Prometheus workspace
   - Test ExecuteRangeQuery
   - Test ListMetrics
   - Test GetServerInfo

7. **Deployment**
   - Update Lambda deployment to use `lambda_function_v2.py`
   - Update CDK stack if needed
   - Deploy to AWS
   - Test with DevOps Agent

8. **Cleanup**
   - Remove old `lambda_function.py` after validation
   - Update documentation
   - Remove manual JSON-RPC code

## Architecture

### Before (Manual JSON-RPC)
```
API Gateway → lambda_function.py → Manual JSON-RPC handlers → AWS SDK
```

### After (Official MCP SDK)
```
API Gateway → lambda_function_v2.py → stdio_adapter.py → FastMCP ToolManager → Official Prometheus MCP Server → AWS SDK
```

## Key Components

### 1. stdio_adapter.py
**Purpose**: Bridge STDIO-based MCP server to Lambda HTTP
**Key Methods**:
- `handle_jsonrpc_request()` - Main request router
- `_handle_initialize()` - Server handshake
- `_handle_tools_list()` - Extract tools from FastMCP
- `_handle_tools_call()` - Execute tools via ToolManager

### 2. lambda_function_v2.py
**Purpose**: Lambda entry point using official SDK
**Features**:
- API Gateway event handling
- Health check endpoint
- Async request processing
- Error handling with stack traces

### 3. Official Prometheus MCP Server
**Location**: `lambda-mcp-wrapper/lambda/awslabs/prometheus_mcp_server/`
**Tools Provided**:
1. **GetAvailableWorkspaces** - List Prometheus workspaces
2. **ExecuteQuery** - Run instant PromQL queries
3. **ExecuteRangeQuery** - Run time-range PromQL queries
4. **ListMetrics** - List available metrics
5. **GetServerInfo** - Get server configuration

## Technical Details

### MCP SDK Integration
- Uses `mcp.server.fastmcp.FastMCP` class
- Tools registered via `@mcp.tool()` decorator
- ToolManager handles tool execution
- Context injection for AWS credentials
- Pydantic models for type safety

### STDIO to HTTP Adapter
**Challenge**: MCP SDK expects stdin/stdout, Lambda uses HTTP
**Solution**: 
- Simulate STDIO by routing JSON-RPC through adapter
- Adapter calls ToolManager directly
- Captures results and formats as JSON-RPC responses
- No actual stdin/stdout piping needed

### AWS Integration
- Uses boto3 for AWS API calls
- SigV4 authentication for Prometheus
- Supports multiple AWS regions
- Workspace discovery via AMP API

## Next Steps

### Immediate Actions
1. Run test suite to validate adapter
2. Fix any issues found in testing
3. Test with AWS credentials configured

### Deployment Steps
1. Update Lambda handler reference in CDK
2. Deploy updated Lambda function
3. Test all 5 tools via API Gateway
4. Validate with DevOps Agent integration

### Validation Checklist
- [ ] Initialize handshake works
- [ ] tools/list returns 5 tools
- [ ] Tool schemas are correct
- [ ] GetAvailableWorkspaces lists workspaces
- [ ] ExecuteQuery runs PromQL queries
- [ ] ExecuteRangeQuery returns time series
- [ ] ListMetrics returns metric names
- [ ] GetServerInfo returns configuration
- [ ] Error handling works properly
- [ ] Health check endpoint responds

## Benefits of Migration

1. **Maintainability**: Use official SDK instead of manual JSON-RPC
2. **Reliability**: Leverage tested MCP implementation
3. **Features**: Automatic tool schema generation
4. **Updates**: Easy to update when SDK improves
5. **Standards**: Follow MCP protocol correctly
6. **Type Safety**: Pydantic validation built-in

## Files Modified/Created

### Created
- `lambda-mcp-wrapper/lambda/stdio_adapter.py` - STDIO to HTTP bridge
- `lambda-mcp-wrapper/lambda/lambda_function_v2.py` - New Lambda handler
- `lambda-mcp-wrapper/lambda/test_migration.py` - Test suite
- `AGENT.md` - This file
- `FILE_INDEX.md` - Project file index

### To Be Modified
- CDK stack to reference new handler
- Deployment scripts if needed

### To Be Removed (After Validation)
- `lambda-mcp-wrapper/lambda/lambda_function.py` - Old manual implementation

## Known Issues & Considerations

1. **Context Injection**: Tools expect Context parameter, adapter passes None (tools handle this)
2. **Async Execution**: Lambda handler uses asyncio.run() for async tools
3. **Error Handling**: Added traceback printing for debugging
4. **AWS Credentials**: Must be available in Lambda environment
5. **Cold Start**: First request may be slower due to SDK initialization

## Testing Strategy

### Unit Tests
- Test adapter methods individually
- Mock MCP server responses
- Verify JSON-RPC format

### Integration Tests
- Test with real MCP server instance
- Verify tool execution
- Check error handling

### End-to-End Tests
- Deploy to Lambda
- Test via API Gateway
- Validate with DevOps Agent

## Success Criteria

✅ All 5 tools accessible via API Gateway
✅ Responses match MCP protocol format
✅ Error handling works correctly
✅ Performance is acceptable
✅ DevOps Agent can use the tools
✅ No manual JSON-RPC code remains
