"""
Prompt template registry for LangChain tasks.

This registry manages prompt templates with auto-discovery from YAML files.
"""

import logging
import importlib
import yaml
from pathlib import Path
from typing import Dict, Optional, Any


class PromptRegistry:
    """
    Registry for prompt templates with auto-discovery.
    
    Automatically discovers and loads prompt templates from YAML files
    in the templates directory.
    """
    
    def __init__(self):
        """Initialize the prompt template registry."""
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._logger = logging.getLogger("langchain_tasks.prompts.registry")
        
        # Auto-discover prompt templates
        self._auto_discover_templates()
    
    def _auto_discover_templates(self):
        """Auto-discover prompt templates from the templates package."""
        try:
            # Import the templates package using relative import
            templates_package = importlib.import_module(".templates", package="src.hex_machina.langchain_tasks.prompts")
            
            # Get the package path
            package_path = Path(templates_package.__file__).parent
            
            # Discover YAML files in the package
            for yaml_file in package_path.glob("*.yaml"):
                try:
                    # Load the YAML file
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        template_data = yaml.safe_load(f)
                    
                    # Validate required fields
                    if self._validate_template(template_data):
                        template_name = template_data["name"]
                        self._templates[template_name] = template_data
                        self._logger.info(f"Auto-discovered prompt template: {template_name}")
                    else:
                        self._logger.warning(f"Invalid prompt template in {yaml_file.name}")
                        
                except Exception as e:
                    self._logger.warning(f"Failed to load prompt template from {yaml_file.name}: {e}")
                    
        except Exception as e:
            self._logger.warning(f"Failed to auto-discover prompt templates: {e}")
    
    def _validate_template(self, template_data: Dict[str, Any]) -> bool:
        """Simple validation of template data.
        
        Args:
            template_data: Template data from YAML file
            
        Returns:
            True if template is valid, False otherwise
        """
        required_fields = ["name", "description", "template"]
        
        for field in required_fields:
            if field not in template_data:
                return False
        
        return True
    
    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a prompt template by name.
        
        Args:
            name: Name of the prompt template
            
        Returns:
            Template data if found, None otherwise
        """
        return self._templates.get(name)
    
    def list_templates(self) -> Dict[str, str]:
        """List all available prompt templates.
        
        Returns:
            Dictionary mapping template names to descriptions
        """
        return {name: template["description"] for name, template in self._templates.items()}
    
    def template_exists(self, name: str) -> bool:
        """Check if a template exists.
        
        Args:
            name: Name of the prompt template
            
        Returns:
            True if template exists, False otherwise
        """
        return name in self._templates


# Global registry instance
prompt_registry = PromptRegistry()
