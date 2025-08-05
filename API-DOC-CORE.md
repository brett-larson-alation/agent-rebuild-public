# Alation Agent Rebuild API Documentation (Username/Password Authentication)

This document provides detailed information about the Alation APIs used in the `agent-rebuild-core.py` script for setting up and configuring Alation Agents with username/password authentication.

## Overview

The agent rebuild process uses the Alation Agent API to download, install, configure, and synchronize an Alation Agent. This version uses username/password authentication with temporary token generation and automatic revocation.

## Authentication Flow

Unlike the SSO version, this script follows a multi-step authentication process:

1. **Generate Refresh Token**: Create a temporary refresh token using username/password
2. **Generate Access Token**: Convert refresh token to API access token
3. **Use Access Token**: All subsequent API calls use the access token
4. **Revoke Tokens**: Clean up tokens at the end for security

All API requests after token generation use the `TOKEN` header:
```
Headers: {"TOKEN": "<api_access_token>"}
```

## Base URL

All endpoints are relative to your Alation Cloud Service instance:
```
BASE_URL = "https://<your-instance>.alationcloud.com"
```

## API Calls in Execution Order

### 1. Create Refresh Token

**Endpoint:** `POST /integration/v1/createRefreshToken/`

**Purpose:** Generate a temporary refresh token using Server Admin credentials

**Request Body:**
```json
{
  "username": "admin@company.com",
  "password": "password123",
  "name": "agent"
}
```

**Usage:** First step in authentication process for username/password users

**Script Usage:** Extracts `refresh_token` and `user_id` from response

**Error Handling:** Script validates HTTP status codes (200/201) and response structure

---

### 2. Create API Access Token

**Endpoint:** `POST /integration/v1/createAPIAccessToken/`

**Purpose:** Convert refresh token to API access token for subsequent requests

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user_id": 12345
}
```

**Usage:** Generates the token used for all subsequent API calls

**Script Usage:** Extracts `api_access_token` from response and adds to session headers

---

### 3. Get Agent Installer Information

**Endpoint:** `GET /integration/v1/agent/installers/{flavor}/`

**Purpose:** Retrieve version and checksum information for the latest agent installer

**Parameters:**
- `flavor` (path): Linux distribution flavor (`debian` or `rhel`)

**Usage:** Determines the latest available agent version and validates download integrity

**Script Usage:** Extracts `installers["latest"]["version"]` and `installers["latest"]["checksum"]`

---

### 4. Download Agent Installer

**Endpoint:** `GET /integration/v1/agent/installers/{flavor}/latest/`

**Purpose:** Download the latest agent installer package

**Parameters:**
- `flavor` (path): Linux distribution flavor (`debian` or `rhel`)

**Response:** Binary content (tar.gz file)

**Usage:** Downloads the actual installer package for system installation

---

### 5. Get Agent Connectivity Endpoint

**Endpoint:** `GET /integration/v1/agent/endpoint/`

**Purpose:** Retrieve the connectivity endpoint for agent proxy configuration

**Usage:** Configures the agent's proxy settings to connect to Alation services

**Script Usage:** Extracts `endpoint` field from response for Hydra configuration

---

### 6. Sign Certificate Request

**Endpoint:** `POST /integration/v1/agent/{agent_id}/sign_certificate/`

**Purpose:** Sign a Certificate Signing Request (CSR) for secure agent communication

**Parameters:**
- `agent_id` (path): Numeric identifier of the agent

**Request Body:**
```json
{
  "CSR": "-----BEGIN CERTIFICATE REQUEST-----\n...\n-----END CERTIFICATE REQUEST-----"
}
```

**Usage:** Establishes secure TLS communication between agent and Alation

**Script Usage:** Extracts `chain` field from response for certificate installation

---

### 7. Get Authentication Service Information

**Endpoint:** `GET /integration/v1/agent/addons/auth/`

**Purpose:** Retrieve version and checksum information for the Authentication Service addon

**Usage:** Determines the latest Authentication Service version for download validation

**Script Usage:** Extracts version and checksum from `["latest"]["version"]` and `["latest"]["checksum"]`

---

### 8. Download Authentication Service

**Endpoint:** `GET /integration/v1/agent/addons/auth/latest/`

**Purpose:** Download the latest Authentication Service addon

**Response:** Binary content (tar.gz file)

**Usage:** Downloads the Authentication Service required for data source authentication

---

### 9. Check Agent Connection Status

**Endpoint:** `GET /integration/v1/agent/{agent_id}/`

**Purpose:** Monitor agent connection status (polling endpoint)

**Parameters:**
- `agent_id` (path): Numeric identifier of the agent

**Usage:** Continuously polls until agent establishes connection with Alation

**Script Usage:** Checks `is_connected` field from response

**Polling Behavior:** Repeats every 5 seconds until `is_connected` is `true`

---

### 10. Initiate Agent Resynchronization

**Endpoint:** `POST /integration/v1/agent/{agent_id}/resync/`

**Purpose:** Start agent resync process to reinstall connectors and update metadata

**Parameters:**
- `agent_id` (path): Numeric identifier of the agent

**Usage:** Triggers the reinstallation of all agent connectors and metadata refresh

**Script Usage:** Extracts `job_id` from response for monitoring

---

### 11. Monitor Resync Job Status

**Endpoint:** `GET /api/v1/bulk_metadata/job/`

**Purpose:** Track the progress of the agent resync job (polling endpoint)

**Parameters:**
- `id` (query): Job ID returned from the resync initiation

**Usage:** Continuously polls until job status is `successful` or `failed`

**Script Usage:** Checks `status` field from response

**Possible Status Values:**
- `running`: Job is in progress
- `successful`: Job completed successfully
- `failed`: Job failed with errors

**Polling Behavior:** Repeats every 5 seconds until completion

---

### 12. Revoke API Access Tokens (Cleanup)

**Endpoint:** `POST /integration/v1/revokeAPIAccessTokens/`

**Purpose:** Revoke all tokens for security cleanup

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user_id": 12345
}
```

