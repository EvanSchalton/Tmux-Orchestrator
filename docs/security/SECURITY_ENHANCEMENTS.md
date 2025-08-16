# Security Enhancements Documentation

## Overview

This document describes the security enhancements implemented in tmux-orchestrator to protect against common attack vectors and ensure safe operation in multi-user environments.

## Security Features Implemented

### 1. Rate Limiting (`tmux_orchestrator/utils/rate_limiter.py`)

#### Purpose
Prevents resource exhaustion attacks and ensures fair usage of system resources by limiting the rate of requests.

#### Implementation
- **Token Bucket Algorithm**: Allows burst traffic while maintaining average rate limits
- **Sliding Window Rate Limiter**: Provides precise rate limiting for critical operations
- **Configurable Limits**: Per-user/session rate limiting with customizable thresholds

#### Usage
```python
from tmux_orchestrator.utils.rate_limiter import RateLimiter, RateLimitConfig

# Configure rate limiter
config = RateLimitConfig(
    max_requests=100,      # 100 requests per minute
    window_seconds=60.0,   # 1 minute window
    burst_size=10,         # Allow burst of 10 requests
    block_on_limit=False,  # Raise exception instead of blocking
)

limiter = RateLimiter(config)

# Check rate limit
await limiter.check_rate_limit("user_id")
```

#### MCP Server Integration
- All MCP tool calls are rate limited by default
- Rate limits are enforced before input sanitization
- Failed rate limit checks return structured error responses

### 2. Input Sanitization (`tmux_orchestrator/utils/input_sanitizer.py`)

#### Purpose
Prevents injection attacks, validates input formats, and ensures data integrity across all user inputs.

#### Input Types Validated
- **Session Names**: Alphanumeric, underscore, hyphen, dot only
- **Window Names**: Session names + spaces allowed
- **Target Strings**: session:window format validation
- **Messages**: Command injection prevention, ANSI escape removal
- **File Paths**: Directory traversal prevention, sensitive path blocking
- **Agent Types**: Whitelist validation
- **Team Types**: Whitelist validation

#### Security Protections
- **Command Injection**: Blocks backticks, command substitution, variable expansion
- **Path Traversal**: Prevents `../` sequences and access to sensitive directories
- **ANSI Escape Sequences**: Removes terminal manipulation codes
- **Length Limits**: Prevents buffer overflow and DoS attacks
- **Special Character Filtering**: Removes dangerous shell metacharacters

#### Usage Examples
```python
from tmux_orchestrator.utils.input_sanitizer import sanitize_input, validate_agent_type

# Sanitize different input types
session_name = sanitize_input("my-project", "session")
message = sanitize_input("Hello world", "message")
agent_type = validate_agent_type("developer")

# Generic sanitization
safe_value = sanitize_input(user_input, "target")
```

### 3. Resource Limits (`tmux_orchestrator/core/monitor.py`)

#### Purpose
Prevents unbounded memory growth and ensures system stability under load.

#### Terminal Cache Limits
- **Maximum Entries**: Configurable limit on cached terminal states (default: 100)
- **Age-based Cleanup**: Removes stale caches older than threshold (default: 24 hours)
- **LRU Eviction**: Least Recently Used algorithm for cache cleanup
- **Periodic Cleanup**: Automatic cleanup every hour during monitoring cycles

#### Configuration
```python
# Configuration options
config = {
    "monitoring.max_cache_entries": 100,     # Max agents to track
    "monitoring.max_cache_age_hours": 24,    # Max cache age
}
```

#### Implementation Details
- **Access Time Tracking**: LRU tracking for efficient cleanup
- **Stale Entry Detection**: Removes caches with no recent content
- **Graceful Error Handling**: Cleanup errors don't crash the monitor
- **Memory Bounds**: Enforces hard limits on cache growth

### 4. MCP Server Security Integration

#### Comprehensive Security Pipeline
1. **Rate Limiting**: Check request rate before processing
2. **Input Sanitization**: Validate and clean all arguments
3. **Tool Execution**: Only execute if security checks pass
4. **Error Handling**: Safe error responses without information leakage

#### Request Flow
```
Client Request → Rate Limit Check → Input Sanitization → Tool Execution → Response
                      ↓                    ↓
                 Rate Limited         Validation Error
                      ↓                    ↓
                 Error Response      Error Response
```

