"""
Core business logic and models.

This module provides template functionality with Pydantic models
and demonstrates clean architecture patterns for package development.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from domain_tracker.settings import Settings

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class ProcessingRequest(BaseModel):
    """Request model for text processing operations."""

    input_data: str = Field(
        description="Input text data to be processed",
    )
    transform_type: str = Field(
        default="uppercase",
        description="Type of transformation to apply to the input",
    )


class ProcessingResult(BaseModel):
    """Result model for text processing operations."""

    output_data: str = Field(
        description="Processed output text data",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the processing operation",
    )
    success: bool = Field(
        default=True,
        description="Whether the processing operation succeeded",
    )


class MyPackage:
    """
    Main interface class for text processing operations.

    This class demonstrates clean architecture patterns and serves as
    the primary API for the package's text transformation functionality.

    Example:
        >>> settings = Settings(whois_api_key="key", slack_webhook_url="url")
        >>> package = MyPackage(settings)
        >>> result = package.process("hello world")
        >>> print(result.output_data)  # "HELLO WORLD"
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize the package with required settings.

        Args:
            settings: Configuration settings for the package. Must be provided.

        Raises:
            ValueError: If settings is None.
        """
        if settings is None:
            raise ValueError("Settings must be provided")
        self.settings = settings
        logger.debug("MyPackage initialized successfully")

    def process(
        self, input_data: str, transform_type: str = "uppercase"
    ) -> ProcessingResult:
        """
        Process input text with the specified transformation.

        Args:
            input_data: Raw text data to be processed.
            transform_type: Type of transformation to apply ('uppercase', 'lowercase',
                          'title', 'reverse', 'capitalize').

        Returns:
            ProcessingResult containing the processed data and metadata.
        """
        logger.info(f"Processing input with transform: {transform_type}")

        request = ProcessingRequest(
            input_data=input_data,
            transform_type=transform_type,
        )

        try:
            result = self._apply_transformation(request)
            logger.info("Processing completed successfully")
            return result

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return ProcessingResult(
                output_data="",
                success=False,
                metadata={"error": str(e)},
            )

    def _apply_transformation(self, request: ProcessingRequest) -> ProcessingResult:
        """
        Apply the requested transformation to the input data.

        Args:
            request: Processing request containing input data and transform type.

        Returns:
            ProcessingResult with transformed data and metadata.

        Raises:
            ValueError: If transform_type is not supported.
        """
        # Available transformations
        available_transforms = {
            "uppercase": str.upper,
            "lowercase": str.lower,
            "title": str.title,
            "reverse": lambda x: x[::-1],
            "capitalize": str.capitalize,
        }

        if request.transform_type not in available_transforms:
            supported_types = ", ".join(available_transforms.keys())
            raise ValueError(
                f"Unsupported transform_type: '{request.transform_type}'. "
                f"Supported types: {supported_types}"
            )

        transform_function = available_transforms[request.transform_type]
        output_data = transform_function(request.input_data)

        return ProcessingResult(
            output_data=output_data,
            metadata={
                "transform_type": request.transform_type,
                "input_length": len(request.input_data),
                "output_length": len(output_data),
            },
        )

    def get_package_info(self) -> dict[str, Any]:
        """
        Get package information and statistics.

        Returns:
            Dictionary containing package version and settings information.
        """
        from domain_tracker import __version__

        return {
            "version": __version__,
            "settings": self.settings.model_dump(),
        }
