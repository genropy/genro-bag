# Schema: MarkdownBuilder Schema

## Elements

| Name | Inherits | Sub Tags | Call Args | Compile | Documentation |
| --- | --- | --- | --- | --- | --- |
| `blockquote` | - | - | `node_value` | `callback: _compile_blockquote` | Blockquote. |
| `bold` | - | - | `node_value` | `template: **{node_value}**` | Bold text. |
| `code` | - | - | `node_value, lang` | `template: \`\`\`{lang}\n{node_value}\n\`\`\`` | Code block with optional language. |
| `h1` | - | - | `node_value` | `template: # {node_value}` | Level 1 heading. |
| `h2` | - | - | `node_value` | `template: ## {node_value}` | Level 2 heading. |
| `h3` | - | - | `node_value` | `template: ### {node_value}` | Level 3 heading. |
| `h4` | - | - | `node_value` | `template: #### {node_value}` | Level 4 heading. |
| `h5` | - | - | `node_value` | `template: ##### {node_value}` | Level 5 heading. |
| `h6` | - | - | `node_value` | `template: ###### {node_value}` | Level 6 heading. |
| `hr` | - | - | - | `template: ---` | Horizontal rule. |
| `img` | - | - | `src, alt` | `template: ![{alt}]({src})` | Image. |
| `inlinecode` | - | - | `node_value` | `template: \`{node_value}\`` | Inline code. |
| `italic` | - | - | `node_value` | `template: *{node_value}*` | Italic text. |
| `li` | - | - | `node_value, idx` | - | List item. |
| `link` | - | - | `node_value, href` | `template: [{node_value}]({href})` | Hyperlink. |
| `ol` | - | `li` | - | `callback: _compile_ol` | Ordered list. |
| `p` | - | - | `node_value` | - | Paragraph. |
| `table` | - | `tr` | - | `callback: _compile_table` | Table container. |
| `td` | - | - | `node_value` | - | Table data cell. |
| `text` | - | - | `node_value` | - | Plain text. |
| `th` | - | - | `node_value` | - | Table header cell. |
| `tr` | - | `th,td` | - | - | Table row. |
| `ul` | - | `li` | - | `callback: _compile_ul` | Unordered list. |