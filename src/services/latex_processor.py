"""
LaTeX processing module for rendering mathematical expressions.
Converts LaTeX expressions to images and saves them to a cache directory.
"""

import re
import hashlib
import os
import tempfile
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from matplotlib import mathtext

# Use mathtext for LaTeX-like rendering without requiring full LaTeX installation
plt.rcParams['mathtext.default'] = 'regular'


class LaTeXProcessor:
    """Processes LaTeX expressions and converts them to PNG images."""

    # Cache for rendered expressions to avoid re-rendering
    _cache = {}
    _cache_dir = None

    @classmethod
    def _initialize_cache_dir(cls):
        """Initialize the cache directory for LaTeX images."""
        if cls._cache_dir is None:
            from config.settings import DATA_DIR
            cache_dir = DATA_DIR / "latex_cache"
            cache_dir.mkdir(exist_ok=True, parents=True)
            cls._cache_dir = str(cache_dir)

    @classmethod
    def _get_cache_key(cls, latex_expr: str) -> str:
        """Generate a cache key for a LaTeX expression."""
        return hashlib.md5(latex_expr.encode()).hexdigest()

    @classmethod
    def _render_latex_to_png(cls, latex_expr: str, is_inline: bool) -> str:
        """
        Render a single LaTeX expression to PNG and return the file path.

        Args:
            latex_expr: The LaTeX expression
            is_inline: Whether this is inline math (smaller) or display math

        Returns:
            Path to the rendered PNG file
        """
        cls._initialize_cache_dir()

        # Cache check
        cache_key = cls._get_cache_key(latex_expr)
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        try:
            # Create figure for rendering with proper sizing
            # Figure size in inches × DPI = pixel size
            # We want reasonable pixel sizes (e.g., ~400-600px for display math)
            if is_inline:
                figsize = (3, 0.5)  # ~450px wide at 150 dpi
                dpi = 150
                fontsize = 14
            else:
                # Use larger height for display math to accommodate complex expressions
                figsize = (5.5, 1.2)  # ~825px wide at 150 dpi, more height for multi-line
                dpi = 150
                fontsize = 16

            fig = plt.figure(figsize=figsize, dpi=dpi)
            ax = fig.add_subplot(111)
            ax.axis('off')

            # Render the expression with mathtext support (renders LaTeX math properly)
            # The $ signs tell matplotlib to use mathtext rendering
            ax.text(0.5, 0.5, f'${latex_expr}$',
                   horizontalalignment='center',
                   verticalalignment='center',
                   fontsize=fontsize,
                   color='white',
                   transform=ax.transAxes)

            # Save to cache directory
            img_path = os.path.join(cls._cache_dir, f"{cache_key}.png")
            fig.savefig(img_path, format='png', bbox_inches='tight', pad_inches=0.1,
                       facecolor='none', edgecolor='none', transparent=True, dpi=dpi)
            plt.close(fig)

            # Cache the path
            cls._cache[cache_key] = img_path

            return img_path

        except Exception as e:
            print(f"Error rendering LaTeX '{latex_expr}': {e}")
            raise

    @classmethod
    def process_html(cls, html_content: str, theme: str = "dark") -> str:
        r"""
        Process HTML content and replace LaTeX expressions with rendered images.

        Supports display math: $$...$$ and \[...\] (both escaped and unescaped) and [ ... ]
        Supports inline math: $...$ and \(...\) (both escaped and unescaped)

        Args:
            html_content: HTML content with LaTeX expressions
            theme: "dark" or "light" theme for text color

        Returns:
            HTML with LaTeX expressions replaced by image file references
        """

        # Process display math \[...\] (escaped form from raw input)
        display_math_bracket_escaped = r'\\\[(.+?)\\\]'
        html_content = cls._replace_latex_matches(
            html_content, display_math_bracket_escaped, is_inline=False
        )

        # Process display math [ ... ] with optional spaces (unescaped from markdown, or model output)
        # Only match if it contains LaTeX-like content (backslash commands)
        display_math_bracket_pattern = r'\[\s*(\\[a-zA-Z].+?)\s*\]'
        html_content = cls._replace_latex_matches(
            html_content, display_math_bracket_pattern, is_inline=False
        )

        # Process display math ($$...$$)
        display_math_pattern = r'\$\$(.+?)\$\$'
        html_content = cls._replace_latex_matches(
            html_content, display_math_pattern, is_inline=False
        )

        # Process inline math \(...\) (escaped form from raw input)
        inline_math_paren_escaped = r'\\\((.+?)\\\)'
        html_content = cls._replace_latex_matches(
            html_content, inline_math_paren_escaped, is_inline=True
        )

        # Process inline math (...) with optional spaces (unescaped from markdown)
        # Only match if contains LaTeX-like content (starts with backslash command)
        inline_math_paren_pattern = r'\(\s*(\\[a-zA-Z].+?)\s*\)'
        html_content = cls._replace_latex_matches(
            html_content, inline_math_paren_pattern, is_inline=True
        )

        # Process inline math ($...$) last (lowest priority)
        # Use negative lookbehind/lookahead to avoid matching $$
        inline_math_pattern = r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)'
        html_content = cls._replace_latex_matches(
            html_content, inline_math_pattern, is_inline=True
        )

        return html_content

    @classmethod
    def _replace_latex_matches(cls, html_content: str, pattern: str, is_inline: bool) -> str:
        """
        Replace LaTeX matches in HTML content with rendered images.

        Args:
            html_content: The HTML content
            pattern: Regex pattern to find LaTeX expressions
            is_inline: Whether these are inline expressions

        Returns:
            HTML with LaTeX replaced by image file references
        """
        def replace_func(match):
            latex_expr = match.group(1).strip()

            # Skip empty expressions
            if not latex_expr:
                return match.group(0)

            try:
                # Render the LaTeX to image
                img_path = cls._render_latex_to_png(latex_expr, is_inline)

                # Convert to file:// URL for QTextBrowser compatibility
                # Use QUrl formatting
                file_url = f"file://{img_path}"

                # Create HTML img tag with file URL
                # Display at natural size, but shrink if it exceeds bubble width
                # Get image dimensions to set explicit width/height
                from PIL import Image
                img = Image.open(img_path)
                img_width, img_height = img.size

                # Bubble max width is 600px, account for padding (36px total)
                bubble_content_width = 600 - 36

                # Only apply max-width if image exceeds bubble width
                if img_width > bubble_content_width:
                    scale_ratio = bubble_content_width / img_width
                    scaled_width = int(bubble_content_width)
                    scaled_height = int(img_height * scale_ratio)
                    max_width_style = f"max-width: 100%; width: {scaled_width}px; height: {scaled_height}px;"
                else:
                    # Keep natural size
                    max_width_style = f"width: {img_width}px; height: {img_height}px;"

                if is_inline:
                    img_tag = f'<img src="{file_url}" style="vertical-align: middle; {max_width_style} margin: 0 3px; display: inline-block;">'
                else:
                    img_tag = f'<div style="text-align: center; margin: 10px 0; display: block;"><img src="{file_url}" style="{max_width_style} display: block; margin: 0 auto;"></div>'

                return img_tag

            except Exception as e:
                # If rendering fails, try to render with simplified expression
                # This handles unsupported commands like \boxed by stripping them
                simplified_expr = latex_expr

                # Strip all \boxed{...} wrappers - handle nested/incomplete cases
                # Use brace counting for proper extraction (regex can't handle nested braces)
                while '\\boxed' in simplified_expr:
                    boxed_pos = simplified_expr.find('\\boxed{')
                    if boxed_pos == -1:
                        break

                    # Start counting braces after the opening {
                    brace_start = boxed_pos + len('\\boxed')
                    brace_count = 0
                    content_start = brace_start + 1
                    content_end = content_start

                    # Count braces to find the matching closing }
                    for i in range(content_start, len(simplified_expr)):
                        if simplified_expr[i] == '{':
                            brace_count += 1
                        elif simplified_expr[i] == '}':
                            if brace_count == 0:
                                # Found the matching closing brace
                                content_end = i
                                break
                            else:
                                brace_count -= 1
                    else:
                        # Reached end without finding closing brace - incomplete
                        simplified_expr = simplified_expr[:boxed_pos] + simplified_expr[brace_start + 1:]
                        continue

                    # Extract content and replace \boxed{...} with just the content
                    boxed_content = simplified_expr[content_start:content_end]
                    simplified_expr = simplified_expr[:boxed_pos] + boxed_content + simplified_expr[content_end + 1:]

                # Strip \text{...} and keep spacing
                simplified_expr = re.sub(r'\\text\{[^}]*\}', 'text', simplified_expr)

                # Strip \quad commands and replace with space
                simplified_expr = re.sub(r'\\quad', ' ', simplified_expr)
                simplified_expr = re.sub(r'\\qquad', '  ', simplified_expr)

                # Clean up multiple spaces
                simplified_expr = re.sub(r' +', ' ', simplified_expr)

                # Don't strip trailing braces - they may be part of valid LaTeX expressions
                simplified_expr = simplified_expr.strip()

                if simplified_expr and simplified_expr != latex_expr:
                    try:
                        img_path = cls._render_latex_to_png(simplified_expr, is_inline)
                        file_url = f"file://{img_path}"

                        # Get image dimensions
                        from PIL import Image
                        img = Image.open(img_path)
                        img_width, img_height = img.size

                        # Bubble max width is 600px, account for padding (36px total)
                        bubble_content_width = 600 - 36

                        # Only apply max-width if image exceeds bubble width
                        if img_width > bubble_content_width:
                            scale_ratio = bubble_content_width / img_width
                            scaled_width = int(bubble_content_width)
                            scaled_height = int(img_height * scale_ratio)
                            max_width_style = f"max-width: 100%; width: {scaled_width}px; height: {scaled_height}px;"
                        else:
                            # Keep natural size
                            max_width_style = f"width: {img_width}px; height: {img_height}px;"

                        if is_inline:
                            img_tag = f'<img src="{file_url}" style="vertical-align: middle; {max_width_style} margin: 0 3px; display: inline-block;">'
                        else:
                            img_tag = f'<div style="text-align: center; margin: 10px 0; display: block;"><img src="{file_url}" style="{max_width_style} display: block; margin: 0 auto;"></div>'
                        return img_tag
                    except Exception as fallback_e:
                        pass

                # If all else fails, return original expression as plain text (don't crash)
                return match.group(0)

        return re.sub(pattern, replace_func, html_content, flags=re.DOTALL)
