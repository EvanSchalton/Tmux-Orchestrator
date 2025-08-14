# Example: Agent Specialization and Skill Development

This example demonstrates how to create specialized agents with specific skills and how they can work together effectively on complex projects.

## Scenario

You're building a full-featured SaaS application that requires various specialized skills: API design, database optimization, security hardening, UI/UX design, and performance tuning.

## Step 1: Deploy Specialized Agents

Instead of generic agents, deploy specialists:

```bash
# Deploy API Design Specialist
tmux-orc spawn agent api-specialist \
  --role "API Designer" \
  --skills "REST,GraphQL,OpenAPI,API versioning" \
  --prompt "You are an expert API designer focused on creating intuitive, scalable APIs"

# Deploy Database Optimization Expert
tmux-orc spawn agent db-expert \
  --role "Database Architect" \
  --skills "PostgreSQL,query optimization,indexing,sharding" \
  --prompt "You specialize in database design and optimization for high-performance applications"

# Deploy Security Specialist
tmux-orc spawn agent security-expert \
  --role "Security Engineer" \
  --skills "OWASP,penetration testing,encryption,auth systems" \
  --prompt "You are a security expert focused on identifying and fixing vulnerabilities"

# Deploy Performance Engineer
tmux-orc spawn agent perf-engineer \
  --role "Performance Engineer" \
  --skills "profiling,caching,load testing,optimization" \
  --prompt "You optimize application performance and scalability"

# Deploy UI/UX Specialist
tmux-orc spawn agent ui-expert \
  --role "UI/UX Designer" \
  --skills "React,design systems,accessibility,user research" \
  --prompt "You create beautiful, intuitive user interfaces with excellent UX"
```

## Step 2: Create a Coordinating PM

Deploy a PM who understands how to leverage specialist skills:

```bash
tmux-orc spawn agent saas-pm \
  --role "Project Manager" \
  --prompt "You coordinate specialist agents, matching tasks to their expertise.
  You understand: API design, database architecture, security, performance, and UI/UX.
  Always assign tasks to the most qualified specialist."
```

## Step 3: Skill-Based Task Assignment

The PM intelligently assigns tasks based on agent skills:

```
PM > "Analyzing project requirements and assigning to specialists:

API Tasks → API Specialist:
- Design user management API
- Create billing API specification
- Define webhook system

Database Tasks → DB Expert:
- Design multi-tenant schema
- Optimize query performance
- Plan data partitioning strategy

Security Tasks → Security Expert:
- Implement OAuth2 flow
- Audit API endpoints
- Set up rate limiting

Performance Tasks → Performance Engineer:
- Profile application bottlenecks
- Implement caching strategy
- Load test API endpoints

UI Tasks → UI/UX Specialist:
- Design dashboard components
- Create responsive layouts
- Implement accessibility features"
```

## Step 4: Cross-Specialist Collaboration

### API and Database Collaboration

```
API Specialist > "I've designed the user API. Need schema from @db-expert"
DB Expert > "Schema ready. Note: using UUID for user IDs for sharding"
API Specialist > "Updating API spec to use UUIDs throughout"
```

### Security Review Process

```
Security Expert > "Reviewing API design from @api-specialist:
  ⚠️ Issue: User deletion endpoint exposes internal IDs
  ✅ Good: All endpoints require authentication
  ⚠️ Issue: Missing rate limiting on password reset
  ✅ Good: Proper input validation schemas"

API Specialist > "Thanks! Updating based on security review"
```

### Performance Optimization Loop

```
Performance Engineer > "Load test results:
  - User API: 2000 req/s ✅
  - Search API: 50 req/s ❌ (target: 500)

  @db-expert: Search queries need optimization"

DB Expert > "Adding composite index on (name, email, created_at).
  Query time reduced from 200ms to 5ms"

Performance Engineer > "Retesting... Now achieving 800 req/s ✅"
```

## Step 5: Specialist Skill Development

Agents can learn from each other:

```bash
# Share knowledge between specialists
tmux-orc agent share-knowledge security-expert api-specialist \
  --topic "API Security Best Practices"

# Security expert teaches API specialist
Security Expert > "Key API security principles:
  1. Always use HTTPS
  2. Implement proper authentication (OAuth2/JWT)
  3. Rate limit all endpoints
  4. Validate all inputs
  5. Use API keys for service-to-service"
```

## Step 6: Complex Feature Implementation

### Example: Implement Real-time Notifications

PM coordinates multiple specialists:

```
PM > "New feature: Real-time notifications. Task breakdown:

@api-specialist: Design WebSocket API
@db-expert: Design notification storage schema
@security-expert: Secure WebSocket connections
@perf-engineer: Ensure scalability to 10k concurrent connections
@ui-expert: Create notification UI components

Timeline: 3 days. Begin!"
```