#### Security Headers
- Origin tracking for rate limiting
- Structured error responses with retry information
- No sensitive information in error messages

## Configuration

### Environment Variables
```bash
# Rate limiting
TMUX_ORC_RATE_LIMIT_REQUESTS=100
TMUX_ORC_RATE_LIMIT_WINDOW=60

# Resource limits
TMUX_ORC_MAX_CACHE_ENTRIES=100
TMUX_ORC_MAX_CACHE_AGE_HOURS=24
```

### Configuration File
```yaml
# .tmux_orchestrator/config.yaml
monitoring:
  max_cache_entries: 100
  max_cache_age_hours: 24
  pm_recovery_grace_period_minutes: 3

security:
  rate_limit:
    max_requests: 100
    window_seconds: 60
    burst_size: 10
```

## Security Testing

### Test Coverage
- **Rate Limiting Tests**: `tests/test_security_rate_limiting.py`
- **Input Sanitization Tests**: `tests/test_security_input_sanitization.py`
- **Resource Limits Tests**: `tests/test_security_resource_limits.py`
- **MCP Security Tests**: `tests/test_mcp_security.py`

### Running Security Tests
```bash
# Run all security tests
pytest tests/test_security_*.py -v

# Run specific test category
pytest tests/test_security_rate_limiting.py -v
```

## Threat Model

### Threats Mitigated
1. **Resource Exhaustion**: Rate limiting prevents DoS attacks
2. **Command Injection**: Input sanitization blocks shell injection
3. **Path Traversal**: Path validation prevents unauthorized file access
4. **Memory Exhaustion**: Resource limits prevent unbounded growth
5. **Terminal Manipulation**: ANSI escape filtering prevents terminal hijacking

### Residual Risks
1. **Network Security**: TLS/encryption must be handled at transport layer
2. **Authentication**: User authentication must be implemented separately
3. **Authorization**: Fine-grained permissions need additional implementation
4. **Audit Logging**: Comprehensive audit trails need separate implementation

## Best Practices

### For Developers
1. **Always Sanitize**: Use sanitization functions for all user inputs
2. **Check Limits**: Respect resource limits in new features
3. **Error Handling**: Don't leak sensitive information in errors
4. **Testing**: Add security tests for new functionality

### For Operators
1. **Monitor Resources**: Watch cache sizes and cleanup frequency
2. **Tune Rate Limits**: Adjust limits based on usage patterns
3. **Update Regularly**: Keep security features updated
4. **Log Security Events**: Monitor for failed validation attempts

### For Users
1. **Use Valid Inputs**: Follow naming conventions for sessions/agents
2. **Respect Limits**: Don't exceed rate limits or resource quotas
3. **Report Issues**: Report suspected security vulnerabilities

## Security Metrics

### Monitored Metrics
- Rate limit violations per user/session
- Input validation failures by type
- Cache cleanup frequency and size
- Resource usage patterns

### Alerting Thresholds
- High rate limit violation rates (>10% of requests)
- Frequent validation failures (may indicate attack)
- Cache cleanup failures
- Memory usage above 80% of limits

## Incident Response

### Security Event Classification
- **Critical**: Command injection attempts, path traversal
- **High**: Sustained rate limit violations, resource exhaustion
- **Medium**: Input validation failures, cache limit exceeded
- **Low**: Single rate limit violations, normal cleanup events

### Response Procedures
1. **Detect**: Security monitoring and alerting
2. **Assess**: Classify severity and impact
3. **Contain**: Apply additional rate limiting if needed
4. **Investigate**: Analyze logs and patterns
5. **Recover**: Restore normal operation
6. **Learn**: Update security measures based on findings

## Future Enhancements

### Planned Improvements
1. **Enhanced Monitoring**: Real-time security dashboards
2. **Machine Learning**: Anomaly detection for attack patterns
3. **Fine-grained Permissions**: Role-based access control
4. **Audit Logging**: Comprehensive security event logging
5. **Network Security**: TLS termination and certificate management

### Integration Opportunities
1. **SIEM Integration**: Security Information and Event Management
2. **WAF Integration**: Web Application Firewall for HTTP endpoints
3. **Identity Providers**: OIDC/SAML integration for authentication
4. **Security Scanners**: Automated vulnerability assessment
