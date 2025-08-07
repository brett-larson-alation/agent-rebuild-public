# Complete Agent Rebuild

This directory contains scripts for **complete agent rebuild** - a single-script approach that installs and configures an Alation Agent from scratch on a new system.

## Timeline Expectations

- **Setup Time**: 3-5 minutes
- **Preparation Required**: None
- **Configuration**: Single script execution

## Available Scripts

| Authentication Method | Script | Purpose |
|----------------------|--------|---------|
| **Username/Password** | `rebuild-core.py` | Complete rebuild with manual login |
| **SSO (SAML, OIDC, etc.)** | `rebuild-sso.py` | Complete rebuild with SSO tokens |

## Quick Start

### For Manual Login Users

1. **Edit configuration** in `rebuild-core.py`:
   ```python
   BASE_URL = "https://yourcompany.alationcloud.com"
   USERNAME = "your-admin-username"
   PASSWORD = "your-admin-password"
   agent_id = 1
   INSTALL_AUTH_SERVICE = True  # Set to False if not needed
   ```

2. **Run the script**:
   ```bash
   python3 rebuild-core.py
   ```

### For SSO Users

1. **Generate tokens** from Alation UI:
   - Log into your Alation instance through your browser
   - Navigate to your user profile settings
   - Generate a Refresh Token and API Access Token

2. **Edit configuration** in `rebuild-sso.py`:
   ```python
   BASE_URL = "https://yourcompany.alationcloud.com"
   REFRESH_TOKEN = "your-refresh-token"
   API_ACCESS_TOKEN = "your-api-access-token"
   agent_id = 1
   INSTALL_AUTH_SERVICE = True  # Set to False if not needed
   ```

3. **Run the script**:
   ```bash
   python3 rebuild-sso.py
   ```

## What These Scripts Do

### Complete Process (All Phases)
```
✅ Authentication & Token Generation
✅ System Detection & Validation
✅ Agent Package Download & Validation
✅ Agent Package Installation
✅ Authentication Service Installation (optional)
✅ Agent Configuration
✅ Certificate Generation & Installation
✅ Service Startup & Connectivity
✅ Agent Registration & Resync
✅ Final Validation & Cleanup
```

### API Workflow
1. **Authentication**: Generate or use API tokens
2. **Download**: Get latest agent installer packages
3. **Install**: Install agent and dependencies via system package manager
4. **Configure**: Set up connectivity and certificates
5. **Activate**: Start services and register with Alation
6. **Sync**: Install connectors and validate functionality

## Prerequisites

### System Requirements
- **Linux Distribution**: Debian/Ubuntu (apt-get) or RHEL/CentOS (yum)
- **Python 3.7+**: With `requests` and `toml` libraries
- **Docker**: Must be installed and running
- **Network Access**: Connectivity to Alation instance and data sources
- **Sudo Access**: Required for system-level operations

### Alation Requirements
- **Alation Cloud Service** instance (not on-premise)
- **Server Admin** privileges in Alation
- **Authentication method**: Either username/password OR SSO tokens

### Install Dependencies
```bash
pip3 install requests toml
```

## Configuration Options

### Authentication Service (Optional)
Both scripts include an `INSTALL_AUTH_SERVICE` flag:

- **Set to `True`** if your data sources require:
  - Kerberos authentication
  - LDAP integration
  - Complex authentication workflows
  
- **Set to `False`** for:
  - Basic data source connections
  - Testing environments
  - Simplified installations

## Validation Steps

After the script completes, verify the installation:

1. **Check Docker containers**:
   ```bash
   sudo docker ps
   ```
   Should show agent, proxy, and connector containers.

2. **Test agent connectivity**:
   - Open Alation → Data Sources
   - Select a data source using the agent
   - Click Settings → Test Connection

3. **Verify service status**:
   ```bash
   sudo systemctl status hydra.service
   ```

## Troubleshooting

### Common Issues

**Authentication Errors**
- Verify credentials don't have angle brackets `<>`
- Ensure user has Server Admin privileges
- For SSO: Check tokens are active and not expired

**Installation Failures**
- Check available disk space: `df -h`
- Verify sudo/root access works
- Ensure no conflicting Docker installations

