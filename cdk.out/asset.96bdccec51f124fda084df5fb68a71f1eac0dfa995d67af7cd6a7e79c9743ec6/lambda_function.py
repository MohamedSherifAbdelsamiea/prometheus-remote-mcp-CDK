import json
import boto3
import requests
import os
from datetime import datetime
from urllib.parse import urlencode

def handler(event, context):
    """Lambda handler for Prometheus MCP server"""
    
    try:
        # Parse the event
        if isinstance(event, str):
            event = json.loads(event)
        
        # Add logging to debug what we receive
        print(f"DEBUG: Received event: {json.dumps(event, default=str)}")
        
        # Check if this is an API Gateway event
        if 'httpMethod' in event:
            # Handle API Gateway health check
            if event.get('httpMethod') == 'GET' and '/health' in event.get('path', ''):
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'status': 'healthy',
                        'service': 'prometheus-mcp-lambda',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                }
            
            # Handle API Gateway MCP requests
            if event.get('httpMethod') == 'POST' and '/mcp' in event.get('path', ''):
                # Extract MCP request from API Gateway body
                body = event.get('body', '{}')
                if event.get('isBase64Encoded'):
                    import base64
                    body = base64.b64decode(body).decode('utf-8')
                
                try:
                    mcp_request = json.loads(body) if body else {}
                except json.JSONDecodeError:
                    return {
                        'statusCode': 400,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({'error': 'Invalid JSON in request body'})
                    }
                
                # Process the MCP request
                mcp_response = handle_mcp_request(mcp_request, context)
                
                # Return API Gateway compatible response
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps(mcp_response) if not isinstance(mcp_response, str) else mcp_response
                }
            
            # Unknown API Gateway request
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Not found'})
            }
        
        # Direct MCP call (not through API Gateway)
        return handle_mcp_request(event, context)
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }

def handle_mcp_request(event, context):
    """Handle MCP protocol requests"""
    
    method = event.get('method')
    params = event.get('params', {})
    
    print(f"DEBUG: Standard MCP format - method: {method}")
    
    # Handle MCP protocol methods
    if method == 'initialize':
        return {
            'jsonrpc': '2.0',
            'id': event.get('id'),
            'result': {
                'protocolVersion': '2024-11-05',
                'capabilities': {'tools': {}},
                'serverInfo': {
                    'name': 'prometheus-mcp-server',
                    'version': '1.0.0'
                }
            }
        }
    
    elif method == 'notifications/initialized':
        # Notifications don't have an id field in JSON-RPC 2.0
        return {
            'jsonrpc': '2.0'
        }
    
    elif method == 'tools/list':
        return {
            'jsonrpc': '2.0',
            'id': event.get('id'),
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
                    'description': 'Execute a PromQL query against Amazon Managed Prometheus at a specific instant in time. Returns current metric values. For time series data over a range, use ExecuteRangeQuery instead.',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'workspace_id': {'type': 'string', 'description': 'Prometheus workspace ID'},
                            'query': {'type': 'string', 'description': 'PromQL query'},
                            'region': {'type': 'string', 'description': 'AWS region'},
                            'time': {'type': 'string', 'description': 'Optional timestamp'}
                        },
                        'required': ['workspace_id', 'query']
                    }
                },
                {
                    'name': 'ExecuteRangeQuery',
                    'description': 'Execute a PromQL range query over a time period. Returns time series data useful for generating graphs or trend analysis.',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'workspace_id': {'type': 'string'},
                            'query': {'type': 'string'},
                            'start': {'type': 'string'},
                            'end': {'type': 'string'},
                            'step': {'type': 'string'},
                            'region': {'type': 'string'}
                        },
                        'required': ['workspace_id', 'query', 'start', 'end', 'step']
                    }
                },
                {
                    'name': 'ListMetrics',
                    'description': 'Get a sorted list of all available metric names in the Prometheus server. Useful for discovering metrics before crafting specific queries.',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'workspace_id': {'type': 'string'},
                            'region': {'type': 'string'}
                        },
                        'required': ['workspace_id']
                    }
                },
                {
                    'name': 'GetServerInfo',
                    'description': 'Get information about the Prometheus server configuration including URL, AWS region, profile, and service name. Useful for debugging connection issues.',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'workspace_id': {'type': 'string'},
                            'region': {'type': 'string'}
                        },
                        'required': ['workspace_id']
                    }
                }
            ]
            }
        }
    
    elif method == 'tools/call':
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        if tool_name == 'GetAvailableWorkspaces':
            result = handle_get_workspaces(arguments)
        elif tool_name == 'ExecuteQuery':
            result = handle_execute_query(arguments)
        elif tool_name == 'ExecuteRangeQuery':
            result = handle_range_query(arguments)
        elif tool_name == 'ListMetrics':
            result = handle_list_metrics(arguments)
        elif tool_name == 'GetServerInfo':
            result = handle_server_info(arguments)
        else:
            return {
                'jsonrpc': '2.0',
                'id': event.get('id'),
                'error': {'code': -32601, 'message': f'Unknown tool: {tool_name}'}
            }
        
        # Return MCP format for tools/call
        if isinstance(result, dict) and result.get('statusCode') == 200:
            body = json.loads(result['body'])
            return {
                'jsonrpc': '2.0',
                'id': event.get('id'),
                'result': {
                    'content': [{
                        'type': 'text',
                        'text': json.dumps(body, indent=2)
                    }]
                }
            }
        else:
            return {
                'jsonrpc': '2.0',
                'id': event.get('id'),
                'error': {'code': -32603, 'message': 'Tool execution failed'}
            }
    
    else:
        return {
            'jsonrpc': '2.0',
            'id': event.get('id'),
            'error': {'code': -32601, 'message': f'Unknown method: {method}'}
        }

