"""PRD analysis and team composition suggestion utilities."""

from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


def analyze_prd_for_team_composition(prd_path: Path) -> tuple[str, int, dict[str, Any]]:
    """Analyze PRD content to suggest optimal team type and size.

    This provides intelligent suggestions based on PRD content analysis,
    but the actual implementation plan is created by the PM agent who
    reads and interprets the full PRD document.

    Returns:
        Tuple of (team_type, team_size, tech_analysis)
    """
    try:
        prd_content = prd_path.read_text()
    except Exception:
        # Default if can't read
        return (
            "fullstack",
            5,
            {
                "error": "Could not read PRD",
                "frontend_score": 0,
                "backend_score": 0,
                "complexity": "medium",
                "requires_qa": False,
                "requires_devops": False,
            },
        )

    console.print("[blue]Analyzing PRD to suggest optimal team composition...[/blue]")

    # This is just a suggestion based on keywords - the PM agent
    # will do the actual PRD interpretation and task creation
    prd_lower = prd_content.lower()

    # Technology detection for team type suggestion
    frontend_keywords = ["ui", "ux", "react", "vue", "angular", "frontend", "css", "html", "javascript", "typescript"]
    backend_keywords = ["api", "database", "server", "backend", "python", "java", "node", "sql", "redis"]
    testing_keywords = ["test", "qa", "quality", "automation", "pytest", "jest", "selenium"]
    devops_keywords = ["deploy", "docker", "kubernetes", "ci/cd", "aws", "cloud", "infrastructure"]

    # Count technology mentions (just for suggestion)
    frontend_score = sum(1 for keyword in frontend_keywords if keyword in prd_lower)
    backend_score = sum(1 for keyword in backend_keywords if keyword in prd_lower)
    testing_score = sum(1 for keyword in testing_keywords if keyword in prd_lower)
    devops_score = sum(1 for keyword in devops_keywords if keyword in prd_lower)

    # Complexity estimation (just a heuristic)
    line_count = len(prd_content.split("\n"))
    word_count = len(prd_content.split())

    if word_count > 2000 or line_count > 100:
        complexity = "high"
        base_team_size = 5
    elif word_count > 1000 or line_count > 50:
        complexity = "medium"
        base_team_size = 4
    else:
        complexity = "low"
        base_team_size = 3

    # Team type suggestion based on scores
    if frontend_score > backend_score * 1.5:
        team_type = "frontend"
    elif backend_score > frontend_score * 1.5:
        team_type = "backend"
    elif testing_score > 5:
        team_type = "testing"
    else:
        team_type = "fullstack"

    # Adjust team size based on requirements
    team_size = base_team_size
    if testing_score > 3:
        team_size += 1  # Add QA engineer
    if devops_score > 3:
        team_size += 1  # Add DevOps engineer

    # Cap team size
    team_size = min(team_size, 8)

    tech_analysis = {
        "frontend_score": frontend_score,
        "backend_score": backend_score,
        "testing_score": testing_score,
        "devops_score": devops_score,
        "complexity": complexity,
        "requires_qa": testing_score > 3,
        "requires_devops": devops_score > 3,
    }

    return team_type, team_size, tech_analysis


def extract_section(content: str, keywords: list[str]) -> str:
    """Extract a section from PRD content based on keywords.

    Args:
        content: PRD content
        keywords: Keywords to search for section headers

    Returns:
        Extracted section content or empty string
    """
    lines = content.split("\n")
    section_lines = []
    in_section = False

    for line in lines:
        line_lower = line.lower()
        # Check if we're starting a relevant section
        if any(keyword in line_lower for keyword in keywords):
            in_section = True
            section_lines.append(line)
        elif in_section:
            # Check if we're starting a new section (common markdown headers)
            if line.startswith("#") or line.startswith("##") or line.startswith("###"):
                break
            section_lines.append(line)

    return "\n".join(section_lines) if section_lines else ""
