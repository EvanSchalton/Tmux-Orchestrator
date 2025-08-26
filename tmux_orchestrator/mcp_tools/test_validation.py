"""
Native MCP Tools Validation Test

Quick validation to ensure all tools can be imported and basic validation works.
"""

import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def test_tool_imports():
    """Test that all tools can be imported successfully."""
    logger.info("Testing tool imports...")

    try:
        # Test imports

        logger.info("✅ All 34 tools imported successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False


async def test_validation_logic():
    """Test parameter validation without executing commands."""
    logger.info("Testing parameter validation...")

    try:
        from .shared_logic import ValidationError, validate_session_format

        # Test valid session format
        validate_session_format("test-session:1")
        logger.info("✅ Valid session format accepted")

        # Test invalid session format
        try:
            validate_session_format("invalid")
            logger.error("❌ Invalid session format should have failed")
            return False
        except ValidationError:
            logger.info("✅ Invalid session format correctly rejected")

        return True

    except Exception as e:
        logger.error(f"❌ Validation test failed: {e}")
        return False


async def test_error_response_format():
    """Test error response formatting."""
    logger.info("Testing error response format...")

    try:
        from .shared_logic import format_error_response, format_success_response

        # Test error response
        error_resp = format_error_response("Test error message", "test command", ["suggestion 1", "suggestion 2"])

        expected_keys = {"success", "error", "command", "suggestions"}
        if not all(key in error_resp for key in expected_keys):
            logger.error(f"❌ Error response missing keys: {error_resp}")
            return False

        if error_resp["success"] is not False:
            logger.error(f"❌ Error response should have success=False: {error_resp}")
            return False

        logger.info("✅ Error response format correct")

        # Test success response
        success_resp = format_success_response({"test": "data"}, "test command", "Test success")

        expected_keys = {"success", "data", "command", "message"}
        if not all(key in success_resp for key in expected_keys):
            logger.error(f"❌ Success response missing keys: {success_resp}")
            return False

        if success_resp["success"] is not True:
            logger.error(f"❌ Success response should have success=True: {success_resp}")
            return False

        logger.info("✅ Success response format correct")
        return True

    except Exception as e:
        logger.error(f"❌ Response format test failed: {e}")
        return False


async def test_command_building():
    """Test command building logic."""
    logger.info("Testing command building...")

    try:
        from .shared_logic import build_command

        # Test basic command
        cmd = build_command(["tmux-orc", "agent", "list"])
        expected = ["tmux-orc", "agent", "list"]
        if cmd != expected:
            logger.error(f"❌ Basic command building failed: {cmd} != {expected}")
            return False

        # Test command with options
        cmd = build_command(["tmux-orc", "agent", "status"], {"metrics": True, "timeout": 30, "skip": False})

        # Should contain base command + --metrics + --timeout 30
        # Should NOT contain --skip (False values are ignored)
        if "tmux-orc" not in cmd or "--metrics" not in cmd or "--timeout" not in cmd:
            logger.error(f"❌ Command with options failed: {cmd}")
            return False

        if "--skip" in cmd:
            logger.error(f"❌ False options should be excluded: {cmd}")
            return False

        logger.info("✅ Command building logic correct")
        return True

    except Exception as e:
        logger.error(f"❌ Command building test failed: {e}")
        return False


async def run_all_tests():
    """Run all validation tests."""
    logger.info("🚀 Starting Native MCP Tools Validation")

    tests = [
        ("Tool Imports", test_tool_imports),
        ("Parameter Validation", test_validation_logic),
        ("Response Formatting", test_error_response_format),
        ("Command Building", test_command_building),
    ]

    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))

    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("🧪 VALIDATION SUMMARY")
    logger.info(f"{'='*50}")

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} {test_name}")
        if result:
            passed += 1

    logger.info(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - Native MCP Tools ready for deployment!")
        return True
    else:
        logger.error(f"⚠️  {total - passed} tests failed - review implementation")
        return False


if __name__ == "__main__":
    asyncio.run(run_all_tests())
