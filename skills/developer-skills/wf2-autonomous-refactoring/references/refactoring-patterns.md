# Refactoring Patterns Reference

This document catalogs common refactoring patterns used by the WF2 Autonomous Refactoring workflow. Each pattern includes a description, when to apply it, and language-specific examples.

## 1. Extract Method

**Problem:** A code fragment that can be grouped together, or a method that is too long.

**Solution:** Turn the fragment into a method whose name explains the purpose.

**When to apply:**
- Method exceeds 20 lines
- A block of code has a comment explaining what it does
- The same code fragment appears in multiple places

**Example (Python):**

```python
# Before
def process_order(order):
    # validate order
    if not order.items:
        raise ValueError("Empty order")
    if order.total < 0:
        raise ValueError("Negative total")
    # calculate discount
    discount = 0
    if order.total > 100:
        discount = order.total * 0.1
    elif order.total > 50:
        discount = order.total * 0.05
    order.total -= discount
    return order

# After
def _validate_order(order):
    if not order.items:
        raise ValueError("Empty order")
    if order.total < 0:
        raise ValueError("Negative total")

def _calculate_discount(total):
    if total > 100:
        return total * 0.1
    elif total > 50:
        return total * 0.05
    return 0

def process_order(order):
    _validate_order(order)
    discount = _calculate_discount(order.total)
    order.total -= discount
    return order
```

## 2. Rename Variable / Function

**Problem:** A variable or function name does not clearly communicate its purpose.

**Solution:** Rename it to something descriptive and intention-revealing.

**When to apply:**
- Single-letter variable names outside of loop counters
- Abbreviated names that require context to understand
- Names that describe implementation rather than intent

**Example (JavaScript):**

```javascript
// Before
function calc(d, r) {
  return d * r * 0.01;
}

// After
function calculateInterest(principal, annualRate) {
  return principal * annualRate * 0.01;
}
```

## 3. Simplify Conditionals

**Problem:** Complex conditional logic that is hard to read and maintain.

**Solution:** Decompose conditionals, consolidate duplicate fragments, replace nested conditionals with guard clauses.

**When to apply:**
- Nested if/else deeper than 2 levels
- Repeated condition checks across branches
- Complex boolean expressions

**Example (Python):**

```python
# Before
def get_charge(date, quantity):
    if date.before(SUMMER_START) or date.after(SUMMER_END):
        if quantity > 100:
            charge = quantity * 0.8
        else:
            charge = quantity * 1.0
    else:
        if quantity > 100:
            charge = quantity * 0.7
        else:
            charge = quantity * 0.9
    return charge

# After
def _is_summer(date):
    return not (date.before(SUMMER_START) or date.after(SUMMER_END))

def _get_rate(is_summer, is_bulk):
    if is_summer and is_bulk:
        return 0.7
    if is_summer:
        return 0.9
    if is_bulk:
        return 0.8
    return 1.0

def get_charge(date, quantity):
    rate = _get_rate(_is_summer(date), quantity > 100)
    return quantity * rate
```

## 4. Remove Duplication (DRY)

**Problem:** The same code structure or logic appears in multiple places.

**Solution:** Extract the common code into a shared function, method, or base class.

**When to apply:**
- Identical or near-identical code blocks in two or more locations
- Copy-paste patterns across methods or classes
- Similar algorithms with minor variations (parameterize the differences)

**Example (Java):**

```java
// Before
public double calculateAreaCircle(double radius) {
    double area = Math.PI * radius * radius;
    System.out.println("Area: " + area);
    logMetric("circle_area", area);
    return area;
}

public double calculateAreaSquare(double side) {
    double area = side * side;
    System.out.println("Area: " + area);
    logMetric("square_area", area);
    return area;
}

// After
private double computeAndLog(String shape, double area) {
    System.out.println("Area: " + area);
    logMetric(shape + "_area", area);
    return area;
}

public double calculateAreaCircle(double radius) {
    return computeAndLog("circle", Math.PI * radius * radius);
}

public double calculateAreaSquare(double side) {
    return computeAndLog("square", side * side);
}
```

## 5. Replace Magic Numbers with Named Constants

**Problem:** Literal numbers in code whose meaning is not obvious.

**Solution:** Replace them with well-named constants.

**When to apply:**
- Numeric literals that are not self-explanatory (0, 1, -1 may be acceptable)
- The same literal appears in multiple places
- The value has domain significance

**Example (Python):**

```python
# Before
def calculate_shipping(weight):
    if weight > 50:
        return weight * 2.5 + 15.0
    return weight * 1.5 + 5.0

# After
HEAVY_THRESHOLD_KG = 50
HEAVY_RATE_PER_KG = 2.5
HEAVY_BASE_FEE = 15.0
STANDARD_RATE_PER_KG = 1.5
STANDARD_BASE_FEE = 5.0

def calculate_shipping(weight):
    if weight > HEAVY_THRESHOLD_KG:
        return weight * HEAVY_RATE_PER_KG + HEAVY_BASE_FEE
    return weight * STANDARD_RATE_PER_KG + STANDARD_BASE_FEE
```

## 6. Introduce Parameter Object

**Problem:** A function takes many parameters that naturally belong together.

**Solution:** Group related parameters into a single object or data class.

**When to apply:**
- Function has more than 3-4 parameters
- The same group of parameters appears in multiple functions
- Parameters represent a coherent concept

**Example (Python):**

```python
# Before
def create_user(first_name, last_name, email, phone, street, city, zip_code):
    ...

# After
@dataclass
class Address:
    street: str
    city: str
    zip_code: str

@dataclass
class UserInfo:
    first_name: str
    last_name: str
    email: str
    phone: str
    address: Address

def create_user(user_info: UserInfo):
    ...
```

## 7. Replace Temp with Query

**Problem:** A temporary variable holds the result of an expression that could be a method.

**Solution:** Extract the expression into a method and replace all references to the temp.

**When to apply:**
- A temp is assigned once and used in multiple places
- The expression is complex enough to benefit from a descriptive name
- The temp obscures the flow of the method

## 8. Decompose Large Class

**Problem:** A class has too many responsibilities (violates Single Responsibility Principle).

**Solution:** Extract cohesive groups of fields and methods into separate classes.

**When to apply:**
- Class exceeds 300 lines
- Class has methods that operate on distinct subsets of its fields
- Class name includes "And" or "Manager" or "Handler" suggesting multiple roles

## Application Guidelines

1. **Preserve public API**: Do not change public method signatures unless explicitly requested
2. **One pattern at a time**: Apply refactoring patterns incrementally, verifying tests after each step
3. **Test first**: Ensure adequate test coverage exists before refactoring; add tests if coverage is below 80%
4. **Commit granularly**: Each refactoring pattern application should be a logical unit of change
5. **Document changes**: Note which patterns were applied and why in the delta report
