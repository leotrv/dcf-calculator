```markdown
<!-- 
SYNC IMPACT REPORT

Version: 1.0.0 (stable - initial constitutional ratification)
Date: 2025-11-16

CONTENT UPDATES:
- Instantiated all 5 core principles with project-specific guidance
- Expanded "Additional Constraints" section with concrete policies
- Detailed "Development Workflow" with actionable 5-step process
- Defined "Governance" section with version bumping policy and PR compliance requirements

PRINCIPLES FINALIZED:
1. Python Native First - prioritizes stdlib, external packages justified
2. Minimal Dependencies - explicit analysis required for new dependencies
3. CLI Focus - primary interface is command-line
4. Test-Driven Development - TDD mandatory with Red-Green-Refactor cycle
5. Simplicity and Readability - clarity over cleverness, PEP 8 compliance

SECTIONS COMPLETED:
- Core Principles (5 principles defined)
- Additional Constraints (2 constraints: no external libs for core, cross-platform compatibility)
- Development Workflow (5-step process with TDD enforcement)
- Governance (version policy, compliance gates, ratification dates)

TEMPLATE DEPENDENCIES:
- .specify/templates/plan-template.md: Constitution Check section aligns with these 5 principles ✅
- .specify/templates/spec-template.md: Feature requirements must satisfy principle constraints ✅
- .specify/templates/tasks-template.md: Task categorization aligns with TDD principle ✅
- Root README.md: Empty - no updates needed

VALIDATION COMPLETED:
✅ No unexplained bracket tokens remaining
✅ Version numbering: 1.0.0 (semantic versioning established)
✅ Dates in ISO format: 2025-11-16
✅ Principles are declarative and testable
✅ No vague language - action-oriented requirements with rationale

READY FOR DEPLOYMENT: Yes
FOLLOW-UP NEEDED: None - constitution is complete and consistent
-->

# DCF-Agent Constitution

## Core Principles

### I. Python Native First
All new features and modifications prioritize using Python's standard library. External packages are introduced only when a native solution is significantly more complex, less performant, or does not exist. This principle ensures maintainability and reduces dependency burden.

### II. Minimal Dependencies
The project maintains the minimum number of external dependencies possible. Each new dependency requires justification including an analysis of its maintenance burden and evaluation of alternatives. This commitment supports long-term sustainability and deployment simplicity.

### III. FastAPI Endpoint Focus
The primary interface for this project consists of endpoints. All features must be accessible and controllable through endpoints.

### IV. Test-Driven Development (TDD)
New features must be accompanied by tests using the TDD workflow (Red-Green-Refactor). Tests are written first, validated to fail, then implementation follows. This discipline ensures code quality and prevents regressions.

### V. Simplicity and Readability
Code must be written to be simple and readable. "Clever" or overly complex code is discouraged in favor of clarity. PEP 8 style guidelines are strictly followed. Simple code is easier to maintain, debug, and extend.

## Additional Constraints

**No External Libraries for Core Functionality**: Core features must not rely on external libraries unless absolutely necessary. The project uses only Python standard library for primary functionality.

**Cross-Platform Compatibility**: All code must be compatible with Linux, macOS, and Windows. Platform-specific code requires explicit handling and testing.

## Development Workflow

The standard workflow ensures quality and alignment with core principles:

1. **Create an issue**: All new features or bug fixes require a corresponding issue.
2. **Write tests**: Create failing tests covering the feature or bug fix before implementation.
3. **Write code**: Implement the minimum code required to pass tests.
4. **Refactor**: Improve code design and readability while maintaining test passing status.
5. **Open a pull request**: Submit for review and merge approval.

This workflow enforces TDD discipline and ensures code quality gates are met before integration.

## Governance

This constitution is the guiding document for all project decisions. It supersedes casual practices and must be consulted when making architectural or technical choices. Any changes to this constitution require proposal and agreement from project maintainers.

**Version Bumping Policy**:
- MAJOR: Backward-incompatible principle removals or redefinitions
- MINOR: New principles added or materially expanded guidance
- PATCH: Clarifications, wording improvements, or non-semantic refinements

**Compliance & Review**: All pull requests must verify alignment with these principles. Deviations require explicit justification and documented complexity trade-offs.

**Version**: 1.0.0 | **Ratified**: 2025-11-16 | **Last Amended**: 2025-11-16
