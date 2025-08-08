# Hybrid Checker Pattern Standardisation

## Status: 
Proposed: ADR-0007

## Primary ADR Relationship:
Augments  ADR-0006 (TextSpans)

1. Non-Conformity Statement
The current hybrid checkers (AcronymHybridChecker, ListFormatHybridChecker, SalaryHybridChecker) exhibit these deviations from ADR-0006:


|   ADR-0006 Expectation   |     Current Implementation     |        Deviation Rationale        |
| :----------------------- | :----------------------------: | --------------------------------: |
| Linter class hierarchy   |   Flat `Check` inheritance     |   Simplified checker development  |
| Dynamic discovery        |   Hardcoded registry           |   Faster initialisation           |
| Regex-first design       |   Hybrid pattern/rule-mix      |   Improved precision              |
| Span generation          |   Direct issue emission        |   Reduced boilerplate             |


## Key Insight: 
The hybrid pattern eliminates the need for separate span generation and validation layers present in classic OOP linters, reducing boilerplate while maintaining precision


2. ADR Relationship Definition
Addendum (Not Replacement)
ADR-0007:
✅ Augments ADR-006's checker contract with hybrid pattern specifics
✅ Documents emergent best practices (e.g, `_find_definitions()` helper pattern)
✅ Standardises the `*HybridChecker` naming convention

ADR-0006 remains valid for:
✅ Core `TextSpan/Issue` contracts
✅ Serialisation requirements
✅ Architectural principles


3. Proposed ADR-0007 Content
# ADR: Hybrid Checker Pattern

## Context
Development needs revealed that:
 - Pure regex linting misses contextual validation
 - Full OOP checkers introduce unnecessary abstraction
 - Span manipulation requires careful positioning

Current Evidence:
The existing Hybrid Checkers demonstrate that:
 - Pure OOP would require abstract span generation methods
 - Actual needs are met with regex + targeted validation


## Decision
Standardise checkers that:
- Use regex for initial matching (e.g, `ACRONYM_PAT`)
- Employ programmatic validation (`_find_definitions()`)
- Leverage `TextSpan` slicing for precise highlighting


## Implementation
```python
class HybridChecker(Check): # Not abstract - concrete pattern documentation
    """Template for hybrid regex + programmatic checkers"""

    @classmethod
    def compile_patterns(cls) -> Dict[str, re.Pattern]:
        """Override to define pre-compiled regexes"""

        return {}

    def validate_match(self, match: re.Match, span: TextSpan) -> Optional[Issue]:
        """Override with custom logic"""

        raise NotImplementedError
```

## Consequences
✅ Expected performance gains from reduced abstraction
✅ Anticipated precision improvements via hybrid validation

It eliminates abstraction layers from traditional OOP linters, with measured efficiency gains in our implementation


4. Recommended Actions**  

a. **Immediate**:  
   - Ratify ADR-0007 as living documentation  
   - Add `HybridChecker` as a concrete (not abstract) template class  

b. **Medium-term**:  
   ```python
   # services.py
   class LintingService:
       def register_hybrid(self, name: str, *, patterns: Dict[str, str]):
           """Decorator for hybrid checkers"""
           def wrapper(cls):
               cls.compiled_patterns = {k: re.compile(v) for k,v in patterns.items()}
               self.available_checks[name] = cls
               return cls

c. Long-term:
    - Migrate existing checkers to hybrid pattern
    - Document span math best practices
    - Ensure all new checkers follow the `HybridChecker` template


5. Justification for Addendum Approach

## Why not Replacement?
 - ADR-0006's core text span approach remains valid
 - Hybrid pattern specialises rather than replace
 - Backwards compatibility required

## Why not New ADR?
 - Tightly coupled to ADR-0006's `TextSpan` usage
 - Doesnt introduce competing paradigms

## Demonstrable Benefits
```python
# Before (ADR-0006 Pure)
class PureRegexChecker(Linter):
    def get_spans(): ... # Boilerplate
    def find_issues(): ... # Duplicate matching

# After (ADR-0007 Hybrid)
class OptimisedHybridChecker(Check):
    PAT = re.compile(...) # One-time compile
    def check(span):
        for match in PAT.finditer(span.text):
            yield self._validate(match, span) # Direct span math
```

##  Maintenance Guidelines

### Consider having preference for:
1. Always use `span.slice()` over manual math
2. The validation snippet below conceptualises it clearly:
```python
if not 0 <= rel_start <= rel_end <= len(span):
    raise ValueError(f"Invalid slice {rel_start}-{rel_end}")
    return TextSpan(span.source_text, rel_start, rel_end)  
```
