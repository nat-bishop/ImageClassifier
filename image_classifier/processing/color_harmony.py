import logging
import math

from image_classifier.color import Color

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


def circular_mean(angles: list[float]) -> float:
    """
    Computes the circular mean of a list of angles (in degrees).
    Uses the standard method via summing sine and cosine components.
    When angles are evenly distributed around the circle (e.g. [0, 120, 240]),
    the vector sum will be close to zero, and we return the first angle.
    """
    if not angles:
        return 0.0

    # Handle special cases first
    if len(angles) == 2:
        # For two angles, we can compute the mean directly
        a1, a2 = angles[0] % 360, angles[1] % 360
        diff = circular_diff(a1, a2)
        if abs(diff - 180) < 1e-10:
            # For opposite angles, return their arithmetic mean
            return ((a1 + a2) / 2) % 360
        # Calculate the mean by going halfway from a1 to a2 in the shorter direction
        # If a2 is clockwise from a1, add the half-diff; otherwise subtract it
        if (a2 - a1) % 360 <= 180:
            return (a1 + diff/2) % 360
        else:
            return (a1 - diff/2) % 360

    # For three or more angles, use the vector method
    sin_sum = sum(math.sin(math.radians(a)) for a in angles)
    cos_sum = sum(math.cos(math.radians(a)) for a in angles)
    # Check if both sums are close to zero (within a small epsilon)
    # For evenly distributed angles like [0, 120, 240], the sums should be exactly zero
    # Use a very small epsilon to avoid false positives
    if abs(sin_sum) < 1e-14 and abs(cos_sum) < 1e-14:
        # Evenly distributed angles or opposite pairs cancel out – return first angle.
        mean_angle = angles[0]
    else:
        mean_angle = math.degrees(math.atan2(sin_sum, cos_sum)) % 360
    logger.debug(f"circular_mean({angles}) = {mean_angle}")
    return mean_angle


def score_triadic(hues: list[float], tolerance: float = 30) -> tuple[float, float]:
    """
    Returns a harmony score (0 to 1) for a triadic palette.
    A perfect triadic palette (3 hues exactly 120° apart) scores 1.

    The score is calculated by comparing each of the three intervals
    (including the wrap-around) to the ideal value of 120°.
    
    Returns:
        tuple: (score, start_hue) where score is between 0 and 1, and start_hue is the best starting hue for visualization
    """
    if len(hues) != 3:
        logger.debug("score_triadic: Palette does not have exactly 3 hues.")
        return 0.0, None
    sorted_hues = sorted(hues)
    best_score = 0.0
    best_start = None
    
    # Try each hue as the starting point
    for i in range(3):
        rotated = sorted_hues[i:] + sorted_hues[:i]
        diff1 = circular_diff(rotated[0], rotated[1])
        diff2 = circular_diff(rotated[1], rotated[2])
        diff3 = circular_diff(rotated[2], rotated[0])
        errors = [abs(diff - 120) for diff in [diff1, diff2, diff3]]
        total_error = sum(errors)
        max_error = 3 * tolerance
        score = max(0.0, 1 - total_error / max_error)
        
        if score > best_score:
            best_score = score
            best_start = rotated[0]
            
    logger.debug(
        f"score_triadic: hues={hues}, sorted={sorted_hues}, diffs={[diff1, diff2, diff3]}, "
        f"errors={errors}, total_error={total_error}, score={score}"
    )
    return best_score, best_start


def score_square(hues: list[float], tolerance: float = 15) -> tuple[float, float]:
    """
    Returns a harmony score (0 to 1) for a square palette.
    In an ideal square scheme, 4 hues are exactly 90° apart.
    
    Returns:
        tuple: (score, start_hue) where score is between 0 and 1, and start_hue is the best starting hue for visualization
    """
    if len(hues) != 4:
        logger.debug("score_square: Palette does not have exactly 4 hues.")
        return 0.0, None
    sorted_hues = sorted(hues)
    best_score = 0.0
    best_start = None
    
    # Try each hue as the starting point
    for i in range(4):
        rotated = sorted_hues[i:] + sorted_hues[:i]
        diffs = [circular_diff(rotated[j], rotated[j+1]) for j in range(3)]
        diffs.append(circular_diff(rotated[3], rotated[0]))
        errors = [abs(diff - 90) for diff in diffs]
        total_error = sum(errors)
        max_error = 4 * tolerance
        score = max(0.0, 1 - total_error / max_error)
        
        if score > best_score:
            best_score = score
            best_start = rotated[0]
            
    logger.debug(
        f"score_square: hues={hues}, sorted={sorted_hues}, diffs={diffs}, "
        f"errors={errors}, total_error={total_error}, score={score}"
    )
    return best_score, best_start


