---
inclusion: fileMatch
globs:
  - "**/*.js"
  - "**/*.ts"
---

# Node.js / TypeScript Guardrails

## Coding Standards

1. **Naming conventions**: camelCase for variables and functions, PascalCase for classes and interfaces, UPPER_SNAKE_CASE for constants.
2. **Formatting**: Use Prettier with project config. 2-space indentation, single quotes, trailing commas.
3. **Module system**: Use ES modules (`import`/`export`). Avoid CommonJS `require` in new code.
4. **Type safety**: Prefer TypeScript over plain JavaScript. Use strict mode (`"strict": true` in `tsconfig.json`).
5. **Async patterns**: Use `async`/`await` over raw Promises or callbacks. Always handle rejections.

## Linting and Static Analysis

1. **Linter**: ESLint with `@typescript-eslint` plugin for TypeScript files.
2. **Formatter**: Prettier (run before commit).
3. **Security audit**: `npm audit` for dependency vulnerabilities.
4. **Type checking**: `tsc --noEmit` for TypeScript type validation.

## Security Patterns

1. **Input validation**: Validate and sanitize all user input. Use a validation library (e.g., zod, joi) for request schemas.
2. **SQL injection**: Use parameterized queries with your ORM or query builder. Never interpolate user input into query strings.
3. **Dependency security**: Run `npm audit` before merge. Block on HIGH/CRITICAL vulnerabilities.
4. **Secrets**: Never hardcode secrets. Use environment variables or a secrets manager.
5. **Prototype pollution**: Avoid `Object.assign` or spread on untrusted input. Validate object shapes before processing.
6. **Error handling**: Never expose internal error details to clients. Use structured error responses.

## Testing Conventions

1. **Framework**: Jest for unit and integration tests.
2. **Property-based testing**: fast-check for property-based tests.
3. **Test location**: `test/` directory or co-located `*.test.ts` files alongside source.
4. **Naming**: Test files suffixed with `.test.ts` or `.test.js`. Use descriptive `describe`/`it` blocks.
5. **Coverage**: Minimum 80% line coverage on new code (WF1/WF2). Run via `jest --coverage`.
