# API Issues & Feedback Report

## Critical API Issues Found During QA Testing

### 1. Ticket Move Endpoint Issue
**Endpoint:** `POST /api/tickets/move`  
**Status Code:** 422 Unprocessable Entity  
**Expected Payload:**
```json
{
  "ticket_id": 123,
  "target_column_id": 456,
  "position": 0
}
```
**Issue:** The endpoint rejects valid-looking payloads with 422 error. This blocks the entire drag-and-drop functionality.

### 2. Comment Creation Endpoint Issue  
**Endpoint:** `POST /api/tickets/{id}/comments`  
**Status Code:** 422 Unprocessable Entity  
**Expected Payload:**
```json
{
  "content": "Comment text",
  "author": "Username"
}
```
**Issue:** Cannot create comments on tickets. Validation appears to be rejecting standard comment payloads.

### 3. WebSocket Broadcast Limitations
**Endpoint:** `ws://localhost:8000/ws/connect`  
**Issue:** WebSocket connects successfully but doesn't broadcast ticket creation/update events to connected clients. Only connection establishment messages are sent.

## Workarounds Implemented

1. **For Testing:** Created alternative test scenarios that don't rely on move/comment operations
2. **For WebSocket:** Verified connection and latency instead of full broadcast functionality
3. **For Load Testing:** Postponed until move operation is fixed

## Recommendations for Development Team

1. **Add OpenAPI schema validation details** for 422 responses to show which fields failed
2. **Implement WebSocket event broadcasting** for ticket CRUD operations
3. **Add request/response logging** for debugging 422 errors
4. **Create integration tests** that cover these critical paths

## Test Data Created

During testing, we created:
- 5 test boards
- 27+ test tickets
- Various test payloads that can be used for debugging

The test scripts in `/tests/` can reproduce these issues consistently.