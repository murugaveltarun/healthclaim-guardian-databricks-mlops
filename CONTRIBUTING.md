# Contributing to Healthclaim Guardian

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Commit Messages](#commit-messages)
- [Pull Requests](#pull-requests)
- [Code Review](#code-review)

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Welcome newcomers and help them learn
- Keep discussions professional and on-topic

---

## Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/your-username/healthclaim_guardian.git
cd healthclaim_guardian
```

### 2. Set Up Development Environment

```bash
# Install dependencies
uv sync --dev

# Configure pre-commit hooks
uv run pre-commit install
```

### 3. Create a Branch

```bash
# Feature branch
git checkout -b feature/your-feature-name

# Bug fix branch
git checkout -b fix/issue-123
```

---

## Development Workflow

### 1. Make Changes

- Write code following the coding standards
- Add tests for new functionality
- Update documentation as needed

### 2. Run Tests Locally

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_validation.py -v

# Run linting
uv run ruff check src/ tests/
uv run black --check src/ tests/
uv run mypy src/
```

### 3. Commit Changes

```bash
# Stage changes
git add <files>

# Commit with conventional commit message
git commit -m "feat: add new feature"
```

### 4. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
```

---

## Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://black.readthedocs.io/) for formatting
- Use [isort](https://pycqa.github.io/isort/) for imports
- Maximum line length: 100 characters

### Type Hints

Use type hints for all function signatures:

```python
# Good
def calculate_risk(score: float) -> str:
    if score > 0.7:
        return "HIGH"
    return "LOW"

# Avoid
def calculate_risk(score):
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def process_claim(claim_id: str, amount: float) -> dict:
    """
    Process a single insurance claim.

    Args:
        claim_id: Unique identifier for the claim
        amount: Billed amount in dollars

    Returns:
        Dictionary with processing results

    Raises:
        ValueError: If claim_id is empty
    """
    ...
```

### Error Handling

```python
# Good: Specific exception handling
try:
    result = process_claim(claim_id, amount)
except ValueError as e:
    logger.error(f"Invalid claim data: {e}")
    return None
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise

# Avoid: Bare except
try:
    result = process_claim(claim_id, amount)
except:
    print("Error occurred")
```

### Logging

```python
from healthclaim_guardian.logging_config import setup_logger

logger = setup_logger(__name__)

# Use appropriate log levels
logger.debug("Debug information for troubleshooting")
logger.info("Normal operational message")
logger.warning("Something unexpected but handled")
logger.error("An error occurred")
logger.critical("Critical issue requiring attention")
```

---

## Testing

### Test Structure

```python
import pytest
from unittest.mock import Mock

class TestYourFeature:
    """Tests for your feature."""

    def test_happy_path(self):
        """Test the normal case."""
        result = your_function(input_data)
        assert result == expected_output

    def test_edge_case(self):
        """Test edge cases."""
        with pytest.raises(ValueError):
            your_function(invalid_input)

    def test_mock_external_dependency(self):
        """Test with mocked dependencies."""
        mock_dep = Mock()
        mock_dep.method.return_value = "mocked_value"

        result = your_function(mock_dep)
        assert result is not None
```

### Coverage Requirements

- New code: >= 80% coverage
- Critical paths: >= 90% coverage
- All public APIs must have tests

### Running Tests

```bash
# All tests
uv run pytest

# Tests with coverage report
uv run pytest --cov=src --cov-report=html --cov-report=term-missing

# Fail if coverage drops below threshold
uv run pytest --cov=src --cov-fail-under=80
```

---

## Documentation

### README Updates

Update README.md when:
- Adding new features
- Changing configuration
- Modifying installation steps
- Adding/removing dependencies

### Code Comments

```python
# Good: Explains WHY, not WHAT
# Using StandardScaler because K-Means is sensitive to feature scales
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Avoid: Redundant comment
# Increment counter by 1
counter = counter + 1
```

### API Documentation

Update `docs/API.md` when:
- Adding new public functions
- Changing function signatures
- Adding/removing configuration options

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Examples

```bash
# Feature
feat: add model registry integration

# Bug fix
fix: resolve null pointer in feature engineering

# Documentation
docs: update setup instructions

# Refactor
refactor: extract validation logic to separate module

# Test
test: add unit tests for bronze ingestion
```

---

## Pull Requests

### PR Template

```markdown
## Summary
Brief description of changes

## Changes
- [ ] Added feature X
- [ ] Fixed bug Y
- [ ] Updated documentation

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added for new functionality
```

### PR Size

- Keep PRs small and focused (< 400 lines)
- Split large changes into multiple PRs
- Each PR should be reviewable in < 30 minutes

---

## Code Review

### Reviewer Guidelines

- Review within 24 hours
- Be constructive and respectful
- Explain reasoning for suggestions
- Approve when requirements are met

### Review Checklist

- [ ] Code follows coding standards
- [ ] Tests cover new functionality
- [ ] Documentation is updated
- [ ] No security vulnerabilities introduced
- [ ] Error handling is appropriate
- [ ] Logging is adequate

### Addressing Feedback

```bash
# After making changes
git add <files>
git commit -m "fix review comments"
git push

# For significant changes, consider squashing
git rebase -i main
```

---

## Release Process

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

### Release Steps

1. Update CHANGELOG.md
2. Update version in pyproject.toml
3. Create release tag
4. Deploy to production

---

## Questions?

- Check existing issues on GitHub
- Ask in Slack: #healthclaim-guardian
- Email: ml-team@synergech.com

---

## Recognition

Contributors will be acknowledged in:
- CHANGELOG.md
- README.md (Contributors section)
- Release notes

Thank you for contributing! 🎉
