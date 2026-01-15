# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""BuildingBuilder - Example builder for building/apartment structures.

A didactic example showing how to use @element decorator for:
- Structure validation with sub_tags parameter
- Simple elements (single node)
- Complex elements (nested structures created by a single method call)
"""

from __future__ import annotations

from genro_bag import Bag, BagBuilderBase, BagNode
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

    This builder demonstrates two types of elements:

    1. SIMPLE ELEMENTS: Create a single node
       - Most elements (floor, apartment, bed, table, etc.)
       - Return a Bag (branch) or BagNode (leaf)

    2. COMPLEX ELEMENTS: Create a nested structure
       - Example: wardrobe(drawers=4, doors=2) creates:
         wardrobe
           └── chest_of_drawers
           │     └── drawer (x4)
           └── door (x2)
       - A single method call creates multiple nodes
       - Useful for composite structures with internal logic

    Hierarchy:
        building
          └── floor
                └── apartment | corridor | stairs
                      apartment:
                        └── kitchen | bathroom | bedroom | living_room | dining_room
                              kitchen: fridge, oven, sink, table, chair
                              bathroom: toilet, shower, sink
                              bedroom: bed, wardrobe, desk, chair
                                wardrobe (COMPLEX):
                                  └── chest_of_drawers
                                  │     └── drawer (multiple)
                                  └── door (multiple)
                              living_room: sofa, tv, table, chair
                              dining_room: table, chair

    Example:
        >>> store = Bag(builder=BuildingBuilder())
        >>> building = store.building(name='Casa Mia')
        >>> floor1 = building.floor(number=1)
        >>> apt = floor1.apartment(number='1A')
        >>>
        >>> # Simple elements
        >>> kitchen = apt.kitchen()
        >>> kitchen.fridge(brand='Samsung')
        >>>
        >>> # Complex element - creates nested structure
        >>> bedroom = apt.bedroom()
        >>> bedroom.wardrobe(drawers=6, doors=3, color='oak')
        >>>
        >>> errors = store.builder.check(building)
    """

    # === Building level ===

    @element(sub_tags="floor")
    def building(self, target: Bag, tag: str, name: str = "", **attr) -> BagNode:
        """Create a building. Can contain only floors."""
        return self.child(target, tag, name=name, **attr)

    # === Floor level ===

    @element(sub_tags="apartment, corridor, stairs")
    def floor(self, target: Bag, tag: str, number: int = 0, **attr) -> BagNode:
        """Create a floor. Can contain apartments, corridors, stairs."""
        return self.child(target, tag, number=number, **attr)

    # === Floor elements ===

    @element(sub_tags="kitchen[:1], bathroom[1:], bedroom, living_room[:1], dining_room[:1]")
    def apartment(self, target: Bag, tag: str, number: str = "", **attr) -> BagNode:
        """Create an apartment. Must have at least 1 bathroom, max 1 kitchen/living/dining."""
        return self.child(target, tag, number=number, **attr)

    @element()
    def corridor(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a corridor."""
        return self.child(target, tag, **attr)

    @element()
    def stairs(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create stairs."""
        return self.child(target, tag, **attr)

    # === Rooms ===

    @element(sub_tags="fridge[:1], oven[:2], sink[:1], table, chair")
    def kitchen(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a kitchen. Max 1 fridge, max 2 ovens, max 1 sink."""
        return self.child(target, tag, **attr)

    @element(sub_tags="toilet[:1], shower[:1], sink[:1]")
    def bathroom(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a bathroom. Max 1 of each fixture."""
        return self.child(target, tag, **attr)

    @element(sub_tags="bed, wardrobe, desk, chair")
    def bedroom(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a bedroom. Can contain bedroom furniture."""
        return self.child(target, tag, **attr)

    @element(sub_tags="sofa, tv, table, chair")
    def living_room(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a living room. Can contain living room furniture."""
        return self.child(target, tag, **attr)

    @element(sub_tags="table, chair")
    def dining_room(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a dining room. Can contain dining furniture."""
        return self.child(target, tag, **attr)

    # === Appliances and fixtures ===
    # Using tags parameter to map multiple tags to same method

    @element(tags="fridge, oven, sink, toilet, shower")
    def appliance(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create an appliance/fixture."""
        return self.child(target, tag, **attr)

    # === Simple furniture ===

    @element(tags="bed, desk, table, chair, sofa, tv")
    def furniture(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a simple piece of furniture."""
        return self.child(target, tag, **attr)

    # === Complex furniture (nested structures) ===
    # A single method call can create multiple nodes

    @element(sub_tags="chest_of_drawers[:1], door")
    def wardrobe(self, target: Bag, tag: str, drawers: int = 4, doors: int = 2, **attr) -> BagNode:
        """Create a wardrobe with chest of drawers and doors.

        This is an example of a COMPLEX ELEMENT: a single method call
        creates a nested structure with multiple children.

        Args:
            target: The Bag to add to.
            tag: The tag name (always 'wardrobe').
            drawers: Number of drawers in the chest (default 4).
            doors: Number of doors (default 2).
            **attr: Additional attributes.

        Returns:
            The wardrobe BagNode (for potential further customization).

        Example:
            >>> bedroom.wardrobe(drawers=6, doors=3, color='white')
            # Creates:
            # wardrobe (color=white)
            #   └── chest_of_drawers
            #   │     └── drawer (number=1)
            #   │     └── drawer (number=2)
            #   │     ...
            #   └── door (number=1)
            #   └── door (number=2)
            #   └── door (number=3)
        """
        wardrobe = self.child(target, tag, **attr)

        # Create chest of drawers with N drawers
        if drawers > 0:
            chest = wardrobe.chest_of_drawers()
            for i in range(drawers):
                chest.drawer(number=i + 1)

        # Create doors
        for i in range(doors):
            wardrobe.door(number=i + 1)

        return wardrobe

    @element(sub_tags="drawer")
    def chest_of_drawers(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a chest of drawers container."""
        return self.child(target, tag, **attr)

    @element(tags="drawer, door")
    def wardrobe_part(self, target: Bag, tag: str, **attr) -> BagNode:
        """Create a wardrobe component (drawer or door)."""
        return self.child(target, tag, **attr)


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

    # Add bedroom with complex wardrobe
    bedroom = apt1a.bedroom()
    bedroom.bed(size="queen")
    bedroom.wardrobe(drawers=6, doors=3, color="oak")
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

    # Invalid: fridge in dining room (not allowed by children spec)
    dining = bad_apt.dining_room()
    dining.fridge()  # This is invalid!

    errors = bad_building.check()
    print("Errors in bad building:")
    for e in errors:
        print(f"  - {e}")


if __name__ == "__main__":
    demo()
