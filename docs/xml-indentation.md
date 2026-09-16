# XML indentation

`to_xml(pretty=True)` writes indentation while traversing the Bag. It does not
parse or reformat the serialized XML. The modern Python and JavaScript writers
use two spaces per nesting level, a newline between sibling elements, no leading
indentation for top-level nodes, and no trailing newline. Scalar text remains
inline and is never stripped or indented internally. An empty Bag emits an empty
fragment. `self_closed_tags` applies equally to compact and pretty output.

The Python legacy codec uses the same direct traversal approach, retaining its
GenRoBag envelope, typed values and attributes, and optional custom indentation
(`pretty=True` uses a tab). It can format fragments with `omit_root=True` without
introducing a temporary XML root. Embedded raw HTML remains opaque.

Pretty output keeps subtrees marked `xml:space="preserve"` compact. This is
conservative for the entire subtree, including descendants. Compact output is
unchanged. Formatting no longer normalizes explicit closing tags, attribute
quoting or final newlines through a DOM serializer. No XML validity check is
implicitly performed by pretty-printing; parsing and validation remain reader
responsibilities.
