# Architecture

## Access Flow

```{mermaid}
flowchart TB
    A["bag['key']"] --> B[BagNode]
    B --> C{Has resolver?}
    C -->|No| D[Return _value]
    C -->|Yes| E{Cache valid?}
    E -->|Yes| F[Return cached]
    E -->|No| G["Call resolver.load()"]
    G --> H[Store in cache]
    H --> I[Return value]
```

## Resolver Types

```{mermaid}
classDiagram
    BagResolver <|-- BagCbResolver
    BagResolver <|-- UrlResolver
    BagResolver <|-- DirectoryResolver
    BagCbResolver <|-- OpenApiResolver

    class BagResolver {
        +load() value
        +reset()
    }

    class BagCbResolver {
        callback function
    }

    class UrlResolver {
        HTTP requests
    }

    class DirectoryResolver {
        filesystem
    }

    class OpenApiResolver {
        HTTP + parse
    }
```
