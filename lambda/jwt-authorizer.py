import json
import urllib.request
import base64
import jwt

def lambda_handler(event, context):
    print(f"Authorizer event: {json.dumps(event)}")
    
    try:
        token = event['authorizationToken'].replace('Bearer ', '')
        
        # For now, let's just decode without verification to test the flow
        # In production, you should verify the signature
        decoded_token = jwt.decode(
            token,
            options={"verify_signature": False},  # Skip signature verification for now
            algorithms=["RS256"]
        )
        
        print(f"Decoded token: {json.dumps(decoded_token)}")
        
        # Check token_use is access
        if decoded_token.get('token_use') != 'access':
            raise Exception('Invalid token use')
            
        # Check issuer
        expected_issuer = "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_MGss0acir"
        if decoded_token.get('iss') != expected_issuer:
            raise Exception('Invalid issuer')
            
        # Generate policy
        policy = {
            'principalId': decoded_token['client_id'],
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': 'Allow',
                        'Resource': event['methodArn']
                    }
                ]
            },
            'context': {
                'clientId': decoded_token['client_id'],
                'scope': decoded_token.get('scope', '')
            }
        }
        
        print(f"Generated policy: {json.dumps(policy)}")
        return policy
        
    except Exception as e:
        print(f"Authorization failed: {str(e)}")
        raise Exception('Unauthorized')