def handle_get_workspaces(arguments):
    """Handle GetAvailableWorkspaces tool call"""
    try:
        region = arguments.get('region', 'us-west-2')
        
        # Create AMP client
        amp_client = boto3.client('amp', region_name=region)
        
        # List workspaces
        response = amp_client.list_workspaces()
        
        workspaces = []
        for ws in response.get('workspaces', []):
            if ws.get('status', {}).get('statusCode') == 'ACTIVE':
                workspaces.append({
                    'workspace_id': ws['workspaceId'],
                    'alias': ws.get('alias', ''),
                    'status': ws.get('status', {}).get('statusCode', ''),
                    'prometheus_url': f"https://aps-workspaces.{region}.amazonaws.com/workspaces/{ws['workspaceId']}"
                })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'workspaces': workspaces,
                'count': len(workspaces),
                'region': region
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to list workspaces: {str(e)}'})
        }

def handle_execute_query(arguments):
    """Handle ExecuteQuery tool call"""
    try:
        workspace_id = arguments['workspace_id']
        query = arguments['query']
        region = arguments.get('region', 'us-west-2')
        time_param = arguments.get('time')
        
        # Build query URL
        base_url = f"https://aps-workspaces.{region}.amazonaws.com/workspaces/{workspace_id}/api/v1/query"
        
        params = {'query': query}
        if time_param:
            params['time'] = time_param
        
        # Make authenticated request
        response = make_signed_request('GET', base_url, params, region)
        
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Query failed: {str(e)}'})
        }

def handle_range_query(arguments):
    """Handle ExecuteRangeQuery tool call"""
    try:
        workspace_id = arguments['workspace_id']
        query = arguments['query']
        start = arguments['start']
        end = arguments['end']
        step = arguments['step']
        region = arguments.get('region', 'us-west-2')
        
        # Build query URL
        base_url = f"https://aps-workspaces.{region}.amazonaws.com/workspaces/{workspace_id}/api/v1/query_range"
        
        params = {
            'query': query,
            'start': start,
            'end': end,
            'step': step
        }
        
        # Make authenticated request
        response = make_signed_request('GET', base_url, params, region)
        
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Range query failed: {str(e)}'})
        }

def handle_list_metrics(arguments):
    """Handle ListMetrics tool call"""
    try:
        workspace_id = arguments['workspace_id']
        region = arguments.get('region', 'us-west-2')
        
        # Build query URL
        base_url = f"https://aps-workspaces.{region}.amazonaws.com/workspaces/{workspace_id}/api/v1/label/__name__/values"
        
        # Make authenticated request
        response = make_signed_request('GET', base_url, {}, region)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'metrics': response.get('data', [])
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'List metrics failed: {str(e)}'})
        }

def handle_server_info(arguments):
    """Handle GetServerInfo tool call"""
    try:
        workspace_id = arguments['workspace_id']
        region = arguments.get('region', 'us-west-2')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'prometheus_url': f"https://aps-workspaces.{region}.amazonaws.com/workspaces/{workspace_id}",
                'aws_region': region,
                'service_name': 'aps',
                'workspace_id': workspace_id
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Get server info failed: {str(e)}'})
        }

def make_signed_request(method, url, params, region):
    """Make a signed request to Prometheus API"""
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    import boto3
    
    # Get credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # Build request
    if method == 'GET' and params:
        url = f"{url}?{urlencode(params)}"
    
    request = AWSRequest(method=method, url=url)
    
    # Sign request
    SigV4Auth(credentials, 'aps', region).add_auth(request)
    
    # Make request
    response = requests.get(url, headers=dict(request.headers))
    response.raise_for_status()
    
    return response.json()
