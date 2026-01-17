# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""BuildingBuilder - Example builder for building/apartment structures.

A didactic example showing how to use @element decorator for:
- Structure validation with sub_tags parameter
- Cardinality constraints ([:1], [1:], etc.)
- Using `tags` parameter to map multiple tags to the same handler
"""

from __future__ import annotations

from genro_bag import Bag, BagBuilderBase
from genro_bag.builders import element


class Building:
    """A building structure with validation.

    This is a "cover" class that wraps a Bag with BuildingBuilder
    and provides a convenient API.

    Example:
        >>> casa = Building(name='Casa Mia')
        >>> floor1 = casa.floor(number=1)
        >>> apt = floor1.apartment(number='1A')
        >>> kitchen = apt.kitchen()
        >>> kitchen.fridge(brand='Samsung')
        >>> kitchen.oven()
        >>>
        >>> # Check the structure
        >>> errors = casa.check()
        >>> if errors:
        ...     for e in errors:
        ...         print(e)
        >>>
        >>> # Invalid: fridge in dining_room
        >>> dining = apt.dining_room()
        >>> dining.fridge()  # This will be caught by check()
        >>> errors = casa.check()
        >>> # ['fridge is not a valid child of dining_room...']
    """

    def __init__(self, name: str = "", **attr):
        """Create a new building.

        Args:
            name: The building name.
            **attr: Additional attributes for the building node.
        """
        self._store = Bag(builder=BuildingBuilder)
        self._root = self._store.building(name=name, **attr)

    @property
    def store(self):
        """Access the underlying Bag."""
        return self._store

    @property
    def root(self):
        """Access the root building Bag."""
        return self._root

    def floor(self, number: int = 0, **attr):
        """Add a floor to the building."""
        return self._root.floor(number=number, **attr)

    def check(self) -> list[str]:
        """Check the building structure.

        Returns:
            List of error messages (empty if valid).
        """
        results = self._store.builder.check(self._root)
        # Convert tuple format (path, node, reasons) to simple error strings
        errors = []
        for path, _node, reasons in results:
            for reason in reasons:
                errors.append(f"{path}: {reason}")
        return errors

    def print_tree(self):
        """Print the building structure for debugging."""
        print("=" * 60)
        print("BUILDING")
        print("=" * 60)
        for path, node in self._root.walk():
            indent = "  " * path.count(".")
            tag = node.tag or node.label
            attrs = " ".join(f"{k}={v}" for k, v in node.attr.items() if not k.startswith("_"))
            attrs_str = f" ({attrs})" if attrs else ""
            print(f"{indent}{tag}{attrs_str}")


class BuildingBuilder(BagBuilderBase):
    """Builder for describing building structures.

    Demonstrates:
    - sub_tags for structure validation
    - Cardinality: [:1] (max 1), [1:] (min 1), [] (any)
    - tags parameter to map multiple tag names to one handler

    Hierarchy:
        building
          └── floor
                └── apartment | corridor | stairs
                      apartment:
                        └── kitchen | bathroom | bedroom | living_room | dining_room
                              kitchen: fridge, oven, sink, table, chair
                              bathroom: toilet, shower, sink
                              bedroom: bed, wardrobe, desk, chair
                              living_room: sofa, tv, table, chair
                              dining_room: table, chair

    Example:
        >>> store = Bag(builder=BuildingBuilder)
        >>> building = store.building(name='Casa Mia')
        >>> floor1 = building.floor(number=1)
        >>> apt = floor1.apartment(number='1A')
        >>> kitchen = apt.kitchen()
        >>> kitchen.fridge(brand='Samsung')
        >>> errors = store.builder.check(building)
    """

    # === Building level ===

    @element(sub_tags="floor")
    def building(self): ...

    # === Floor level ===

    @element(sub_tags="apartment, corridor, stairs")
    def floor(self): ...

    # === Floor elements ===

    @element(sub_tags="kitchen[:1], bathroom[1:], bedroom, living_room[:1], dining_room[:1]")
    def apartment(self): ...

    @element()
    def corridor(self): ...

    @element()
    def stairs(self): ...

    # === Rooms ===

    @element(sub_tags="fridge[:1], oven[:2], sink[:1], table, chair")
    def kitchen(self): ...

    @element(sub_tags="toilet[:1], shower[:1], sink[:1]")
    def bathroom(self): ...

    @element(sub_tags="bed, wardrobe, desk, chair")
    def bedroom(self): ...

    @element(sub_tags="sofa, tv, table, chair")
    def living_room(self): ...

    @element(sub_tags="table, chair")
    def dining_room(self): ...

    # === Appliances and fixtures ===
    # Using tags parameter to map multiple tags to same handler

    @element(tags="fridge, oven, sink, toilet, shower")
    def appliance(self): ...

    # === Furniture ===
    # Using tags parameter to map multiple tags to same handler

    @element(tags="bed, desk, table, chair, sofa, tv, wardrobe")
    def furniture(self): ...


def demo():
    """Demo of BuildingBuilder."""
    print("=" * 60)
    print("BuildingBuilder Demo")
    print("=" * 60)

    # Create a building
    casa = Building(name="Casa Mia")

    # Add first floor
    floor1 = casa.floor(number=1)

    # Add apartment 1A
    apt1a = floor1.apartment(number="1A")

    # Add kitchen with appliances
    kitchen = apt1a.kitchen()
    kitchen.fridge(brand="Samsung")
    kitchen.oven(brand="Bosch")
    kitchen.sink()
    kitchen.table()
    kitchen.chair()
    kitchen.chair()

    # Add bathroom
    bathroom = apt1a.bathroom()
    bathroom.toilet()
    bathroom.shower()
    bathroom.sink()

    # Add bedroom
    bedroom = apt1a.bedroom()
    bedroom.bed(size="queen")
    bedroom.wardrobe(color="oak")
    bedroom.desk()
    bedroom.chair()

    # Add living room
    living = apt1a.living_room()
    living.sofa(seats=3)
    living.tv(brand="LG", size='55"')

    # Add second floor
    floor2 = casa.floor(number=2)
    apt2a = floor2.apartment(number="2A")
    apt2a.bathroom()  # minimum requirement

    # Print structure
    casa.print_tree()

    # Validate
    print("\n" + "=" * 60)
    print("Validation")
    print("=" * 60)
    errors = casa.check()
    if errors:
        print("Errors found:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("Building structure is valid!")

    # Demo: Invalid structure
    print("\n" + "=" * 60)
    print("Invalid Structure Demo")
    print("=" * 60)

    bad_building = Building(name="Bad House")
    bad_floor = bad_building.floor(number=1)
    bad_apt = bad_floor.apartment(number="1A")

    # Invalid: fridge in dining room (not allowed by sub_tags)
    dining = bad_apt.dining_room()
    dining.fridge()  # This is invalid!

    errors = bad_building.check()
    print("Errors in bad building:")
    for e in errors:
        print(f"  - {e}")


if __name__ == "__main__":
    demo()
