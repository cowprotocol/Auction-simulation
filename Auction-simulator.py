import itertools
import random
import time
import matplotlib.pyplot as plt
from copy import deepcopy

# Parameters
n = 7 # Number of items
s = 15  # Number of bidders
increase_min, increase_max = -0.45, 0.05 #the additional efficiencies from batching orders (or smaller batched) is calculated by: drawing a value v between these two parameters, and then multipylyng the value of the individual orders (or smaller batches) by min(1,v) 
valuation_min, valuation_max = -10, 30 #the amount that a solver can return when executing a single order is a uniform random variable between these two values. Limit prices are assumed zero, so negative values means that the solver has no solution for the order
num_runs = 10
max_runs = 100000 #max iterations when looking for the solution of the Combinatorial auction, after which a "timeout" is declared

# Helper to calculate the best partition of a set. Unlike the later function that computes the ourcome of the combinatorial auction, here is important that we keep track of the value of each item in a bundle (and not just the total value of a bundle)
def best_partition(subset, valuations):
    if subset in valuations:
        return valuations[subset]
    else:
        max_value = float('-inf')
        best_valuation = {}
        for i in range(1, len(subset)):
            for partition in itertools.combinations(subset, i):
                part1 = frozenset(partition)
                part2 = subset - part1
                valuation1 = deepcopy(best_partition(part1, valuations))
                valuation2 = deepcopy(best_partition(part2, valuations))
                total_value = sum(valuation1.values()) + sum(valuation2.values())
                if total_value > max_value:
                    max_value = total_value
                    best_valuation = valuation1.copy()
                    best_valuation.update(valuation2)
        return best_valuation

# helper function to filter a set of bids based on some reference values: filters bids by keeping only those for which each item's valuation is greater than the provided reference values. You can also specify a bundle size that will not be filtered 

def filter_bids_by_reference(valuations, reference_values, no_filter_bundle_size=-1):
    filtered_valuations = {
        bundle: deepcopy(valuation)
        for bundle, valuation in valuations.items()
        if len(bundle) == no_filter_bundle_size or all(valuation[item] >= reference_values[item] for item in bundle)
    }
    return filtered_valuations


# generate bidders' valuation and bids, compute the reference for fairness, and output both the unfiltered set of bids and the filtered sets of bids
def generate_bidder_valuations():
    bidder_valuations = {}
    bidder_valuations_fair = {}
    reference = deepcopy(limit_prices)

    for bidder in range(1, s + 1):
        valuations = {}
        for item in range(n):
            value = random.uniform(valuation_min, valuation_max)
            valuations[frozenset([item])] = {item: value}

            if value > reference[item]:
                reference[item] = value

        for k in range(2, n + 1):
            for bundle in itertools.combinations(range(n), k):
                bundle_set = frozenset(bundle)
                partition_valuation = best_partition(bundle_set, valuations)

                increase_percentage = max(0, random.uniform(increase_min, increase_max))
                partition_valuation = deepcopy(partition_valuation)
                for item in partition_valuation:
                    partition_valuation[item] *= (1 + increase_percentage)
                valuations[bundle_set] = deepcopy(partition_valuation)

        valuations_above_limit = filter_bids_by_reference(valuations, limit_prices)
        bidder_valuations[bidder] = valuations_above_limit
        valuations_above_reference = filter_bids_by_reference(valuations_above_limit, reference, 1)
        bidder_valuations_fair[bidder] = valuations_above_reference

  #  print(f'limit prices {limit_prices}')
   # print(f'reference for fairness{reference}')
  #  print(f' bidder valuations {bidder_valuations}')
  #  print(f' bidders valuations filtered {bidder_valuations_fair}')
    return bidder_valuations, bidder_valuations_fair

# smulates a repeated batch auction (repeat until all orders are executed)
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

