import * as cdk from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { Construct } from 'constructs';

export class CognitoStack extends cdk.Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;
  public readonly userPoolDomain: cognito.UserPoolDomain;
  public readonly m2mClient: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const domainPrefix = process.env.COGNITO_DOMAIN_PREFIX || 'prometheus-mcp-oauth-v2n2x';

    // Cognito User Pool
    this.userPool = new cognito.UserPool(this, 'PrometheusUserPool', {
      userPoolName: 'prometheus-mcp-oauth-pool',
      selfSignUpEnabled: false,
      signInAliases: {
        email: true,
      },
      autoVerify: {
        email: true,
      },
      passwordPolicy: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Resource Server with custom scopes for M2M
    const resourceServer = this.userPool.addResourceServer('MCPResourceServer', {
      identifier: 'prometheus-mcp-server',
      userPoolResourceServerName: 'Prometheus MCP Server',
      scopes: [
        {
          scopeName: 'read',
          scopeDescription: 'Read access to MCP server',
        },
        {
          scopeName: 'write',
          scopeDescription: 'Write access to MCP server',
        },
      ],
    });

    // App Client for ALB authentication (authorization code flow)
    this.userPoolClient = this.userPool.addClient('WebAppClient', {
      userPoolClientName: 'web-app-client',
      generateSecret: true,
      authFlows: {
        userPassword: true,
        userSrp: true,
        custom: false,
      },
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
        },
        scopes: [
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.PROFILE,
        ],
        callbackUrls: [
          'https://prometheus.v2n2x.com/oauth2/idpresponse',
        ],
        logoutUrls: [
          'https://prometheus.v2n2x.com/',
        ],
      },
    });

    // M2M Client for machine-to-machine authentication (client credentials flow)
    this.m2mClient = new cognito.UserPoolClient(this, 'M2MClient', {
      userPool: this.userPool,
      userPoolClientName: 'm2m-client',
      generateSecret: true,
      authFlows: {
        userPassword: false,
        userSrp: false,
        custom: false,
      },
      oAuth: {
        flows: {
          clientCredentials: true,
        },
        scopes: [
          cognito.OAuthScope.resourceServer(resourceServer, {
            scopeName: 'read',
            scopeDescription: 'Read access',
          }),
          cognito.OAuthScope.resourceServer(resourceServer, {
            scopeName: 'write', 
            scopeDescription: 'Write access',
          }),
        ],
      },
    });

    // Cognito Domain
    this.userPoolDomain = this.userPool.addDomain('MCPDomain', {
      cognitoDomain: {
        domainPrefix: domainPrefix,
      },
    });

    // Outputs
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID',
    });

    new cdk.CfnOutput(this, 'WebClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'Web App Client ID (for ALB)',
    });

    new cdk.CfnOutput(this, 'M2MClientId', {
      value: this.m2mClient.userPoolClientId,
      description: 'M2M Client ID (for machines)',
    });

    new cdk.CfnOutput(this, 'CognitoDomain', {
      value: this.userPoolDomain.domainName,
      description: 'Cognito Domain',
    });

    new cdk.CfnOutput(this, 'TokenEndpoint', {
      value: `https://${domainPrefix}.auth.${this.region}.amazoncognito.com/oauth2/token`,
      description: 'OAuth Token Endpoint (for M2M)',
    });
  }
}
