---
inclusion: fileMatch
globs:
  - "**/*.java"
---

# Java Guardrails

## Coding Standards

1. **Naming conventions**: Use PascalCase for classes and interfaces, camelCase for methods and variables, UPPER_SNAKE_CASE for constants.
2. **Formatting**: Use google-java-format. 4-space indentation, braces on same line.
3. **Package structure**: Follow reverse-domain convention (e.g., `com.example.module`).
4. **Access modifiers**: Prefer the most restrictive access level. Default to `private`; use `public` only for API surfaces.
5. **Immutability**: Prefer `final` for fields, parameters, and local variables where possible.

## Linting and Static Analysis

1. **Formatter**: google-java-format (applied before commit).
2. **Static analysis**: SpotBugs for bug detection, PMD for code quality.
3. **Dependency check**: OWASP dependency-check-maven plugin in `pom.xml`.
4. **Build tool**: Maven. Run `mvn verify` to execute all checks.

## Security Patterns

1. **SQL injection**: Use PreparedStatement or JPA parameterized queries. Never concatenate user input into SQL strings.
2. **Deserialization**: Never deserialize untrusted data. Use allowlists for deserialization when required.
3. **Logging**: Never log sensitive data (passwords, tokens, PII). Use SLF4J with parameterized messages.
4. **Exception handling**: Never expose stack traces to end users. Catch specific exceptions, not generic `Exception`.
5. **Dependency security**: Run `mvn org.owasp:dependency-check-maven:check` before merge. Block on HIGH/CRITICAL CVEs.

## Testing Conventions

1. **Framework**: JUnit 5 with AssertJ for assertions.
2. **Property-based testing**: jqwik for property-based tests.
3. **Test location**: `src/test/java/` mirroring the main source package structure.
4. **Naming**: Test classes suffixed with `Test` (e.g., `UserServiceTest`). Test methods use descriptive names with `@DisplayName`.
5. **Coverage**: Minimum 80% line coverage on new code (WF1/WF2). Run via `mvn jacoco:report`.