# simulates a simple combinatorial auction (which looks at the bid with the highest score, then the bid with the second-highest score, and so on). Note that the winners of the simple combinatorial auction are the same as the winners in the repeated batch auctions
def run_simple_combinatorial_auction(bidder_valuations):
    winning_bids  = run_batch_auctions(bidder_valuations)
    total_value = sum(value for _, _, value, _ in winning_bids)
    rewards = {}
    for bidder in set(b for b, _, _, _ in winning_bids):
        valuations_without_bidder = {b: v for b, v in bidder_valuations.items() if b != bidder}
        cf_winning_bids = run_batch_auctions(valuations_without_bidder)
        cf_total_value = sum(value for _, _, value, _ in cf_winning_bids)
        rewards[bidder] = total_value - cf_total_value
    return winning_bids, rewards

# simulated the full combinatorial auction
def combinatorial_auction_with_timeout(bidder_valuations, calculate_rewards=1 ):
    # Convert bidder_valuations to [(bidder, subset, total_value of the subset)]
    subsets_with_values = [
        (bidder, set(bundle), sum(valuation_dict[item] for item in bundle))
        for bidder, bundles in bidder_valuations.items()
        for bundle, valuation_dict in bundles.items()
    ]
    subsets_with_values.sort(key=lambda x: x[2], reverse=True)

    # Prepare subsets and subset values dictionary with bidder tracking
    subsets = [set(subset) for _, subset, _ in subsets_with_values]
    subset_values = {(bidder, frozenset(subset)): value for bidder, subset, value in subsets_with_values}
    S = set().union(*subsets)

    best_value = float('-inf')
    best_partition = []
    rewards={}
    
    timed_out = 0
    counter = 0
    
    highest_bidder_for_subset = {}
    for bidder, subset, value in subsets_with_values:
         subset_frozen = frozenset(subset)
         if subset_frozen not in highest_bidder_for_subset:
            highest_bidder_for_subset[subset_frozen] = bidder


    def backtrack(remaining, current_partition, current_value):
        nonlocal best_value, best_partition, counter, timed_out

        if current_value > best_value:
            best_value = current_value
            best_partition[:] = current_partition[:]  # Ensure best_partition is updated properly
            
        possible_subsets = [ subset for subset in highest_bidder_for_subset.keys() if subset.issubset(remaining) ]
        
        for subset in possible_subsets:
           if counter < max_runs:
             counter += 1
             bidder = highest_bidder_for_subset[subset]  # Direct lookup
             subset_value = subset_values[(bidder, subset)]
             backtrack(remaining - subset, current_partition + [[bidder, subset]], current_value + subset_value )
        else:
            timed_out = 1
            return
    
    backtrack(S, [], 0)
    
    if calculate_rewards == 1:
        for bidder in set(b for b, _ in best_partition):
            valuations_without_bidder = {b: v for b, v in bidder_valuations.items() if b != bidder}
            _, _, cf_total_value, _ = combinatorial_auction_with_timeout(valuations_without_bidder, calculate_rewards=0)
            rewards[bidder] = best_value - cf_total_value
 #   print(counter)
    return best_partition, rewards, best_value, timed_out




# Main simulation loop
batch_scores, sca_scores, sca_filtered_scores, CA_scores, CA_scores_fair = [], [], [], [], []
batch_rewards_list, sca_rewards_list, sca_filtered_rewards_list, CA_rewards, CA_rewards_fair, num_auctions_list = [], [], [], [], [], []
batch_negative, sca_negative, sca_filtered_negative, CA_rewards_negative, CA_rewards_negative_fair, T_out_count, T_out_fair_count = 0, 0, 0, 0, 0, 0, 0

