# Alation Agent Rebuild API Documentation (SSO Authentication)

This document provides detailed information about the Alation APIs used in the `agent-rebuild-sso.py` script for setting up and configuring Alation Agents with SSO authentication.

## Overview

The agent rebuild process uses the Alation Agent API to download, install, configure, and synchronize an Alation Agent. All API calls use SSO authentication with pre-generated tokens.

## Authentication

All API requests use the `TOKEN` header with an SSO access token:
```
Headers: {"TOKEN": "<api_access_token>"}
```

## Base URL

All endpoints are relative to your Alation Cloud Service instance:
```
BASE_URL = "https://<your-instance>.alationcloud.com"
```

## API Calls in Execution Order

### 1. Get Agent Installer Information

**Endpoint:** `GET /integration/v1/agent/installers/{flavor}/`

**Purpose:** Retrieve version and checksum information for the latest agent installer

**Parameters:**
- `flavor` (path): Linux distribution flavor (`debian` or `rhel`)

**Usage:** Determines the latest available agent version and validates download integrity

**Script Usage:** Extracts `installers["latest"]["version"]` and `installers["latest"]["checksum"]`

---

### 2. Download Agent Installer

**Endpoint:** `GET /integration/v1/agent/installers/{flavor}/latest/`

**Purpose:** Download the latest agent installer package

**Parameters:**
- `flavor` (path): Linux distribution flavor (`debian` or `rhel`)

**Response:** Binary content (tar.gz file)

**Usage:** Downloads the actual installer package for system installation

---

### 3. Get Agent Connectivity Endpoint

**Endpoint:** `GET /integration/v1/agent/endpoint/`

**Purpose:** Retrieve the connectivity endpoint for agent proxy configuration

**Usage:** Configures the agent's proxy settings to connect to Alation services

**Script Usage:** Extracts `endpoint` field from response for Hydra configuration

---

### 4. Sign Certificate Request

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

### 5. Get Authentication Service Information

**Endpoint:** `GET /integration/v1/agent/addons/auth/`

**Purpose:** Retrieve version and checksum information for the Authentication Service addon

**Usage:** Determines the latest Authentication Service version for download validation

**Script Usage:** Extracts version and checksum from `["latest"]["version"]` and `["latest"]["checksum"]`

---

### 6. Download Authentication Service

**Endpoint:** `GET /integration/v1/agent/addons/auth/latest/`

**Purpose:** Download the latest Authentication Service addon

**Response:** Binary content (tar.gz file)

**Usage:** Downloads the Authentication Service required for data source authentication

---

### 7. Check Agent Connection Status

**Endpoint:** `GET /integration/v1/agent/{agent_id}/`

**Purpose:** Monitor agent connection status (polling endpoint)

**Parameters:**
- `agent_id` (path): Numeric identifier of the agent

**Usage:** Continuously polls until agent establishes connection with Alation

**Script Usage:** Checks `is_connected` field from response

**Polling Behavior:** Repeats every 5 seconds until `is_connected` is `true`

---

### 8. Initiate Agent Resynchronization

**Endpoint:** `POST /integration/v1/agent/{agent_id}/resync/`

**Purpose:** Start agent resync process to reinstall connectors and update metadata

**Parameters:**
- `agent_id` (path): Numeric identifier of the agent

**Usage:** Triggers the reinstallation of all agent connectors and metadata refresh

**Script Usage:** Extracts `job_id` from response for monitoring

---

### 9. Monitor Resync Job Status

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

## Error Handling

### HTTP Error Responses

All API calls include error handling with `res.raise_for_status()` which raises exceptions for:
- 4xx Client Errors (authentication, authorization, bad requests)
- 5xx Server Errors (internal server issues)

### Checksum Validation

Downloaded files are validated using SHA256 checksums:
- Agent installer checksum validation
- Authentication Service checksum validation

If checksums don't match, the script raises an exception and terminates.

## Security Considerations

1. **Token Management**: SSO tokens are managed externally and not revoked by the script
2. **Secure Downloads**: All downloads are validated with SHA256 checksums
3. **Certificate Management**: TLS certificates are properly signed and installed
4. **Temporary Files**: Downloads use secure temporary files that are automatically cleaned up

## Dependencies

- **requests**: HTTP client library for API calls
- **hashlib**: SHA256 checksum validation
- **tempfile**: Secure temporary file handling

## Notes

- The script uses a persistent `requests.Session()` to maintain authentication across all API calls
- All system commands are executed with `sudo` privileges for agent installation
- The script includes comprehensive cleanup on failure to restore system state
- SSO tokens remain active after script completion for manual management