**Usage:** Always executed in `finally` block to ensure tokens are cleaned up

**Error Handling:** Catches and logs revocation failures but doesn't stop script execution

## Key Differences from SSO Version

### Authentication
- **Token Generation**: Creates temporary tokens using username/password
- **Token Management**: Automatically revokes tokens for security
- **User ID Required**: Must track user_id for token operations

### Security Features
- **Automatic Cleanup**: Tokens are always revoked in the finally block
- **Error Handling**: Comprehensive validation of authentication responses
- **Temporary Nature**: Tokens are short-lived and purpose-specific

### API Count
- **Total API Calls**: 12 distinct endpoints (vs 9 in SSO version)
- **Additional Calls**: 3 extra authentication-related endpoints
- **Same Core Process**: Identical agent setup workflow after authentication

## Error Handling

### Authentication Errors
- **HTTP Status Validation**: Checks for 200/201 status codes
- **Response Structure Validation**: Ensures required fields are present
- **Credential Validation**: Clear error messages for authentication failures

### Checksum Validation
Downloaded files are validated using SHA256 checksums:
- Agent installer checksum validation
- Authentication Service checksum validation

### Token Cleanup
- **Always Executed**: Token revocation runs in finally block
- **Graceful Degradation**: Logs warnings but doesn't fail if revocation fails
- **Security First**: Ensures no tokens remain active after script completion

## Security Considerations

1. **Credential Management**: Username/password should be securely stored
2. **Token Lifecycle**: Temporary tokens are automatically created and destroyed
3. **Secure Downloads**: All downloads are validated with SHA256 checksums
4. **Certificate Management**: TLS certificates are properly signed and installed
5. **Cleanup Guarantee**: Token revocation ensures no persistent authentication

## Dependencies

- **requests**: HTTP client library for API calls
- **hashlib**: SHA256 checksum validation
- **tempfile**: Secure temporary file handling
- **json**: JSON response parsing

## Notes

- The script uses a persistent `requests.Session()` to maintain authentication
- All system commands are executed with `sudo` privileges for agent installation
- Comprehensive cleanup on failure restores system state
- Token revocation is guaranteed regardless of script success/failure
- More secure than SSO version due to automatic token lifecycle management