for run in range(num_runs):
    print(f"Run {run}/{num_runs}")
    limit_prices={item: 0 for item in range(n)}
    bidder_valuations, bidder_valuations_fair = generate_bidder_valuations()

 #   print(bidder_valuations)
 #   print(bidder_valuations_fair)
    
    batch_results = run_batch_auctions(bidder_valuations)
    num_auctions_list.append(len(batch_results))
    batch_scores.append(sum(value for _, _, value, _ in batch_results))
    batch_rewards = [reward for _, _, _, reward in batch_results]
    batch_rewards_list.append(sum(batch_rewards))
    batch_negative += sum(1 for r in batch_rewards if r < 0)
    

    _, CA_rew, score, T_out = combinatorial_auction_with_timeout(bidder_valuations)
    CA_scores.append(score)
    CA_rewards.append(CA_rew)
    CA_rewards_negative += sum(1 for r in CA_rew.values() if r < 0)
    T_out_count += T_out
    
    _, CA_rew_fair, score_fair, T_out_fair  = combinatorial_auction_with_timeout(bidder_valuations_fair)
    CA_scores_fair.append(score_fair)
    CA_rewards_fair.append(CA_rew_fair)
    CA_rewards_negative_fair += sum(1 for r in CA_rew_fair.values() if r < 0)
    T_out_fair_count += T_out_fair

    sca_results, sca_rewards = run_simple_combinatorial_auction(bidder_valuations)
    sca_scores.append(sum(value for _, _, value, _ in sca_results))
    sca_rewards_list.append(sum(sca_rewards.values()))
    sca_negative += sum(1 for r in sca_rewards.values() if r < 0)
    if score < sum(value for _, _, value, _ in sca_results):
        print("Error: combinatorial auction score < SCA score")
   
    filtered_results, sca_filtered_rewards = run_simple_combinatorial_auction(bidder_valuations_fair)
    sca_filtered_scores.append(sum(value for _, _, value, _ in filtered_results))
    sca_filtered_rewards_list.append(sum(sca_filtered_rewards.values()))
    sca_filtered_negative += sum(1 for r in sca_filtered_rewards.values() if r <= 0)

    if score_fair < sum(value for _, _, value, _ in filtered_results):
        print("Error: fair combinatorial auction score < SCA")

# Print average scores and rewards
print(f'Average Batch Auction Score: {sum(batch_scores)/num_runs:.2f}, Average Rewards: {sum(batch_rewards_list)/num_runs:.2f}, Negative Rewards: {batch_negative}, Average number of auctions {sum(num_auctions_list)/num_runs:.2f}')

SCA_Positive_rewards = [r for r in sca_rewards_list if r > 0]
print(f'Average Simple Combinatorial Auction Score: {sum(sca_scores)/num_runs:.2f}, Average Rewards: {sum(SCA_Positive_rewards)/num_runs:.2f}, Negative Rewards: {sca_negative}')

filtered_SCA_Positive_rewards = [r for r in sca_filtered_rewards_list if r > 0]
print(f'Average Fair Simple Combinatorial Auction Score: {sum(sca_filtered_scores)/num_runs:.2f}, Average Rewards: {sum(filtered_SCA_Positive_rewards)/num_runs:.2f}, Negative Rewards: {sca_filtered_negative}')

CA_Positive_rewards = sum(
    reward for rewards_dict in CA_rewards for reward in rewards_dict.values() if reward > 0
)
print(f'Average Combinatorial Auction Score: {sum(CA_scores)/num_runs:.2f}, Average Rewards: {CA_Positive_rewards/num_runs:.2f}, Negative Rewards: {CA_rewards_negative}, fraction of timeouts: {T_out_count/num_runs} ')

CA_Positive_rewards_fair = sum(
    reward for rewards_dict in CA_rewards_fair for reward in rewards_dict.values() if reward > 0
)
print(f'Average Fair Combinatorial Auction Score: {sum(CA_scores_fair)/num_runs:.2f}, Average Rewards: {CA_Positive_rewards_fair/num_runs:.2f}, Negative Rewards: {CA_rewards_negative_fair}, fraction of timeouts: {T_out_fair_count/num_runs}')
