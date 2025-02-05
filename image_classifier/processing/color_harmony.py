
def is_triadic(hues):
    """Checks if a palette forms a triadic scheme (three hues ~120° apart)."""
    hues = sorted(hues)
    if len(hues) != 3:
        return False
    return abs(hues[0] - hues[1]) % 360 in (120, 240) and abs(hues[1] - hues[2]) % 360 in (120, 240)


def is_tetradic(hues):
    """Checks if a palette forms a tetradic (double complementary) scheme."""
    hues = sorted(hues)
    if len(hues) != 4:
        return False
    return abs(hues[0] - hues[1]) % 360 == 90 and abs(hues[2] - hues[3]) % 360 == 90


def is_square(hues):
    """Checks if a palette forms a square scheme (four hues ~90° apart)."""
    hues = sorted(hues)
    if len(hues) != 4:
        return False
    return abs(hues[0] - hues[1]) % 360 == 90 and abs(hues[1] - hues[2]) % 360 == 90 and abs(
        hues[2] - hues[3]) % 360 == 90


def is_analogous(hues):
    """Checks if all colors are within 30° of each other (Analogous scheme)."""
    return max(hues) - min(hues) <= 30


def is_complementary(hues):
    """Checks if a palette is complementary (one pair of colors ~180° apart)."""
    if len(hues) != 2:
        return False
    return abs(hues[0] - hues[1]) % 360 == 180


def is_split_complementary(hues):
    """Checks if a palette follows the split-complementary rule."""
    if len(hues) != 3:
        return False
    return (abs(hues[0] - hues[1]) % 360 == 150 or abs(hues[0] - hues[1]) % 360 == 210) and \
        (abs(hues[0] - hues[2]) % 360 == 150 or abs(hues[0] - hues[2]) % 360 == 210)