**Network Issues**
- Test connectivity: `ping your-instance.alationcloud.com`
- Check firewall rules for required ports
- Verify DNS resolution works

**Agent Connection Issues**
- Confirm agent ID is correct
- Check network access to data sources
- Verify certificates installed properly

## API Workflow Details

Both scripts use the Alation Agent API to automate the complete agent rebuild process. Understanding the API workflow helps with troubleshooting and customization.

### Authentication Methods

#### Manual Login Authentication (`rebuild-core.py`)
1. **Generate Refresh Token**: `POST /integration/v1/createRefreshToken/`
2. **Generate Access Token**: `POST /integration/v1/createAPIAccessToken/`
3. **Use Access Token**: All subsequent API calls use `TOKEN` header
4. **Revoke Tokens**: `POST /integration/v1/revokeAPIAccessTokens/` (automatic cleanup)

#### SSO Authentication (`rebuild-sso.py`)
- **Use Pre-Generated Tokens**: Tokens generated manually through Alation UI
- **No Token Generation**: Scripts use provided tokens directly
- **No Token Revocation**: Tokens remain active for manual management

### Core API Workflow (Both Scripts)

#### Phase 1: System Preparation
1. **Get Installer Info**: `GET /integration/v1/agent/installers/{flavor}/`
   - Retrieves latest version and SHA256 checksum
   - `{flavor}` = `debian` or `rhel` based on system detection

2. **Download Installer**: `GET /integration/v1/agent/installers/{flavor}/latest/`
   - Downloads binary installer package (tar.gz)
   - Validated against SHA256 checksum

#### Phase 2: Agent Configuration  
3. **Get Connectivity Endpoint**: `GET /integration/v1/agent/endpoint/`
   - Retrieves proxy endpoint for agent connectivity
   - Used to configure `/etc/hydra/hydra.toml`

4. **Sign Certificate**: `POST /integration/v1/agent/{agent_id}/sign_certificate/`
   - Submits Certificate Signing Request (CSR) generated by Kratos
   - Returns signed certificate chain for secure communication

#### Phase 3: Authentication Service (Optional)
5. **Get Auth Service Info**: `GET /integration/v1/agent/addons/auth/` 
   - Retrieves Authentication Service version and checksum (if `INSTALL_AUTH_SERVICE = True`)

6. **Download Auth Service**: `GET /integration/v1/agent/addons/auth/latest/`
   - Downloads Authentication Service addon package (if enabled)

#### Phase 4: Agent Activation
7. **Check Connection**: `GET /integration/v1/agent/{agent_id}/`
   - Polls every 5 seconds until `is_connected = true`
   - Maximum 2 minutes timeout (24 attempts)

8. **Initiate Resync**: `POST /integration/v1/agent/{agent_id}/resync/`
   - Triggers connector installation and metadata refresh
   - Returns `job_id` for monitoring

9. **Monitor Resync**: `GET /api/v1/bulk_metadata/job/?id={job_id}`
   - Polls every 5 seconds until status is `successful` or `failed`
   - Maximum 5 minutes timeout (60 attempts)

### API Call Count
- **Manual Login**: 12 total API calls (includes 3 authentication calls)
- **SSO**: 9 total API calls (uses pre-generated tokens)

### Error Handling
- **HTTP Status Validation**: All calls check for 200/201 responses
- **Checksum Verification**: SHA256 validation for all downloads
- **Automatic Cleanup**: Tokens revoked and temp files cleaned up on failure
- **Comprehensive Logging**: Color-coded progress and error messages

### Base URL Format
All endpoints are relative to your Alation Cloud Service instance:
```
https://your-instance.alationcloud.com
```

## Alternative: Partial Rebuild

The **[partial rebuild approach](../partial-rebuild/)** offers a two-phase option that pre-installs packages and activates them later.

| Method | Time | Description |
|--------|------|-------------|
| **Complete** | 3-5 min | Single script handles everything in one execution |
| **Partial** | 3-5 min | Two-phase: prepare once, activate when needed |

## Additional Resources

- [Main Repository Guide](../README.md)
- [Partial Rebuild Alternative](../partial-rebuild/README.md)
- [Alation Developer Portal](https://developer.alation.com/dev/recipes/agent-re-setup)