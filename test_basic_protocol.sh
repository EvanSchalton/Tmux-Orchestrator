#\!/bin/bash

echo "=== MCP Server Basic Protocol Test ==="
echo

# Test 1: Initialize
echo "1. Testing initialization..."
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}' | timeout 2s python tmux_orchestrator/mcp_server.py > init_response.json 2>init_stderr.log

if [ -s init_response.json ]; then
    echo "✅ Initialization response received"
    cat init_response.json | jq -r '.result.serverInfo.name // "unknown"' 2>/dev/null | xargs -I {} echo "   Server name: {}"
else
    echo "❌ No initialization response"
    echo "Stderr:" && cat init_stderr.log
fi

# Test 2: Tools list (in initialized session)
echo
echo "2. Testing tools/list..."
(
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}'
echo '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}'
) | timeout 3s python tmux_orchestrator/mcp_server.py > tools_response.json 2>tools_stderr.log

if [ -s tools_response.json ]; then
    echo "✅ Tools list response received"
    # Count tools in response
    TOOL_COUNT=$(cat tools_response.json | tail -1 | jq -r '.result.tools | length' 2>/dev/null || echo "unknown")
    echo "   Tools count: $TOOL_COUNT"
else
    echo "❌ No tools list response"
    echo "Stderr:" && cat tools_stderr.log
fi

# Test 3: Invalid method
echo
echo "3. Testing error handling..."
echo '{"jsonrpc": "2.0", "id": 3, "method": "invalid_method", "params": {}}' | timeout 2s python tmux_orchestrator/mcp_server.py > error_response.json 2>error_stderr.log

if grep -q "error" error_response.json 2>/dev/null; then
    echo "✅ Error handling working"
else
    echo "⚠️  Error response format unknown"
fi

echo
echo "=== Test Summary ==="
echo "Server starts: $([ -s init_response.json ] && echo "✅ YES" || echo "❌ NO")"
echo "Protocol compliance: $(grep -q '"jsonrpc":"2.0"' init_response.json 2>/dev/null && echo "✅ YES" || echo "❌ NO")"
echo "Tools available: $([ "$TOOL_COUNT" \!= "unknown" ] && [ "$TOOL_COUNT" -gt 0 ] && echo "✅ YES ($TOOL_COUNT)" || echo "❌ NO")"

# Cleanup
rm -f init_response.json init_stderr.log tools_response.json tools_stderr.log error_response.json error_stderr.log
