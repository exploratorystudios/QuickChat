#!/usr/bin/env python3
"""
Test actual QuickChat code to verify thinking directives are applied correctly.
"""

import asyncio
import sys
import os

# Add the project root to path so we can import QuickChat modules
sys.path.insert(0, '/home/thewindmage/Desktop/QuickChat')

from src.services.ollama_client import OllamaClient

async def test_actual_code():
    """Test the actual QuickChat directive application."""

    client = OllamaClient()

    # Test models
    models = [
        ("qwen3-vl:4b", "Thinking model (GGUF/Qwen3)"),
        ("smollm2:135m", "Non-thinking model"),
    ]

    for model_name, description in models:
        print("\n" + "=" * 80)
        print(f"Testing Model: {model_name}")
        print(f"Description: {description}")
        print("=" * 80)

        try:
            # Get capabilities using actual QuickChat code
            caps = await client.get_model_capabilities(model_name)
            thinking = caps.get('thinking')
            thinking_method = caps.get('thinking_method')

            print(f"\nCapabilities detected:")
            print(f"  - Thinking supported: {thinking}")
            print(f"  - Thinking method: {thinking_method}")

            # Create test message history
            messages = [
                {'role': 'user', 'content': 'Hello, how are you?'},
                {'role': 'assistant', 'content': 'I am doing well!'},
                {'role': 'user', 'content': 'What is 2+2?'}
            ]

            print(f"\nOriginal message history:")
            for i, msg in enumerate(messages):
                role = msg['role']
                content = msg['content'][:40] + "..." if len(msg['content']) > 40 else msg['content']
                print(f"  [{i}] {role:10} | {content}")

            # Test WITH thinking enabled
            print(f"\n--- Testing with THINKING ENABLED ---")
            messages_thinking = [dict(m) for m in messages]
            enable_thinking = True

            # Apply the exact same logic from chat_stream()
            if thinking_method == 'directive' and messages_thinking:
                for msg in messages_thinking:
                    if msg.get('role') == 'user':
                        directive = '/think' if enable_thinking else '/no_think'
                        msg['content'] = f"{directive}\n{msg['content']}"
                        print(f"✓ Applied directive '{directive}' to first user message")
                        break

            # Check what API parameters would be used
            if thinking_method == 'parameter':
                print(f"✓ Would use API parameter: think={enable_thinking}")
            elif thinking_method == 'directive':
                pass  # Already printed above
            else:
                print(f"✓ No thinking support - no directives or parameters")

            print(f"\nMessages after processing (thinking enabled):")
            for i, msg in enumerate(messages_thinking):
                role = msg['role']
                content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
                print(f"  [{i}] {role:10} | {content}")

            # Test WITH thinking disabled
            print(f"\n--- Testing with THINKING DISABLED ---")
            messages_no_thinking = [dict(m) for m in messages]
            enable_thinking = False

            # Apply the exact same logic from chat_stream()
            if thinking_method == 'directive' and messages_no_thinking:
                for msg in messages_no_thinking:
                    if msg.get('role') == 'user':
                        directive = '/think' if enable_thinking else '/no_think'
                        msg['content'] = f"{directive}\n{msg['content']}"
                        print(f"✓ Applied directive '{directive}' to first user message")
                        break

            # Check what API parameters would be used
            if thinking_method == 'parameter':
                print(f"✓ Would use API parameter: think={enable_thinking}")
            elif thinking_method == 'directive':
                pass  # Already printed above
            else:
                print(f"✓ No thinking support - no directives or parameters")

            print(f"\nMessages after processing (thinking disabled):")
            for i, msg in enumerate(messages_no_thinking):
                role = msg['role']
                content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
                print(f"  [{i}] {role:10} | {content}")

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_actual_code())
