import math
import logging
from typing import List, Optional, Tuple, Any

# Set up logging configuration.
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def circular_diff(a: float, b: float) -> float:
    """
    Returns the smallest difference between two angles (in degrees)
    accounting for wrap-around.
    """
    diff = abs(a - b) % 360
    result = diff if diff <= 180 else 360 - diff
    logger.debug(f"circular_diff({a}, {b}) = {result}")
    return result


def circular_mean(angles: List[float]) -> float:
    """
    Computes the circular mean of a list of angles (in degrees).
    Uses the standard method via summing sine and cosine components.
    """
    sin_sum = sum(math.sin(math.radians(a)) for a in angles)
    cos_sum = sum(math.cos(math.radians(a)) for a in angles)
    if sin_sum == 0 and cos_sum == 0:
        # Ambiguous situation (e.g. opposite pairs cancel out) – return first angle.
        mean_angle = angles[0]
    else:
        mean_angle = math.degrees(math.atan2(sin_sum, cos_sum)) % 360
    logger.debug(f"circular_mean({angles}) = {mean_angle}")
    return mean_angle


def score_triadic(hues: List[float], tolerance: float = 30) -> float:
    """
    Returns a harmony score (0 to 1) for a triadic palette.
    A perfect triadic palette (3 hues exactly 120° apart) scores 1.

    The score is calculated by comparing each of the three intervals
    (including the wrap-around) to the ideal value of 120°.
    """
    if len(hues) != 3:
        logger.debug("score_triadic: Palette does not have exactly 3 hues.")
        return 0.0
    sorted_hues = sorted(hues)
    diffs = [
        circular_diff(sorted_hues[0], sorted_hues[1]),
        circular_diff(sorted_hues[1], sorted_hues[2]),
        circular_diff(sorted_hues[2], sorted_hues[0])
    ]
    errors = [abs(diff - 120) for diff in diffs]
    total_error = sum(errors)
    max_error = 3 * tolerance
    score = max(0.0, 1 - total_error / max_error)
    logger.debug(
        f"score_triadic: hues={hues}, sorted={sorted_hues}, diffs={diffs}, "
        f"errors={errors}, total_error={total_error}, score={score}"
    )
    return score


def score_square(hues: List[float], tolerance: float = 15) -> float:
    """
    Returns a harmony score (0 to 1) for a square palette.
    In an ideal square scheme, 4 hues are exactly 90° apart.
    """
    if len(hues) != 4:
        logger.debug("score_square: Palette does not have exactly 4 hues.")
        return 0.0
    sorted_hues = sorted(hues)
    diffs = [
        circular_diff(sorted_hues[0], sorted_hues[1]),
        circular_diff(sorted_hues[1], sorted_hues[2]),
        circular_diff(sorted_hues[2], sorted_hues[3]),
        circular_diff(sorted_hues[3], sorted_hues[0])
    ]
    errors = [abs(diff - 90) for diff in diffs]
    total_error = sum(errors)
    max_error = 4 * tolerance
    score = max(0.0, 1 - total_error / max_error)
    logger.debug(
        f"score_square: hues={hues}, sorted={sorted_hues}, diffs={diffs}, "
        f"errors={errors}, total_error={total_error}, score={score}"
    )
    return score


def score_analogous(hues: List[float], threshold: float = 120) -> float:
    """
    Returns a score (0 to 1) for an analogous scheme.
    The idea is that all hues should be grouped closely together.

    This implementation uses the range (max-min) of the hues (assuming
    they do not span the 0°/360° wrap-around) and scales the score linearly.
    """
    if not hues:
        logger.debug("score_analogous: Empty palette.")
        return 0.0
    hue_range = max(hues) - min(hues)
    score = max(0.0, 1 - hue_range / threshold)
    logger.debug(f"score_analogous: hues={hues}, range={hue_range}, score={score}")
    return score


