# Contributing to GCP HCP CLI

We welcome contributions to the GCP HCP CLI project! This document provides guidelines for contributing code, reporting issues, and suggesting improvements.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow. Please be respectful and constructive in all interactions.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment
4. Create a feature branch
5. Make your changes
6. Test your changes
7. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- Make (optional but recommended)

### Setup Steps

1. Clone your fork:
```bash
git clone https://github.com/YOUR_USERNAME/gcp-hcp-cli.git
cd gcp-hcp-cli
```

2. Set up development environment:
```bash
make setup-dev
```

This will:
- Install the package in development mode
- Install all development dependencies
- Set up pre-commit hooks

### Manual Setup (if Make is not available)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev,test,docs]"

# Install pre-commit hooks
pre-commit install
```

## Making Changes

### Branching Strategy

- Create feature branches from `main`
- Use descriptive branch names: `feature/add-nodepool-scaling`, `fix/auth-token-refresh`, `docs/improve-readme`
- Keep branches focused on a single feature or fix

### Development Workflow

1. Create a new branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes following the coding guidelines below

3. Test your changes:
```bash
make test
make lint
```

4. Commit your changes with descriptive messages:
```bash
git add .
git commit -m "Add nodepool scaling functionality

- Implement scale up/down commands
- Add validation for node count limits
- Update tests and documentation"
```

5. Push to your fork:
```bash
git push origin feature/your-feature-name
```

6. Create a pull request on GitHub

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run tests with coverage
pytest --cov=gcphcp --cov-report=html
```

### Writing Tests

- Write tests for all new functionality
- Maintain or improve test coverage (target: 85%+)
- Use descriptive test names and docstrings
- Mock external dependencies (API calls, file system, etc.)

#### Test Structure

```python
def test_function_name_behavior():
    """Test that function_name does something specific when condition."""
    # Arrange
    setup_data = create_test_data()

    # Act
    result = function_name(setup_data)

    # Assert
    assert result.expected_property == expected_value
```

### Test Categories

- **Unit tests**: Test individual functions and classes in isolation
- **Integration tests**: Test component interactions and API integration
- **End-to-end tests**: Test complete user workflows

## Code Style

### Python Code Standards

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [flake8](https://flake8.pycqa.org/) for linting
- Use [mypy](https://mypy.readthedocs.io/) for type checking

### Code Formatting

```bash
# Format code
make format

# Check formatting
black --check src tests

# Run linting
make lint

# Type checking
mypy src
```

### Type Hints

- Use type hints for all function parameters and return values
- Import types from `typing` module when needed
- Use `Optional[T]` for nullable types
- Use `Union[T1, T2]` for multiple possible types

```python
from typing import Dict, List, Optional, Union

def process_clusters(
    clusters: List[Dict[str, Any]],
    format_type: str = "table"
) -> Optional[str]:
    """Process cluster data and return formatted output."""
    ...
```

### Documentation

- Write docstrings for all public functions and classes
- Use Google-style docstrings
- Include examples in docstrings when helpful
- Keep comments concise and focused on "why" rather than "what"

```python
def create_cluster(name: str, project_id: str) -> Cluster:
    """Create a new cluster in the specified project.

    Args:
        name: Cluster name (must be DNS-compatible)
        project_id: Target GCP project ID

    Returns:
        Created cluster object

    Raises:
        ValidationError: If cluster name is invalid
        APIError: If cluster creation fails

    Example:
        >>> cluster = create_cluster("my-cluster", "my-project")
        >>> print(cluster.name)
        my-cluster
    """
    ...
```

## Submitting Changes

### Pull Request Guidelines

1. **Title**: Use a clear, descriptive title
2. **Description**: Explain what changes you made and why
3. **Testing**: Describe how you tested your changes
4. **Breaking Changes**: Clearly document any breaking changes
5. **Related Issues**: Reference any related GitHub issues

### Pull Request Template

```markdown
## Summary
Brief description of the changes

## Changes Made
- List of specific changes
- Another change
- etc.

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Documentation updated

## Breaking Changes
None / List any breaking changes

## Related Issues
Fixes #123
Related to #456
```

### Review Process

1. All pull requests require at least one review
2. Automated checks must pass (tests, linting, type checking)
3. Address review feedback promptly
4. Maintain a clean commit history (squash if necessary)

## Reporting Issues

### Bug Reports

When reporting bugs, please include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Exact steps to reproduce the bug
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: OS, Python version, CLI version
6. **Logs**: Relevant error messages or logs

### Feature Requests

When requesting features, please include:

1. **Use Case**: Why is this feature needed?
2. **Description**: Detailed description of the feature
3. **Examples**: How would the feature be used?
4. **Alternatives**: Any alternative solutions considered

### Issue Template

```markdown
## Issue Type
- [ ] Bug Report
- [ ] Feature Request
- [ ] Documentation Issue
- [ ] Question

## Description
Clear description of the issue or request

## Steps to Reproduce (for bugs)
1. Step one
2. Step two
3. etc.

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., macOS 12.0]
- Python Version: [e.g., 3.9.7]
- CLI Version: [e.g., 0.1.0]

## Additional Context
Any other relevant information
```

## Documentation

### Documentation Types

- **Code Documentation**: Docstrings and inline comments
- **User Documentation**: README, usage examples, tutorials
- **API Documentation**: Generated from docstrings
- **Developer Documentation**: Contributing guidelines, architecture docs

### Writing Documentation

- Use clear, concise language
- Provide practical examples
- Keep documentation up-to-date with code changes
- Test all code examples to ensure they work

## Release Process

1. Update version in `src/gcphcp/__init__.py`
2. Update CHANGELOG.md with new version and changes
3. Create and tag a release on GitHub
4. Automated workflows will build and publish to PyPI

## Getting Help

- **Questions**: Open a GitHub discussion or issue
- **Chat**: Join our community chat (link TBD)
- **Email**: Contact maintainers directly for sensitive issues

Thank you for contributing to GCP HCP CLI!