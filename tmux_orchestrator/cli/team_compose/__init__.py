"""Team composition module - backwards compatibility layer.

This module maintains full backwards compatibility with the original team_compose.py
while providing a modular, SOLID-principle-compliant architecture.
"""

# Import all functions and classes from the original module to maintain compatibility
from .commands import compose, deploy, list_templates, status, team
from .composer import (
    determine_project_type as _determine_project_type,
)
from .composer import (
    generate_interaction_diagram as _generate_interaction_diagram,
)
from .composer import (
    generate_system_prompt as _generate_system_prompt,
)
from .composer import (
    generate_team_composition as _generate_team_composition,
)
from .composer import (
    interactive_team_composition as _interactive_team_composition,
)
from .composer import (
    suggest_team_composition as _suggest_team_composition,
)
from .deployer import (
    deploy_team,
    generate_system_prompt,
    show_team_status,
)
from .template_manager import (
    TEAM_TEMPLATE,
    TEMPLATES_DIR,
    load_agent_templates,
)
from .template_manager import (
    get_default_team_template as _get_default_team_template,
)
from .template_manager import (
    load_team_template as _load_team_template,
)
from .validators import (
    sanitize_for_template as _sanitize_for_template,
)
from .validators import (
    validate_prd_path,
    validate_project_exists,
    validate_project_name,
)

# Maintain original function names for backwards compatibility
__all__ = [
    # CLI commands (main interface)
    "team",
    "compose",
    "deploy",
    "list_templates",
    "status",
    # Core functionality
    "_interactive_team_composition",
    "_suggest_team_composition",
    "_generate_team_composition",
    "_generate_system_prompt",
    "_generate_interaction_diagram",
    "_determine_project_type",
    "_get_default_team_template",
    "_load_team_template",
    "_sanitize_for_template",
    # Public API
    "load_agent_templates",
    "validate_project_name",
    "validate_project_exists",
    "validate_prd_path",
    "deploy_team",
    "show_team_status",
    "generate_system_prompt",
    # Constants
    "TEMPLATES_DIR",
    "TEAM_TEMPLATE",
]


# For any imports that expect the original structure
def __getattr__(name: str):
    """Dynamic attribute access for backwards compatibility."""
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
