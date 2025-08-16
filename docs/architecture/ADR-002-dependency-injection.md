# ADR-002: Dependency Injection and Service Container

## Status
Accepted

## Context
The original monitor.py had hard-coded dependencies, making it difficult to test components in isolation and swap implementations. Components directly instantiated their dependencies, leading to tight coupling and inflexibility.

## Decision
We will implement a dependency injection container that:
1. Manages component lifecycles (singleton vs transient)
2. Supports both sync and async factories
3. Provides automatic dependency resolution
4. Enables easy mocking for tests

### Service Container Features:
```python
# Register implementations
container.register(Interface, Implementation)
container.register_async(AsyncInterface, async_factory)

# Resolve dependencies
service = container.resolve(Interface)
async_service = await container.resolve_async(AsyncInterface)

# Plugin support
container.register_plugin("strategy_name", strategy_instance)
```

## Consequences

### Positive
- Loose coupling between components
- Easy to swap implementations
- Simplified testing with mock injection
- Clear dependency graphs
- Support for both sync and async patterns

### Negative
- Additional abstraction layer
- Learning curve for developers
- Potential runtime errors if dependencies not registered

## Example Usage
```python
# Registration
builder = ServiceBuilder(container)
builder.add(CrashDetectorInterface)
       .use(lambda: CrashDetector(tmux, logger))
       .as_singleton()
       .build()

# Resolution with auto-injection
monitor = container.resolve(MonitorServiceInterface)
```
