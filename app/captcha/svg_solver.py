import re
import logging

logger = logging.getLogger(__name__)


class SvgCaptchaSolver:
    """
    Regex-based SVG captcha solver.
    Ported from C# SVGCaptchaSolver.
    """

    # TODO: COPY NGUYÊN GetListPathAllKeywords() TỪ C# SANG ĐÂY
    PATH_KEYWORDS = [
        "MQQQQQZMQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQZMQQZ",
        "MQQQQQQQQQZMQQQQQQZMQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQZMQQQQQQQQZMQQQQQQQQZ",
        "MQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQZ",
        "MQQQQQQQQZMQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQZ",
        "MQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQZ",
        "MQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQZ",
        "MQQQQQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ",
        "MQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQZ",
        "",
        "MQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQZ",
        "MQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQZ",
        "",
        "MQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQZ",
        "MQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQZ",
        "",
        "MQQQQQQZMQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQZ",
        "MQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQZ",
        "MQQQQQQZMQQQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQZ",
        "MQQQQQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ",
        "MQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQZ",
        "",
        "MQQQQQQQQQQZMQQQQQQQQQQQQQQQQZ",
        "MQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQZ",
        "MQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQZ",
        "MQQQQQQQQQZMQQQQQQQQQQQQQZ",
        "MQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQZ",
        "",
        "",
        "MQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ",
        "MQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ",
        "MQQQQZMQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQZMQQQQQZ",
        "MQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ",
        "MQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQZ",
        "MQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQZ",
        "MQQQQQQQQZMQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQZMQQQQQQQZ",
        "MQQQQQQQQZMQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQZ"
        # ...
    ]

    PATH_REGEX = re.compile(r'([MQZ])([^MQZ]*)')

    def solve(self, svg_text: str) -> str:
        if not svg_text:
            logger.warning("Empty SVG captcha")
            return ""

        results = []

        # Split SVG by path definitions
        parts = svg_text.split(' d="')[1:]

        logger.debug("Found %d path segments", len(parts))

        for part in parts:
            try:
                path_data = part.split('"', 1)[0]

                # Simplify path: keep only M/Q/Z
                simplified = self.PATH_REGEX.sub(r'\1', path_data)

                if simplified not in self.PATH_KEYWORDS:
                    logger.debug("Unknown path pattern: %s", simplified)
                    continue

                index = self.PATH_KEYWORDS.index(simplified)

                # Map index to character
                if index < 26:
                    char = chr(ord('A') + index)
                else:
                    char = str(index - 26)

                # Extract X position from first match
                matches = self.PATH_REGEX.findall(path_data)
                if not matches:
                    x_pos = 0.0
                else:
                    coord_part = matches[0][1].strip()
                    x_pos = float(coord_part.split()[0].split(",")[0])

                results.append((x_pos, char))

            except Exception as e:
                logger.exception("Failed to process path segment: %s", e)

        if not results:
            logger.error("Captcha solving failed: no characters detected")
            return ""

        # Sort by X position
        results.sort(key=lambda x: x[0])

        captcha = "".join(char for _, char in results)

        logger.info("Solved captcha: %s", captcha)
        return captcha
