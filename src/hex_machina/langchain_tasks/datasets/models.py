"""
Dataset models for LangChain tasks.

This module defines the data structures for managing step-range datasets
and examples with run_id grouping.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DatasetExample(BaseModel):
    """An example to be added to a dataset."""

    inputs: Dict[str, Any] = Field(description="Input data for the step")
    outputs: Dict[str, Any] = Field(description="Output data from the step")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata including run_id, step_name, etc.",
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="When this example was created"
    )


class DatasetDefinition(BaseModel):
    """Configuration for a dataset that spans multiple steps."""

    name: str = Field(..., description="Name of the dataset")
    description: Optional[str] = Field(default=None, description="Dataset description")
    input_step: str = Field(..., description="Step name that provides the input data")
    output_step: str = Field(..., description="Step name that provides the output data")
    enabled: bool = Field(default=True, description="Whether this dataset is enabled")
