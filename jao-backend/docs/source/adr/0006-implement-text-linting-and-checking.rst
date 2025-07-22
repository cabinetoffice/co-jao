# ADR: Implement text checking using Text Spans

Context:

The JAO app has a requirement to check a job description for various problems and offer solutions.
Issues are generally with one part of the text: for example some incorrect ALL CAPS text, a way of representing where that text in the document is required, so that it can be highlighted and fixed by the user.

A common pattern implementation pattern used in domains from Natural Language Processing (NLP), to text editors and web browsers is the Text Span or just "span".
Spans are substrings, implemented by referencing a string and holding a start and end index.

A python implementation might look like this:

```python
@dataclass
class TextSpan:
    source_text: str
    start_index: int
    end_index: int
```

Spans enable many references to parts of a string without copying the underlying string, this is important in places like web browsers where performance is important.
As an abstraction for runs of text they are useful.


Checking / Linting scripts with Text Spans

In JAO there is a need to highlight runs of text that are flagged by some check, and associate that run of text with information about what was found.

In the initial implementation checks will run on the backend, and be passed to the frontend.



`Linter`
The linter will orchestrate the checks and and delegate to

A linter will check the whole job description, classes will extend this to find particular problems, e.g. issues with capitalisation, list formatting etc.

`Check`
A checker will operate on a single text span, if it finds one or more problems it will output Issues.
Subclasses of Check will implement each check.

`Issue`
Representing a single issue, it holds a text span to represent where the problem is, and other information such as which checker found the issue and a description of the problem.

`TextSpan`
Reference one particular part of the text.


Decision:

Use Text Spans to implement checks and highlighting of issues, this will allow associating runs of text with particular checks.

An Addendum (ADR-0007) to complement this ADR, has been created to document the hybrid approach of using regex for initial matching and programmatic validation for precise highlighting.