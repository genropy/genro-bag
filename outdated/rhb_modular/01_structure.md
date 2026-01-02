
# RHB Specification — 01 Structure

## Bag
- Attributes: dict
- Children: ordered dict label → Node
- parent_node backref

## Node
- label
- attributes
- value (primitive or Bag)
- parent_bag backref
- local triggers
