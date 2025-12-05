# Copyright 2025 Exploratory Studios
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ollama
import re
import json
import os
from config.settings import OLLAMA_HOST, DEFAULT_MODEL, DATA_DIR

class OllamaClient:
    # In-memory cache for model capabilities detected during this session
    # Format: {'model_name': {'thinking': bool, 'vision': bool, 'thinking_method': 'parameter'|'directive'}}
    _capabilities_cache = {}

    # Known models that support thinking (fallback list for offline detection)
    THINKING_MODEL_KEYWORDS = {
        'qwen3', 'qwen2.5', 'deepseek-r1', 'deepseek-v3', 'qwq'
    }

    # Known models that support vision
    VISION_MODEL_KEYWORDS = {
        'llava', 'bakllava', 'llava-phi', 'moondream', 'cogvlm', 'llama3.2-vision', 'gemma3'
    }

    def __init__(self, host=OLLAMA_HOST):
        self.client = ollama.AsyncClient(host=host)

    async def get_model_capabilities(self, model_name):
        """
        Detect model capabilities using the Ollama show() API.
        This is instant and reliable - the official way to check capabilities.

        Args:
            model_name (str): The model name to check.

        Returns:
            dict: {'thinking': bool, 'vision': bool}
        """
        # Check in-memory cache first
        if model_name in OllamaClient._capabilities_cache:
            print(f"[Capabilities] Using cached capabilities for {model_name}")
            return OllamaClient._capabilities_cache[model_name]

        try:
            print(f"[Capabilities] Fetching capabilities for {model_name}...")
            # Use the show() method to get model details
            details = await self.client.show(model_name)

            thinking_capable = False
            vision_capable = False
            thinking_method = None  # 'parameter' if API supports it, 'directive' if keyword-detected

            # Check capabilities field (primary source)
            if hasattr(details, 'capabilities'):
                caps = details.capabilities if isinstance(details.capabilities, list) else []
                thinking_capable = any('reasoning' in str(cap).lower() or 'think' in str(cap).lower() for cap in caps)
                vision_capable = any('vision' in str(cap).lower() for cap in caps)
                print(f"[Capabilities] Found capabilities field: {caps}")

                # If thinking is in API capabilities, it uses the parameter method
                if thinking_capable:
                    thinking_method = 'parameter'
                    print(f"[Capabilities] Thinking is parameter-based (has API support)")

            # Also check modelinfo for vision (contains vision-related params)
            if hasattr(details, 'modelinfo') and details.modelinfo:
                modelinfo = details.modelinfo
                # Check for vision-related parameters
                has_vision_params = any('vision' in str(key).lower() for key in modelinfo.keys())
                if has_vision_params:
                    vision_capable = True
                    print(f"[Capabilities] Found vision parameters in modelinfo")

            # If thinking wasn't detected via API, check keywords for directive-based thinking
            if not thinking_capable:
                model_lower = model_name.lower()
                if any(keyword in model_lower for keyword in OllamaClient.THINKING_MODEL_KEYWORDS):
                    thinking_capable = True
                    thinking_method = 'directive'
                    print(f"[Capabilities] Thinking is directive-based (detected via keyword)")

            result = {
                'thinking': thinking_capable,
                'vision': vision_capable,
                'thinking_method': thinking_method
            }

            # Cache the result
            OllamaClient._capabilities_cache[model_name] = result
            print(f"[Capabilities] {model_name} - thinking: {thinking_capable}, vision: {vision_capable}")
            return result

        except Exception as e:
            print(f"[Capabilities] Error fetching capabilities for {model_name}: {e}")
            # Fallback to keyword-based detection if show() fails
            model_lower = model_name.lower()
            thinking_capable = any(keyword in model_lower for keyword in OllamaClient.THINKING_MODEL_KEYWORDS)
            vision_capable = any(keyword in model_lower for keyword in OllamaClient.VISION_MODEL_KEYWORDS)

            # If thinking was detected via keyword fallback, it's directive-based
            thinking_method = 'directive' if thinking_capable else None

            result = {
                'thinking': thinking_capable,
                'vision': vision_capable,
                'thinking_method': thinking_method
            }
            OllamaClient._capabilities_cache[model_name] = result
            print(f"[Capabilities] {model_name} (fallback) - thinking: {thinking_capable}, vision: {vision_capable}")
            return result

    @classmethod
    def supports_thinking(cls, model_name):
        """
        Check if a model supports thinking mode.
        Returns cached value if available, otherwise returns False.
        Use get_model_capabilities() to fetch fresh capabilities.

        Args:
            model_name (str): The model name to check.

        Returns:
            bool: True if the model supports thinking, False otherwise.
        """
        if model_name in cls._capabilities_cache:
            return cls._capabilities_cache[model_name].get('thinking', False)
        return False

    @classmethod
    def supports_vision(cls, model_name):
        """
        Check if a model supports vision/image capabilities.
        Returns cached value if available, otherwise returns False.
        Use get_model_capabilities() to fetch fresh capabilities.

        Args:
            model_name (str): The model name to check.

        Returns:
            bool: True if the model supports vision, False otherwise.
        """
        if model_name in cls._capabilities_cache:
            return cls._capabilities_cache[model_name].get('vision', False)
        return False


    async def list_models(self):
        """Fetch available models from Ollama."""
        try:
            response = await self.client.list()
            # Handle both object (pydantic) and dict responses
            models = []
            if hasattr(response, 'models'):
                models_list = response.models
            else:
                models_list = response.get('models', [])
                
            for model in models_list:
                # Check for 'name' or 'model' attribute/key
                if hasattr(model, 'model'):
                    models.append(model.model)
                elif hasattr(model, 'name'):
                    models.append(model.name)
                elif isinstance(model, dict):
                    models.append(model.get('model') or model.get('name'))
                else:
                    models.append(str(model))
            return models
        except Exception as e:
            print(f"Error listing models: {e}")
            return []

    async def chat_stream(self, model, messages, enable_thinking=True, images=None):
        """
        Stream chat response from Ollama with thinking and image support.
        Intelligently handles both parameter-based thinking (think=True/False) and
        directive-based thinking (/think, /no_think) depending on model type.

        Args:
            model (str): Model name.
            messages (list): List of message dicts [{'role': 'user', 'content': '...'}, ...].
            enable_thinking (bool): Whether to enable thinking mode (default: True).
            images (str or list): Image file path(s) or base64 strings to include in the first message.

        Yields:
            dict: {'thinking': str, 'content': str} Chunks of thinking and response content.
        """
        try:
            # If images provided, add them to the LAST user message only
            if images:
                # Find the last user message and add images to it
                last_user_msg_idx = None
                for i, msg in enumerate(messages):
                    if msg.get('role') == 'user':
                        last_user_msg_idx = i

                if last_user_msg_idx is not None:
                    msg = messages[last_user_msg_idx]
                    if not msg.get('images'):
                        if isinstance(images, str):
                            msg['images'] = [images]
                        else:
                            msg['images'] = images if isinstance(images, list) else [images]

            # Get model capabilities to determine thinking method
            capabilities = await self.get_model_capabilities(model)
            thinking_method = capabilities.get('thinking_method')

            # For directive-based models, prepend /think or /no_think to ALL user messages
            if thinking_method == 'directive' and messages:
                directive = '/think' if enable_thinking else '/no_think'
                count = 0
                # Add directive to all user messages to maintain consistent thinking behavior
                for msg in messages:
                    if msg.get('role') == 'user':
                        msg['content'] = f"{directive}\n{msg['content']}"
                        count += 1
                if count > 0:
                    print(f"[ChatStream] Added directive '{directive}' to {count} user message(s) for {model}")

            # Build chat kwargs - only add 'think' parameter for parameter-based models
            chat_kwargs = {
                'model': model,
                'messages': messages,
                'stream': True,
            }

            # Only add think parameter if model supports it (parameter-based thinking)
            if thinking_method == 'parameter':
                chat_kwargs['think'] = enable_thinking
                print(f"[ChatStream] Using think parameter for {model}")
            elif thinking_method == 'directive':
                print(f"[ChatStream] Using directive-based thinking for {model}")
            else:
                print(f"[ChatStream] No thinking support detected for {model}")

            # Buffer for accumulating content to extract think tags
            buffered_content = ""
            in_thinking_section = False
            think_buffer = ""  # Accumulate thinking content between tags

            async for part in await self.client.chat(**chat_kwargs):
                message = part.get('message', {})

                # Extract thinking and content independently
                thinking_chunk = message.get('thinking', '')
                content_chunk = message.get('content', '')

                # For directive-based models, intelligently parse think tags while streaming
                if thinking_method == 'directive' and content_chunk:
                    buffered_content += content_chunk

                    # Check if we're currently in a thinking section
                    if '<think>' in buffered_content and not in_thinking_section:
                        # Found opening tag, but stream content BEFORE it first
                        think_start = buffered_content.find('<think>')
                        if think_start > 0:
                            # There's content before the think tag, stream it
                            pre_think_content = buffered_content[:think_start]
                            yield {
                                'thinking': '',
                                'content': pre_think_content
                            }
                        # Keep only the think section in buffer
                        buffered_content = buffered_content[think_start + 7:]  # Skip past '<think>'
                        in_thinking_section = True
                        print(f"[ChatStream] Detected start of think tag")

                    # If we're in a thinking section, accumulate thinking content
                    if in_thinking_section:
                        # Look for closing tag
                        closing_pos = buffered_content.find('</think>')
                        if closing_pos >= 0:
                            # Found closing tag, get remaining thinking before the tag
                            remaining_thinking = buffered_content[:closing_pos]

                            # Only yield if there's new thinking content (not already streamed)
                            if remaining_thinking:
                                yield {
                                    'thinking': remaining_thinking,
                                    'content': ''
                                }

                            in_thinking_section = False
                            print(f"[ChatStream] Extracted complete think tag")
                            think_buffer = ""

                            # Keep content after closing tag
                            buffered_content = buffered_content[closing_pos + 8:].strip()  # Skip past '</think>'

                            # Stream any remaining content after think tags
                            if buffered_content:
                                yield {
                                    'thinking': '',
                                    'content': buffered_content
                                }
                                buffered_content = ""
                        else:
                            # No closing tag yet, stream the new thinking content only
                            if buffered_content:
                                yield {
                                    'thinking': buffered_content,
                                    'content': ''
                                }
                            think_buffer += buffered_content
                            buffered_content = ""
                    else:
                        # Not in thinking section, stream content as it comes
                        if buffered_content:
                            yield {
                                'thinking': '',
                                'content': buffered_content
                            }
                            buffered_content = ""

                elif thinking_chunk or content_chunk:
                    # For parameter-based models or API thinking field, stream normally
                    yield {
                        'thinking': thinking_chunk,
                        'content': content_chunk
                    }

            # After stream ends, yield any remaining buffered content
            if buffered_content:
                yield {
                    'thinking': '',
                    'content': buffered_content
                }
        except Exception as e:
            print(f"Error in chat stream: {e}")
            yield {'thinking': '', 'content': f"\n[Error: {str(e)}]"}

    async def generate_chat_title(self, user_message, assistant_message, model=DEFAULT_MODEL):
        """
        Generate a smart title for a chat based on the first message exchange.
        Yields title chunks as they're generated for streaming updates.

        Args:
            user_message (str): The user's first message.
            assistant_message (str): The assistant's first response.
            model (str): Model to use for title generation.

        Yields:
            str: Title chunks as they're generated.
        """
        try:
            # Strip think tags from assistant message before using for title
            clean_assistant_message = re.sub(r'<think>.*?</think>', '', assistant_message, flags=re.DOTALL).strip()

            prompt = f"""Based on this conversation, generate a very short, concise title (maximum 5 words, no quotes):

User: {user_message[:200]}
Assistant: {clean_assistant_message[:200]}

Title:"""

            # Get model capabilities to determine thinking method
            capabilities = await self.get_model_capabilities(model)
            thinking_method = capabilities.get('thinking_method')
            supports_thinking = capabilities.get('thinking')

            messages = [{'role': 'user', 'content': prompt}]

            # For directive-based models, prepend /no_think to disable thinking during title generation
            if thinking_method == 'directive' and supports_thinking:
                messages[0]['content'] = f"/no_think\n{prompt}"
                print(f"[GenerateChatTitle] Added /no_think directive for {model}")

            full_title = ""
            chat_kwargs = {
                'model': model,
                'messages': messages,
                'stream': True,
            }
            # Only add think parameter if model supports parameter-based thinking
            if thinking_method == 'parameter' and supports_thinking:
                chat_kwargs['think'] = False
                print(f"[GenerateChatTitle] Using think=False parameter for {model}")

            async for chunk in await self.client.chat(**chat_kwargs):
                # Extract content from chunk
                if hasattr(chunk, 'message'):
                    message = chunk.message
                    if hasattr(message, 'content'):
                        content = message.content
                    else:
                        content = message.get('content', '')
                else:
                    content = chunk.get('message', {}).get('content', '')

                if content:
                    full_title += content

            # Clean up the final title - strip think tags, quotes, and limit length
            full_title = re.sub(r'<think>.*?</think>', '', full_title, flags=re.DOTALL).strip()
            full_title = full_title.strip('"\'').strip()
            if len(full_title) > 50:
                full_title = full_title[:47] + "..."

            # Yield the cleaned title for streaming updates
            if full_title:
                yield full_title

        except Exception as e:
            print(f"Error generating chat title: {e}")
            # Fallback to truncated user message
            fallback = user_message[:30] + "..." if len(user_message) > 30 else user_message
            yield fallback

# Global instance
ollama_service = OllamaClient()
