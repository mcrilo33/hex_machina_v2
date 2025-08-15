"""
Annotation models for dataset annotation sessions.

This module defines the data structures for configuring and managing
interactive dataset annotation sessions.
"""

from typing import Dict, List, Union

from pydantic import BaseModel, Field


class AnnotationField(BaseModel):
    """Configuration for an annotation field."""

    name: str = Field(..., description="Name of the annotation field")
    field_type: str = Field(..., description="Type of annotation field")
    options: Union[List[str], str] = Field(
        ..., description="Available options or field type description"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "examples": [
                {
                    "name": "article_text_quality",
                    "field_type": "categorical",
                    "options": ["high", "medium", "low"],
                },
                {"name": "notes", "field_type": "free_text", "options": "free_text"},
                {
                    "name": "outputs['generations'][0][0]['text']",
                    "field_type": "replace",
                    "options": "free_text",
                },
            ]
        }


class AnnotationSession(BaseModel):
    """Configuration for a dataset annotation session."""

    name: str = Field(..., description="Name of the annotation session")
    description: str = Field(..., description="Description of the annotation session")

    dataset: Dict[str, str] = Field(..., description="Dataset configuration")

    display_fields: Dict[str, List[str]] = Field(
        ..., description="Fields to display for inputs and outputs"
    )

    annotation_fields: Dict[str, List[AnnotationField]] = Field(
        ..., description="Fields to annotate for inputs and outputs"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "examples": [
                {
                    "name": "article_completeness_annotation",
                    "description": "Annotate article completeness examples",
                    "dataset": {
                        "name": "article_completeness_dataset",
                        "split": "train",
                    },
                    "display_fields": {
                        "inputs": [
                            "article_text",
                            "article_url",
                            "metadata['source_domain']",
                        ],
                        "outputs": ["is_complete", "reasoning"],
                    },
                    "annotation_fields": {
                        "inputs": [
                            {
                                "name": "article_text_quality",
                                "field_type": "categorical",
                                "options": ["high", "medium", "low"],
                            }
                        ],
                        "outputs": [
                            {
                                "name": "annotation_confidence",
                                "field_type": "categorical",
                                "options": ["high", "medium", "low"],
                            }
                        ],
                    },
                }
            ]
        }


class AnnotationConfig(BaseModel):
    """Root configuration for annotation sessions."""

    annotation_session: AnnotationSession = Field(
        ..., description="Annotation session configuration"
    )