### Specialist Responses

```
API Specialist > "WebSocket API design:
  - Connection: wss://api.app.com/notifications
  - Auth: JWT in connection params
  - Events: notification.new, notification.read, notification.deleted"

DB Expert > "Notification schema:
  - Partitioned by user_id for fast queries
  - TTL for auto-deletion after 30 days
  - Indexed on (user_id, created_at, read)"

Security Expert > "Security measures:
  - WSS only (no WS)
  - JWT validation on connect
  - Rate limit: 100 messages/minute/user
  - Sanitize all notification content"

Performance Engineer > "Scalability plan:
  - Use Redis for pub/sub
  - Horizontal scaling with sticky sessions
  - Connection pooling
  - Graceful reconnection strategy"

UI Expert > "UI Components:
  - NotificationBell with unread count
  - NotificationDropdown with infinite scroll
  - Toast notifications for urgent items
  - Accessibility: Screen reader friendly"
```

## Step 7: Quality Assurance by Specialists

Each specialist validates their domain:

```bash
# Run specialized quality checks
tmux-orc pm quality-check saas-app --by-specialist

## Quality Check Results by Specialist:

API Specialist:
✅ All APIs follow REST conventions
✅ OpenAPI specs are valid
✅ Versioning strategy implemented

DB Expert:
✅ No N+1 queries detected
✅ All queries use indexes
⚠️ Warning: Large table without partitioning

Security Expert:
✅ No SQL injection vulnerabilities
✅ All endpoints authenticated
❌ Missing CSP headers

Performance Engineer:
✅ Page load time < 2s
✅ API response time < 200ms
⚠️ Memory usage growing over time

UI Expert:
✅ WCAG 2.1 AA compliant
✅ Mobile responsive
✅ Design system consistent
```

## Advanced Specialization Patterns

### Specialist Pairing

```bash
# Pair specialists for complex tasks
tmux-orc agent pair api-specialist security-expert \
  --task "Design secure payment API" \
  --mode collaborative
```

### Specialist Review Chains

```bash
# Set up automatic review chains
tmux-orc pm configure-reviews saas-app \
  --chain "developer -> security-expert -> performance-engineer"
```

### Cross-Training Sessions

```bash
# Schedule knowledge sharing
tmux-orc pm schedule-training saas-app \
  --topic "Database Performance Tuning" \
  --teacher db-expert \
  --students "api-specialist,backend-dev"
```

## Specialist Communication Patterns

### Domain-Specific Channels

```bash
# Create specialist channels
tmux-orc team create-channel saas-app security-discuss
tmux-orc team create-channel saas-app performance-optimizations
tmux-orc team create-channel saas-app api-design
```

### Expert Consultations

```
Developer > "@security-expert: Is it safe to store API keys in environment variables?"
Security Expert > "Yes, but use a secrets manager in production. Here's why..."

Frontend Dev > "@perf-engineer: My React component re-renders too often"
Performance Engineer > "Use React.memo and useCallback. Let me show you..."
```

## Measuring Specialist Effectiveness

```bash
# Generate specialist performance report
tmux-orc pm report saas-app --specialist-metrics

## Specialist Performance Metrics

API Specialist:
- APIs designed: 12
- Breaking changes: 0
- Developer satisfaction: 95%

DB Expert:
- Query optimizations: 34
- Performance improvement: 78% avg
- Downtime caused: 0

Security Expert:
- Vulnerabilities found: 23
- Vulnerabilities fixed: 23
- Security incidents: 0

Performance Engineer:
- Performance improvements: 45
- Load capacity increase: 300%
- SLA compliance: 99.9%

UI Expert:
- Components created: 67
- Accessibility score: 98/100
- User satisfaction: 4.8/5
```

## Best Practices for Specialist Teams

1. **Clear Specializations**: Define specific expertise areas
2. **Cross-Domain Communication**: Encourage specialists to share knowledge
3. **Task Matching**: Always assign tasks to the most qualified specialist
4. **Continuous Learning**: Specialists should stay updated in their domains
5. **Collaborative Reviews**: Leverage specialist knowledge in reviews

## Scaling Specialist Teams

For larger projects, create specialist guilds:

```bash
# Create API Guild with multiple API specialists
tmux-orc team create-guild api-guild \
  --lead api-specialist \
  --members "api-specialist-2,api-specialist-3"

# Create Security Guild
tmux-orc team create-guild security-guild \
  --lead security-expert \
  --members "security-expert-2,appsec-specialist"
```

## Results of Specialization

After implementing specialist teams:
- 🎯 Task accuracy: 95% (tasks completed correctly first time)
- 🚀 Development speed: 3x faster than generalist teams
- 🛡️ Security issues: 90% caught before production
- 📈 Performance: All targets exceeded
- 😊 Code quality: Consistently high across domains