def score_complementary(hues: List[float], tolerance_mean: float = 60, tolerance_spread: float = 120) -> float:
    """
    Returns a harmony score (0 to 1) for a complementary palette.

    For a palette to be complementary, the hues should cluster into two groups
    whose circular means are approximately 180° apart. This function works for
    any number of hues (≥2). For 2 hues, it simply checks the difference.

    For 3 or more hues, it tries every contiguous split (in the circular sense)
    of the sorted list of hues into two clusters. For each split, it computes:
      - error_mean: the deviation of the circular difference between the clusters' means from 180°.
      - error_spread: the average spread (arc length) of each cluster.

    These errors are normalized by their respective tolerances, combined, and
    converted to a score between 0 and 1 (with 1 being ideal).
    """
    n = len(hues)
    if n < 2:
        logger.debug("score_complementary: Not enough hues.")
        return 0.0
    if n == 2:
        diff = circular_diff(hues[0], hues[1])
        error = abs(diff - 180)
        score = max(0.0, 1 - error / tolerance_mean)
        logger.debug(
            f"score_complementary (n=2): hues={hues}, diff={diff}, error={error}, score={score}"
        )
        return score

    sorted_hues = sorted(hues)
    best_score = 0.0
    best_split = None
    # For complementary schemes, we try all ways to split the hues (considering the circular order)
    # into two contiguous clusters. We "rotate" the sorted list to consider all splits.
    for i in range(n):
        rotated = sorted_hues[i:] + sorted_hues[:i]
        # k is the size of the first cluster; k must be between 1 and n-1 so that both clusters are non-empty.
        for k in range(1, n):
            cluster1 = rotated[:k]
            cluster2 = rotated[k:]
            mean1 = circular_mean(cluster1)
            mean2 = circular_mean(cluster2)
            error_mean = abs(circular_diff(mean1, mean2) - 180)
            # For a contiguous cluster (in the rotated order) the spread is simply:
            spread1 = (max(cluster1) - min(cluster1)) if len(cluster1) > 1 else 0
            spread2 = (max(cluster2) - min(cluster2)) if len(cluster2) > 1 else 0
            avg_spread = (spread1 + spread2) / 2
            # Normalize errors:
            norm_error_mean = error_mean / tolerance_mean  # 0 if perfect; 1 if error equals tolerance_mean.
            norm_error_spread = avg_spread / tolerance_spread  # likewise for spread.
            total_norm = (norm_error_mean + norm_error_spread) / 2  # average the two normalized errors.
            current_score = max(0.0, 1 - total_norm)
            logger.debug(
                f"score_complementary split (rotated start index {i}, k={k}): "
                f"cluster1={cluster1}, cluster2={cluster2}, mean1={mean1}, mean2={mean2}, "
                f"error_mean={error_mean}, spread1={spread1}, spread2={spread2}, "
                f"avg_spread={avg_spread}, norm_error_mean={norm_error_mean}, "
                f"norm_error_spread={norm_error_spread}, current_score={current_score}"
            )
            if current_score > best_score:
                best_score = current_score
                best_split = (cluster1, cluster2, mean1, mean2, error_mean, avg_spread)
    logger.debug(f"score_complementary: hues={hues}, best_score={best_score}, best_split={best_split}")
    return best_score


