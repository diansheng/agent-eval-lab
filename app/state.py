from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json

@dataclass
class Issue:
    """Represents a single issue found during code review."""
    file_path: str
    description: str
    line_number: Optional[int] = None
    severity: str = "medium"  # low, medium, high, critical
    suggested_fix: Optional[str] = None

@dataclass
class AgentState:
    """
    The Memory Layer (State Object) for the Multi-Step Agent.
    This tracks the progress and data across the 4-step workflow:
    1. Gather -> 2. Review -> 3. Verify -> 4. Report
    """
    
    # --- Step 1: Gather ---
    pr_url: Optional[str] = None
    files_reviewed: List[str] = field(default_factory=list)
    
    # --- Step 2: Review ---
    issues_found: List[Issue] = field(default_factory=list)
    
    # --- Step 3: Verify ---
    verification_results: List[Issue] = field(default_factory=list)
    false_positives_discarded: int = 0
    
    # --- Workflow Tracking ---
    current_step: str = "initialize"
    
    # --- LLM Memory ---
    messages: List[Dict[str, str]] = field(default_factory=list)

    def add_issue(self, issue: Issue):
        """Helper to append a found issue."""
        self.issues_found.append(issue)

    def update_step(self, step_name: str):
        """Helper to transition workflow state."""
        self.current_step = step_name
        
    def to_json(self):
        """Convert state to a JSON string for persistence or debugging."""
        # Convert dataclass to dict, handling nested Issue dataclasses
        import dataclasses
        return json.dumps(dataclasses.asdict(self), indent=2)
