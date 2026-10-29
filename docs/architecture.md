# Architecture

```mermaid
flowchart LR
    A[Upload] --> B[Text Extraction]
    B --> C[Lexical Analysis]
    C --> D[Syntactical Analysis]
    D --> E[Semantic Analysis]
    E --> F[Structured JSON]
    F --> G[UI]
```

Uploads are size- and extension-checked and consumed from memory. The parser normalizes extracted text, identifies section blocks, and resolves candidate fields into a stable JSON shape. The browser renders the result and an optional raw JSON view.