def score_split_complementary(hues: List[float], tolerance: float = 30) -> float:
    """
    Returns a score (0 to 1) for a split-complementary scheme without assuming a fixed base hue.

    In this scheme, any one hue can be the base. For the other two hues, one should be near 150° away
    from the base and the other near 210° away. This function tests every hue as a potential base and
    for each base it computes the error for both possible assignments of the other hues to the two ideals.
    The best (lowest error) configuration is used to produce a score.

    Args:
        hues (List[float]): A list of 3 hue values (in degrees).
        tolerance (float): Tolerance for deviation from the ideal differences.

    Returns:
        float: A score between 0 and 1.
    """
    if len(hues) != 3:
        logger.debug("score_split_complementary: Palette does not have exactly 3 hues.")
        return 0.0

    best_score = 0.0
    best_details = None

    # Try each hue as the potential base.
    for i, base in enumerate(hues):
        # The other two hues.
        other_hues = [h for j, h in enumerate(hues) if j != i]

        # Compute the circular differences between the base and each of the other hues.
        diff1 = circular_diff(base, other_hues[0])
        diff2 = circular_diff(base, other_hues[1])

        # Now, instead of taking the minimal error for each hue independently,
        # we force one hue to be compared with 150° and the other with 210°.
        # There are two possibilities:
        error_option1 = abs(diff1 - 150) + abs(diff2 - 210)
        error_option2 = abs(diff1 - 210) + abs(diff2 - 150)

        total_error = min(error_option1, error_option2)

        # The maximum total error is defined as 2*tolerance.
        max_error = 2 * tolerance
        current_score = max(0.0, 1 - total_error / max_error)

        logger.debug(
            f"score_split_complementary: base_candidate={base}, other_hues={other_hues}, "
            f"diff1={diff1}, diff2={diff2}, error_option1={error_option1}, error_option2={error_option2}, "
            f"total_error={total_error}, current_score={current_score}"
        )

        if current_score > best_score:
            best_score = current_score
            best_details = (base, other_hues, diff1, diff2, total_error)

    logger.debug(f"score_split_complementary: hues={hues}, best_details={best_details}, best_score={best_score}")
    return best_score


def score_saturation_absolute(lab_colors: List[Tuple[int, int, int]]) -> float:
    """
    Computes an absolute saturation score for a palette.

    0 means completely desaturated (i.e. all colors are gray, with a=b=128),
    and 1 means the palette is as saturated as possible (with chroma near the maximum).

    Args:
        lab_colors (List[LabColor]): List of Lab colors (each as a tuple (L, a, b)).

    Returns:
        float: A score between 0 and 1.
    """
    if not lab_colors:
        return 0.0

    # Maximum chroma for OpenCV Lab: sqrt((128)^2 + (128)^2) ~ 181.02
    max_chroma = math.sqrt(128 ** 2 + 128 ** 2)
    total_chroma = 0.0
    for L, a, b in lab_colors:
        # Calculate chroma (saturation) for this color
        chroma = math.sqrt((a - 128) ** 2 + (b - 128) ** 2)
        total_chroma += chroma

    avg_chroma = total_chroma / len(lab_colors)
    # Normalize the average chroma to [0, 1]
    score = avg_chroma / max_chroma
    return min(max(score, 0.0), 1.0)


def score_contrast_absolute(lab_colors: List[Tuple[int, int, int]]) -> float:
    """
    Computes an absolute contrast score based on the L (lightness) channel.

    0 means no contrast (all colors have the same lightness),
    and 1 means maximum contrast (the lightness range is 255).

    Args:
        lab_colors (List[LabColor]): List of Lab colors (each as a tuple (L, a, b)).

    Returns:
        float: A score between 0 and 1.
    """
    if not lab_colors:
        return 0.0

    # Extract L values from each Lab color
    L_values = [L for (L, a, b) in lab_colors]
    contrast_range = max(L_values) - min(L_values)
    # Normalize the contrast range: maximum possible is 255.
    score = contrast_range / 255.0
    return min(max(score, 0.0), 1.0)


def score_monochromatic(hues: List[float], tolerance: float = 120) -> float:
    """
    Returns a score (0 to 1) for a monochromatic palette.
    For a palette to be monochromatic, all hues should be very similar.
    This function computes the circular range of hues and maps a small range to a high score.

    Args:
        hues (List[float]): A list of hue values (in degrees).
        tolerance (float): The maximum acceptable circular range of hues for a score of 1.
                           Larger differences decrease the score linearly.

    Returns:
        float: A score between 0 and 1.
    """
    if not hues:
        return 0.0

    # Compute the naive range.
    min_hue = min(hues)
    max_hue = max(hues)
    diff = max_hue - min_hue
    # Adjust if the range spans the wrap-around (e.g. near 0/360)
    if diff > 180:
        diff = 360 - diff

    score = max(0.0, 1 - (diff / tolerance))
    return score
