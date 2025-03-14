import itertools
import random
import matplotlib.pyplot as plt

# Parameters
n = 5  # Number of items
s = 15  # Number of bidders
prob_complementarity = 0.1
increase_min, increase_max = -0.45, 0.05
num_runs = 100

# Helper function to calculate the best partition of a set
def best_partition(subset, valuations, memo):
    if subset in memo:
        return memo[subset]

    # Base case: single-item subset
    if len(subset) == 1:
        value = valuations[subset]
        memo[subset] = value
        return value

    max_value = valuations.get(subset, 0)  # start with direct valuation if exists

    # Check all possible partitions
    for i in range(1, len(subset)):
        for part in itertools.combinations(subset, i):
            part1 = frozenset(part)
            part2 = subset - part1
            value1 = best_partition(part1, valuations, memo)
            value2 = best_partition(part2, valuations, memo)
            total_value = value1 + value2
            if total_value > max_value:
                max_value = total_value

    memo[subset] = max_value
    return max_value

# Generate bidder valuations
def generate_bidder_valuations():
    bidder_valuations = {}
    for bidder in range(1, s + 1):
        valuations = {}
        # Generate valuations for single items
        for item in range(n):
            valuations[frozenset([item])] = max(random.uniform(-10, 20), 0)

        # Generate valuations for bundles
        all_items = list(range(n))
        for k in range(2, n + 1):
            for bundle in itertools.combinations(all_items, k):
                bundle_set = frozenset(bundle)

                # Calculate best partition using memoization
                memo = {}
                partition_value = best_partition(bundle_set, valuations, memo)

                increase_percentage = random.uniform(increase_min, increase_max)
                # Complementarity or substitutability adjustment
                adjusted_value = partition_value * (1 + increase_percentage)
                adjusted_value = max(adjusted_value, 0)  # Ensure non-negative valuation
                valuations[bundle_set] = adjusted_value

        bidder_valuations[bidder] = valuations
    return bidder_valuations

# Example usage and test
bidder_vals = generate_bidder_valuations()

# Let's print the valuations for one bidder as an example
bidder_example = 1
print(f"Bidder {bidder_example} valuations:")
for bundle, value in sorted(bidder_vals[bidder_example].items(), key=lambda x: (len(x[0]), x)):
    print(f"Items {sorted(bundle)}: {value:.2f}")
