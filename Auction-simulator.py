import itertools
import random
import matplotlib.pyplot as plt

# Parameters
n = 6  # Number of items
s = 15  # Number of bidders
prob_complementarity = 0.1
increase_min, increase_max = 0.0001, 0.05
num_runs = 100

# Helper to calculate the best partition of a set
def best_partition(subset, valuations):
    if subset in valuations:
        return valuations[subset]
    else:
        max_value = 0
        best_valuation = {}
        for i in range(1, len(subset)):
            for partition in itertools.combinations(subset, i):
                part1 = frozenset(partition)
                part2 = subset - part1
                valuation1 = best_partition(part1, valuations)
                valuation2 = best_partition(part2, valuations)
                total_value = sum(valuation1.values()) + sum(valuation2.values())
                if total_value > max_value:
                    max_value = total_value
                    best_valuation = valuation1.copy()
                    best_valuation.update(valuation2)
        return best_valuation

# Functions (as previously defined)
def generate_bidder_valuations():
    bidder_valuations = {}
    for bidder in range(1, s + 1):
        valuations = {}
        for item in range(n):
            valuations[frozenset([item])] = {item: random.uniform(-10, 20)}
        for k in range(2, n + 1):
            for bundle in itertools.combinations(range(n), k):
                bundle_set = frozenset(bundle)
                partition_valuation = best_partition(bundle_set, valuations)
                if random.random() < prob_complementarity:
                    increase_percentage = random.uniform(increase_min, increase_max)
                    for item in partition_valuation:
                        partition_valuation[item] *= (1 + increase_percentage)
                    valuations[bundle_set] = partition_valuation
                else 
                    valuations[bundle_set] = partition_valuation
        bidder_valuations[bidder] = valuations
    return bidder_valuations

def run_batch_auctions(bidder_valuations):
    remaining_items = set(range(n))
    winning_bids = []
    while remaining_items:
        best_bid = None
        best_bidder = None
        best_value = 0
        for bidder, valuations in bidder_valuations.items():
            for bundle, valuation in valuations.items():
                if set(bundle).issubset(remaining_items):
                    value = sum(valuation.values())
                    if value > best_value:
                        best_value = value
                        best_bid = bundle
                        best_bidder = bidder
        if not best_bid:
            break
        second_best_value = 0
        for bidder, valuations in bidder_valuations.items():
            if bidder != best_bidder:
                for bundle, valuation in valuations.items():
                    if set(bundle).issubset(remaining_items):
                        value = sum(valuation.values())
                        if value > second_best_value:
                            second_best_value = value
        rewards = best_value - second_best_value
        winning_bids.append((best_bidder, best_bid, best_value, rewards))
        remaining_items -= set(best_bid)
    return winning_bids

def run_simple_combinatorial_auction(bidder_valuations):
    winning_bids = run_batch_auctions(bidder_valuations)
    total_value = sum(value for _, _, value, _ in winning_bids)
    rewards = {}
    for bidder in set(b for b, _, _, _ in winning_bids):
        valuations_without_bidder = {b: v for b, v in bidder_valuations.items() if b != bidder}
        cf_winning_bids = run_batch_auctions(valuations_without_bidder)
        cf_total_value = sum(value for _, _, value, _ in cf_winning_bids)
        rewards[bidder] = total_value - cf_total_value
    return winning_bids, rewards

def filter_bids(bidder_valuations):
    reference_values = {item: max(v[frozenset([item])][item] for v in bidder_valuations.values()) for item in range(n)}
    filtered_bidder_valuations = {}
    for bidder, valuations in bidder_valuations.items():
        filtered_valuations = {bundle: valuation for bundle, valuation in valuations.items()
                               if len(bundle) == 1 or all(valuation[item] >= reference_values[item] for item in bundle)}
        filtered_bidder_valuations[bidder] = filtered_valuations
    return filtered_bidder_valuations

# Main simulation loop
batch_scores, sca_scores, sca_filtered_scores = [], [], []
batch_rewards_list, sca_rewards_list, sca_filtered_rewards_list = [], [], []
batch_negative, sca_negative, sca_filtered_negative = 0, 0, 0

for run in range(num_runs):
    bidder_valuations = generate_bidder_valuations()

    batch_results = run_batch_auctions(bidder_valuations)
    batch_scores.append(sum(value for _, _, value, _ in batch_results))
    batch_rewards = [reward for _, _, _, reward in batch_results]
    batch_rewards_list.append(sum(batch_rewards))
    batch_negative += sum(1 for r in batch_rewards if r < 0)

    _, sca_rewards = run_simple_combinatorial_auction(bidder_valuations)
    sca_scores.append(sum(value for _, _, value, _ in batch_results))
    sca_rewards_list.append(sum(sca_rewards.values()))
    sca_negative += sum(1 for r in sca_rewards.values() if r < 0)

    filtered_valuations = filter_bids(bidder_valuations)
    filtered_results, sca_filtered_rewards = run_simple_combinatorial_auction(filtered_valuations)
    sca_filtered_scores.append(sum(value for _, _, value, _ in filtered_results))
    sca_filtered_rewards_list.append(sum(sca_filtered_rewards.values()))
    sca_filtered_negative += sum(1 for r in sca_filtered_rewards.values() if r < 0)

# Plot histograms
fig, axes = plt.subplots(2, 3, figsize=(15, 8))

axes[0, 0].hist(batch_scores, bins=5, color='blue', alpha=0.7)
axes[0, 0].set_title('Batch Auction Scores')
axes[0, 1].hist(sca_scores, bins=5, color='green', alpha=0.7)
axes[0, 1].set_title('Simple Combinatorial Auction Scores')
axes[0, 2].hist(sca_filtered_scores, bins=5, color='purple', alpha=0.7)
axes[0, 2].set_title('Filtered SCA Scores')

axes[1, 0].hist(batch_rewards_list, bins=5, color='blue', alpha=0.7)
axes[1, 0].set_title('Batch Auction Rewards')
axes[1, 1].hist(sca_rewards_list, bins=5, color='green', alpha=0.7)
axes[1, 1].set_title('Simple Combinatorial Auction Rewards')
axes[1, 2].hist(sca_filtered_rewards_list, bins=5, color='purple', alpha=0.7)
axes[1, 2].set_title('Filtered SCA Rewards')

plt.tight_layout()
plt.show()

# Print average scores and rewards
print(f'Average Batch Auction Score: {sum(batch_scores)/num_runs:.2f}, Average Rewards: {sum(batch_rewards_list)/num_runs:.2f}, Negative Rewards: {batch_negative}')
print(f'Average Simple Combinatorial Auction Score: {sum(sca_scores)/num_runs:.2f}, Average Rewards: {sum(sca_rewards_list)/num_runs:.2f}, Negative Rewards: {sca_negative}')
print(f'Average Filtered SCA Score: {sum(sca_filtered_scores)/num_runs:.2f}, Average Rewards: {sum(sca_filtered_rewards_list)/num_runs:.2f}, Negative Rewards: {sca_filtered_negative}')