def score_analogous(hues: list[float], threshold: float = 120) -> tuple[float, tuple]:
    """
    Returns a score (0 to 1) for an analogous scheme.
    The idea is that all hues should be grouped closely together.

    This implementation uses the range (max-min) of the hues (assuming
    they do not span the 0°/360° wrap-around) and scales the score linearly.
    
    Returns:
        tuple: (score, (start_hue, arc_size)) where score is between 0 and 1,
              and the second element contains the starting hue and arc size for visualization
    """
    if not hues:
        logger.debug("score_analogous: Empty palette.")
        return 0.0, (None, None)
        
    # Find the smallest arc that contains all hues
    sorted_hues = sorted(hues)
    min_arc = float('inf')
    best_start = None
    
    for i in range(len(hues)):
        rotated = sorted_hues[i:] + sorted_hues[:i]
        arc = circular_diff(rotated[0], rotated[-1])
        if arc < min_arc:
            min_arc = arc
            best_start = rotated[0]
    
    score = max(0.0, 1 - min_arc / threshold)
    logger.debug(f"score_analogous: hues={hues}, range={min_arc}, score={score}")
    return score, (best_start, min_arc)


def score_complementary(hues: list[float], tolerance_mean: float = 60, tolerance_spread: float = 120) -> tuple[float, tuple]:
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
    
    Returns:
        tuple: (score, (cluster1, cluster2, mean1, mean2)) where score is between 0 and 1,
              and the second element contains the clusters and their means for visualization
    """
    n = len(hues)
    if n < 2:
        logger.debug("score_complementary: Not enough hues.")
        return 0.0, (None, None, None, None)
    if n == 2:
        diff = circular_diff(hues[0], hues[1])
        error = abs(diff - 180)
        score = max(0.0, 1 - error / tolerance_mean)
        logger.debug(
            f"score_complementary (n=2): hues={hues}, diff={diff}, error={error}, score={score}"
        )
        return score, ([hues[0]], [hues[1]], hues[0], hues[1])

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
            # Weight angle errors more heavily (0.7) than spread errors (0.3)
            total_error = 0.7 * norm_error_mean + 0.3 * norm_error_spread
            current_score = max(0.0, 1 - total_error)
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
    if best_split:
        cluster1, cluster2, mean1, mean2, _, _ = best_split
        return best_score, (cluster1, cluster2, mean1, mean2)
    return best_score, (None, None, None, None)


def score_split_complementary(hues: list[float], tolerance_mean: float = 15, tolerance_spread: float = 45) -> tuple[float, tuple]:
    """
    Returns a score (0 to 1) for a split-complementary scheme without assuming a fixed base hue.

    In this scheme, the hues should cluster into three groups:
    - A base cluster
    - Two split clusters that are approximately 150° and 210° from the base cluster's mean
      (or equivalently, 30° on either side of the complement)

    The function tries every possible way to split the hues into three clusters and finds
    the arrangement that best matches the split-complementary pattern. The score is based on:
    1. How close the means of the split clusters are to the ideal angles from the base (65% weight)
    2. How tightly grouped the colors are within each cluster (35% weight)

    The scoring uses a quadratic falloff for both angle and spread errors to give more credit
    for near-perfect arrangements.

    Args:
        hues (List[float]): A list of hue values (in degrees). Must have at least 3 hues.
        tolerance_mean (float): Tolerance for deviation from the ideal angles (in degrees).
        tolerance_spread (float): Tolerance for spread within each cluster (in degrees).

    Returns:
        tuple: (score, (base_cluster, split1_cluster, split2_cluster, base_mean, split1_mean, split2_mean))
              where score is between 0 and 1, and the second element contains the clusters and their means
              for visualization. If no valid split is found, returns (0.0, (None, None, None, None, None, None)).
    """
    if len(hues) < 3:
        logger.debug("score_split_complementary: Palette must have at least 3 hues.")
        return 0.0, (None, None, None, None, None, None)

    # Normalize all hues to [0, 360) range
    normalized_hues = [h % 360 for h in hues]
    sorted_hues = sorted(normalized_hues)
    best_score = 0.0
    best_arrangement = None

    # Try each possible way to split the hues into three clusters
    n = len(sorted_hues)
    for i in range(n):
        rotated = sorted_hues[i:] + sorted_hues[:i]
        # Try different split points to form three clusters
        for j in range(1, n-1):
            for k in range(j+1, n):
                base_cluster = rotated[:j]
                split1_cluster = rotated[j:k]
                split2_cluster = rotated[k:]

                # All clusters must be non-empty
                if not (base_cluster and split1_cluster and split2_cluster):
                    continue

                # Calculate means for each cluster
                base_mean = circular_mean(base_cluster)
                split1_mean = circular_mean(split1_cluster)
                split2_mean = circular_mean(split2_cluster)

                # Calculate target angles (150° and 210° from base_mean)
                target1 = (base_mean + 150) % 360
                target2 = (base_mean + 210) % 360

                # Try both possible assignments of the split clusters to the targets
                error1 = (circular_diff(split1_mean, target1) + circular_diff(split2_mean, target2)) / 2
                error2 = (circular_diff(split1_mean, target2) + circular_diff(split2_mean, target1)) / 2
                angle_error = min(error1, error2)

                # Calculate spread within each cluster using circular_diff
                def cluster_spread(cluster):
                    if len(cluster) == 1:
                        return 0
                    max_diff = 0
                    for i in range(len(cluster)):
                        for j in range(i + 1, len(cluster)):
                            diff = circular_diff(cluster[i], cluster[j])
                            max_diff = max(max_diff, diff)
                    return max_diff

                base_spread = cluster_spread(base_cluster)
                split1_spread = cluster_spread(split1_cluster)
                split2_spread = cluster_spread(split2_cluster)
                avg_spread = (base_spread + split1_spread + split2_spread) / 3

                # Normalize errors with quadratic falloff and 65/35 weighting
                norm_angle_error = (angle_error / tolerance_mean) ** 2
                norm_spread_error = (avg_spread / tolerance_spread) ** 2
                total_error = 0.65 * norm_angle_error + 0.35 * norm_spread_error
                current_score = max(0.0, 1 - total_error)

                logger.debug(
                    f"Split at {j},{k}: base={base_cluster}(mean={base_mean}), "
                    f"split1={split1_cluster}(mean={split1_mean}), "
                    f"split2={split2_cluster}(mean={split2_mean}), "
                    f"angle_error={angle_error}, avg_spread={avg_spread}, "
                    f"score={current_score}"
                )

                if current_score > best_score:
                    best_score = current_score
                    # If error2 was better, swap the split clusters to match the targets
                    if error2 < error1:
                        split1_cluster, split2_cluster = split2_cluster, split1_cluster
                        split1_mean, split2_mean = split2_mean, split1_mean
                    # Normalize base_mean to 0° if it's at 360°
                    if abs(base_mean - 360) < 1e-10:
                        base_mean = 0
                    best_arrangement = (base_cluster, split1_cluster, split2_cluster,
                                      base_mean, split1_mean, split2_mean)

    logger.debug(f"score_split_complementary: Final result - best_score={best_score}, "
                f"best_arrangement={best_arrangement}")
    if best_arrangement:
        return best_score, best_arrangement
    return 0.0, (None, None, None, None, None, None)


def score_saturation_absolute(colors: list[Color]) -> float:
    """
    Computes an absolute saturation score for a palette.

    0 means completely desaturated (i.e. all colors are gray, with a=b=128),
    and 1 means the palette is as saturated as possible (with chroma near the maximum).

    The score weights colors based on their brightness, giving more importance
    to brighter colors when calculating the average saturation.

    Args:
        colors (List[Color]): List of colors.

    Returns:
        float: A score between 0 and 1.
    """
    if not colors:
        return 0.0

    # In OpenCV's LAB space, maximum chroma observed for pure RGB colors is ~120
    # This was determined empirically by testing pure RGB colors
    max_chroma = 120.0
    total_weighted_chroma = 0.0
    total_weight = 0.0
    
    for color in colors:
        L, a, b = color.lab
        # Calculate chroma (saturation) for this color
        chroma = math.sqrt((a - 128) ** 2 + (b - 128) ** 2)
        
        # Calculate weight based on lightness (L ranges from 0 to 255)
        # We want brighter colors to have more impact on the final score
        # A color with L=255 should have maximum weight (1.0)
        # A color with L=0 should have minimum weight (0.0)
        weight = L / 255.0
        
        weighted_chroma = chroma * weight
        total_weighted_chroma += weighted_chroma
        total_weight += weight

    if total_weight == 0:
        return 0.0
        
    # Calculate weighted average chroma
    avg_chroma = total_weighted_chroma / total_weight
    # Normalize the average chroma to [0, 1]
    score = avg_chroma / max_chroma
    return min(max(score, 0.0), 1.0)


def score_contrast_absolute(colors: list[Color]) -> float:
    """
    Computes an absolute contrast score based on the L (lightness) channel.

    0 means no contrast (all colors have the same lightness),
    and 1 means maximum contrast (the lightness range is 255).

    Args:
        colors (List[Color]): List of colors.

    Returns:
        float: A score between 0 and 1.
    """
    if not colors:
        return 0.0

    # Extract L values from each Lab color
    L_values = [color.lab[0] for color in colors]
    contrast_range = max(L_values) - min(L_values)
    # Normalize the contrast range: maximum possible is 255 in OpenCV's LAB space
    score = contrast_range / 255.0
    return min(max(score, 0.0), 1.0)


def score_monochromatic(hues: list[float], tolerance: float = 120) -> tuple[float, float]:
    """
    Returns a score (0 to 1) for a monochromatic palette.
    For a palette to be monochromatic, all hues should be very similar.
    This function computes the circular range of hues and maps a small range to a high score.

    Args:
        hues (List[float]): A list of hue values (in degrees).
        tolerance (float): The maximum acceptable circular range of hues for a score of 1.
                           Larger differences decrease the score linearly.

    Returns:
        tuple: (score, mean_hue) where score is between 0 and 1, and mean_hue is the average hue for visualization
    """
    if not hues:
        return 0.0, None

    # Compute the naive range.
    min_hue = min(hues)
    max_hue = max(hues)
    diff = max_hue - min_hue
    # Adjust if the range spans the wrap-around (e.g. near 0/360)
    if diff > 180:
        diff = 360 - diff

    score = max(0.0, 1 - (diff / tolerance))
    mean_hue = circular_mean(hues)
    return score, mean_hue
