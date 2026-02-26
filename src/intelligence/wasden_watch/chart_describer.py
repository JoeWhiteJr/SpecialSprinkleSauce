"""Uses Claude Vision API to describe charts/images found in PDFs."""

import base64
import itertools
import logging
import time
from pathlib import Path

import fitz  # pymupdf

logger = logging.getLogger("wasden_watch")


class ChartDescriber:
    """Extracts images from PDFs and describes them using Claude Vision."""

    def __init__(self, api_keys: list[str], model: str = "claude-sonnet-4-20250514"):
        self._model = model
        self._key_cycle = itertools.cycle(api_keys) if api_keys else None
        self._last_request_time: float = 0.0

    def describe_charts(self, pdf_path: Path) -> list[str]:
        """Extract images from a PDF and describe each using Claude Vision.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of text descriptions of charts/images found.
        """
        if self._key_cycle is None:
            logger.warning("No Claude API keys configured, skipping chart description")
            return []

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            logger.warning(f"Failed to open PDF for chart extraction: {e}")
            return []

        descriptions: list[str] = []

        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                image_list = page.get_images(full=True)

                for img_index, img_info in enumerate(image_list):
                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]

                        # Skip very small images (likely icons/logos)
                        if len(image_bytes) < 5000:
                            continue

                        description = self._describe_image(image_bytes)
                        if description:
                            descriptions.append(description)
                    except Exception as e:
                        logger.warning(
                            f"Error extracting image {img_index} from page {page_num} "
                            f"of {pdf_path.name}: {e}"
                        )
                        continue

            except Exception as e:
                logger.warning(f"Error processing page {page_num} of {pdf_path.name}: {e}")
                continue

        doc.close()
        logger.info(f"Described {len(descriptions)} charts from {pdf_path.name}")
        return descriptions

    def _describe_image(self, image_bytes: bytes) -> str:
        """Send an image to Claude Vision for description.

        Args:
            image_bytes: Raw image bytes.

        Returns:
            Text description of the image, or empty string on failure.
        """
        if self._key_cycle is None:
            return ""

        # Rate limiting: 1 request per second
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        try:
            import anthropic

            key = next(self._key_cycle)
            client = anthropic.Anthropic(api_key=key)

            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            message = client.messages.create(
                model=self._model,
                max_tokens=512,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    "Describe this financial chart or image from an investment newsletter. "
                                    "Focus on: the type of chart, what data it shows, key trends, "
                                    "notable data points, and any text labels or annotations. "
                                    "Be concise but thorough."
                                ),
                            },
                        ],
                    }
                ],
            )

            self._last_request_time = time.time()
            return message.content[0].text

        except Exception as e:
            logger.warning(f"Chart description failed: {e}")
            self._last_request_time = time.time()
            return ""
