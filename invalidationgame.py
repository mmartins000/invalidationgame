#!/usr/local/bin/python3

# InvalidationGame v0.1
# Author: Marcelo Martins (stakey.club)
# Source: https://github.com/mmartins000/invalidationgame
# Simulates a (double-spending) blockchain attack

# This script simulates an attack on a (simulated) pure PoW blockchain mining mechanisms
# like Bitcoin and also of a PoW + PoS hybrid mining blockchains
# like the one introduced by Decred Project (https://decred.org)
# Named after "The Imitation Game"

# Purpose: understand the security provided by PoW + PoS mechanism
# Why double-spending attack? Because the attacks cost upfront money (PoW)
# and the adversary attacking the network must have economic incentive to execute the attack.
# Another scenario to investigate would be the sabotage performed by wealthy adversaries, like governments.
# For Assumptions and Caveats, please check README.md file in Github repository.

# Execution example 1: Pure PoW, 1 simulation, save output to file sim_pow.txt:
# $ python invalidationgame.py -w 50.01 -w 49.99 -o sim_pow.txt

# Execution example 2: PoW + PoS, 1 simulation, save output to file invalidationgame.json5:
# $ python invalidationgame.py -w 50 -w 50 -s 50 -s 50

# Execution example 3: PoW + PoS, 3 simulations, adversary A1 trying to rewrite last two blocks,
# save output to file sim_pow_pos2.txt:
# $ python invalidationgame.py -w 50 -w 50 -s 50 -s 50 -i 3 --block-rewind 2 -o sim_pow_pos2.txt

# Execution example 4: PoW + PoS, 1 simulation, logging debug level information:
# $ python invalidationgame.py -w 50 -w 50 -s 50 -s 50 --log-level DEBUG

import argparse
import random
import pprint
import statistics
import datetime
import logging
import os
from stat import *
import configparser

__author__ = "Marcelo Martins (stakey.club)"
__license__ = "GNU GPL 3"
__version__ = "0.1"

simulations = {}
adversaries = {}
block_diff_2 = list()
block_diff_6 = list()
sim_duration_times = list()
batch_start_time = datetime.datetime.now()
batch_end_time = datetime.datetime.now()

block_hash_space = 10000             # 10000 (instead of 100) allows for two floating point hashpower number
pos_avg_ticket_pool_size = 40960
# Number of blocks with 3 votes: 5617; 4 votes: 22561; 5 votes: 401716; Total blocks: 429894 (100%)
pos_blocks_with_5votes = 401716      # Numbers from Decred blockchain
pos_blocks_with_4votes = 22561       # Extracted from dcrdata PostgreSQL database
pos_blocks_with_3votes = 5617        # from 08.02.16 to 08.02.20
pos_blocks_with_votes = pos_blocks_with_5votes + pos_blocks_with_4votes + pos_blocks_with_3votes
pos_prop_blocks_5votes = pos_blocks_with_5votes / pos_blocks_with_votes
pos_prop_blocks_4votes = pos_blocks_with_4votes / pos_blocks_with_votes
pos_prop_blocks_3votes = pos_blocks_with_3votes / pos_blocks_with_votes


def restricted_float(x):
    try:
        x = float(x)
    except ValueError:
        raise argparse.ArgumentTypeError("%r not a floating-point literal" % (x,))

    if not 0.0 <= x <= 100.0:
        raise argparse.ArgumentTypeError("%r not in range [0.0, 100.0]" % (x,))
    return x


def restricted_int(x):
    try:
        x = int(x)
    except ValueError:
        raise argparse.ArgumentTypeError("%r not a int literal" % (x,))

    if not x > 0:
        raise argparse.ArgumentTypeError("%r not greater then 0" % (x,))
    return x


def restricted_mode(x):
    if x != 'w' and x != 'a':
        raise argparse.ArgumentTypeError("%r not equal 'w' or 'a'" % (x,))
    return x


def restricted_regular_file(file):
    if os.path.isfile(file):
        # Avoid sockets, fifos, symbolic links, etc
        if not S_ISREG(os.stat(file).st_mode):
            raise argparse.ArgumentTypeError("%r not a regular file" % (file,))

        # Avoid overwriting executables
        if os.access(file, os.X_OK):
            raise argparse.ArgumentTypeError("%r is an executable file" % (file,))

    return file


parser = argparse.ArgumentParser()
parser.add_argument("-v", "--version", dest='version', action='store_true', help="Prints version")
parser.add_argument("-o", "--output", dest='outputfile', help="Saves simulations to output file",
                    default='invalidationgame.json5', type=restricted_regular_file)
parser.add_argument("-w", "--pow", dest='pow', help="Informs adversaries' PoW hashpower",
                    action='append', type=restricted_float)
parser.add_argument("-s", "--pos", dest='pos', help="Informs adversaries' PoS stake size",
                    action='append', type=restricted_float)
parser.add_argument("-i", "--simulations", dest='simulations', help="Number of simulations to be run",
                    default=1, type=restricted_int)
parser.add_argument("-c", "--config", dest='configfile', help="Configuration file", default='invalidationgame.conf',
                    type=restricted_regular_file)
parser.add_argument("--verbose", dest='verbose', action='store_true', help="Prints the simulation at the end")
parser.add_argument("--log-level", dest='loglevel', default='ERROR', help="Logs this level and above to the screen")
parser.add_argument("--log-file", dest='logfile', default='invalidationgame.log',
                    help="Logs to the selected file. Default: invalidationgame.log", type=restricted_regular_file)
parser.add_argument("--log-mode", dest='logmode', default='w',
                    help="Overwrite (w) or append (a) to log file. Default: w", type=restricted_mode)
parser.add_argument("--output-mode", dest='outputmode', default='w',
                    help="Overwrite (w) or append (a) to output file. Default: w", type=restricted_mode)
parser.add_argument("--rewind-blocks", dest='rewind_blocks', default=0,
                    help="Number of blocks to pre-mine for an adversary. Default: 0", type=restricted_int)
parser.add_argument("--rewind-adv", dest='rewind_adv', default=0,
                    help="Which adversary will be ahead in number of blocks (advantage). Default: 0",
                    type=restricted_int)
parser.add_argument("--no-output-json", dest='nooutputjson', action='store_true',
                    help="Doesn't output the simulations to a JSON file at the end")
parser.add_argument("--no-erase-prob", dest='noeraseprob', action='store_true',
                    help="Doesn't erase prob_block_hashes from adversary array object")
parser.add_argument("--no-erase-drawn", dest='noerasedrawn', action='store_true',
                    help="Doesn't erase drawn_blocks from adversary array object")
parser.add_argument("--no-create-config", dest='nocreateconfig', action='store_true',
                    help="Doesn't create the configuration file from default values")
parser.add_argument("--runtest", dest='runtest', action='store_true', help="Tests basic functionality and exits")
args = parser.parse_args()


def print_version():
    print("InvalidationGame, version", __version__)
    exit(0)


def sanity_check(adv_hashpower, adv_stake, rewind_adv):
    if type(adv_hashpower) == list:
        if len(adv_hashpower) < 2:
            print("Error: When simulating PoW attacks, a minimum of 2 adversaries are required. Use --help for help.")
            exit(1)
    else:
        print("Error: When simulating PoW attacks, a minimum of 2 adversaries are required. Use --help for help.")
        exit(1)

    total_pow_hashpower = sum(round(float(x), 2) for x in adv_hashpower)
    if total_pow_hashpower != 100:
        print("Error: Total hashpower must sum 100, but summed", str(total_pow_hashpower))
        exit(2)

    if adv_stake:
        total_pos_stake = sum(round(float(x), 2) for x in adv_stake)
        if total_pos_stake != 100:
            print("Error: Total staked must sum 100, but summed", str(total_pos_stake))
            exit(3)

        if len(adv_hashpower) != len(adv_stake):
            print("Error: The number of PoW and PoS adversaries don't match")
            exit(1)

    if rewind_adv + 1 > len(adv_hashpower):     # rewind_adv starts in 0
        print("Error: Adversary in advantage and hashpower settings don't match")
        exit(4)


def create_config(config_file):
    if not args.nocreateconfig:
        global pos_avg_ticket_pool_size, pos_blocks_with_5votes, pos_blocks_with_4votes, pos_blocks_with_3votes, \
            block_hash_space
        # Will keep variables with default values from the beginning
        config = configparser.ConfigParser()
        config.optionxform = lambda option: option
        config['TICKET_POOL'] = {'AverageTicketPoolSize': str(pos_avg_ticket_pool_size),
                                 'BlocksWith5Votes': str(pos_blocks_with_5votes),
                                 'BlocksWith4Votes': str(pos_blocks_with_4votes),
                                 'BlocksWith3Votes': str(pos_blocks_with_3votes)}
        config['HASH_SPACE'] = {'BlockHashSpace': str(block_hash_space)}
        # Creates a default config file
        try:
            with open(config_file, 'w') as cfh:
                config.write(cfh)
        except PermissionError:
            logging.error("Missing write permission while saving configuration to", config_file)
            pass
        else:
            logging.info("Saved configuration to " + config_file)


def read_config(config_file):
    global pos_avg_ticket_pool_size, pos_blocks_with_5votes, pos_blocks_with_4votes, pos_blocks_with_3votes, \
        block_hash_space, pos_blocks_with_votes, pos_prop_blocks_5votes, pos_prop_blocks_4votes, pos_prop_blocks_3votes
    # Reads the config file
    config = configparser.ConfigParser()
    config.read(config_file)
    if not config.sections():
        create_config(config_file)
    else:
        pos_avg_ticket_pool_size = restricted_int(int(config['TICKET_POOL']['AverageTicketPoolSize']))
        pos_blocks_with_5votes = restricted_int(int(config['TICKET_POOL']['BlocksWith5Votes']))
        pos_blocks_with_4votes = restricted_int(int(config['TICKET_POOL']['BlocksWith4Votes']))
        pos_blocks_with_3votes = restricted_int(int(config['TICKET_POOL']['BlocksWith3Votes']))
        block_hash_space = restricted_int(int(config['HASH_SPACE']['BlockHashSpace']))
        # Recalculate ticket proportions with read values
        pos_blocks_with_votes = pos_blocks_with_5votes + pos_blocks_with_4votes + pos_blocks_with_3votes
        pos_prop_blocks_5votes = pos_blocks_with_5votes / pos_blocks_with_votes
        pos_prop_blocks_4votes = pos_blocks_with_4votes / pos_blocks_with_votes
        pos_prop_blocks_3votes = pos_blocks_with_3votes / pos_blocks_with_votes


def calc_hashpower(adv_hashpower, adv_stake):
    global adversaries
    adversaries = {}
    for idx, a in enumerate(adv_hashpower):
        adv_id = "A" + str(idx)
        adversaries[adv_id] = {}
        adversaries[adv_id]["hashpower"] = a
        adversaries[adv_id]["drawn_block_hashes"] = list()
        adversaries[adv_id]["chain"] = {}
        adversaries[adv_id]["sum_blocks"] = 0

        # Won't remove the block hashes already selected; one block hash can be owned by two adversaries
        # This only means that they can mine a block roughly at the same time t;
        adversaries[adv_id]["prob_block_hashes"] = \
            random.sample(range(block_hash_space), k=round(round(float(a), 2) * 100))

    if args.pos:
        ticket_pool = range(pos_avg_ticket_pool_size)
        for idx, s in enumerate(adv_stake):
            adv_id = "A" + str(idx)
            # Validated and invalidated blocks are set here to avoid KeyError exceptions
            adversaries[adv_id]["validated_blocks"] = 0
            adversaries[adv_id]["invalidated_blocks"] = 0
            adversaries[adv_id]["stakesize"] = s
            adversaries[adv_id]["prob_tickets"] = \
                random.sample(ticket_pool, k=round(round(float(s), 2) / 100 * pos_avg_ticket_pool_size))
            selected_tickets = set(adversaries[adv_id]["prob_tickets"])
            # Remove the tickets already selected; one ticket cannot be owned by multiple adversaries
            ticket_pool = [e for e in ticket_pool if e not in selected_tickets]

    # Generate info for calc_averages()
    for a in adversaries:
        adversaries[a]["pow_hashpower"] = "{:.2f}".format(len(adversaries[a]["prob_block_hashes"]) / 100) + "%"
        if adv_stake:
            adversaries[a]["pos_stakesize"] = \
                "{:.2f}".format(len(adversaries[a]["prob_tickets"]) * 100 / pos_avg_ticket_pool_size) + "%"
            logging.info(a + " hashpower: " + "{:.2f}".format(len(adversaries[a]["prob_block_hashes"]) / 100) + "% " +
                         "and stake size: " +
                         "{:.4f}".format(len(adversaries[a]["prob_tickets"]) * 100 / pos_avg_ticket_pool_size) + "%")
        else:
            logging.info(a + " hashpower:" + "{:.2f}".format(len(adversaries[a]["prob_block_hashes"]) / 100) + "%")


def setup_block_rewind(s, rewind_blocks, rewind_adv):
    # Generates a number of blocks for the selected adversary before simulation starts
    a = "A" + str(rewind_adv)
    for b in range(int(rewind_blocks)):
        simulations["sims"][str(s)]["cycles"][str(b)] = {}
        block_hash = "RWB" + str(b)
        simulations["sims"][str(s)]["cycles"][str(b)]["drawn_block_hash"] = block_hash
        simulations["sims"][str(s)]["cycles"][str(b)]["pow_winners"] = [a]
        adversaries[a]["drawn_block_hashes"].append(block_hash)

        # Add fake blocks to the "chain" node
        this_height = str(len(adversaries[a]["chain"])).zfill(3)
        adversaries[a]["chain"][this_height] = {}
        if not args.pos:
            # Pure PoW: Append fake block to the "chain"
            adversaries[a]["chain"][this_height].update({"block_hash": block_hash})
        else:
            # PoW + PoS: Append fake block to the "chain"
            adversaries[a]["chain"][this_height].update(
                {"block_hash": block_hash, "online_tickets": -1, "owned_tickets": [block_hash]})

        logging.info("Block height: " + str(b) + ", set up rewind block hash: " + block_hash + " for " + a)
    logging.info("Adversary " + a + " already mined " + str(len(adversaries[a]["drawn_block_hashes"])) + " blocks")


def create_simulation(s):
    simulations["sims"][str(s)] = {}
    simulations["sims"][str(s)]["cycles"] = {}


def mine_block(s, cycle_height):
    pow_winner = False
    while not pow_winner:
        # PoW mining
        # Could have random.sampled block hashes in calc_hashpower() as it was done for tickets (second for loop)
        # That way it would not be possible for multiple adversaries to mine a block roughly at same time t
        # because they would not be able to draw the same block hash
        # Instead, calc_hashpower() randomizes block hashes with replacements (first for loop)
        # This choice affects the way block hashes are drawn here
        draw_block_hash = random.choice(range(block_hash_space))
        # The dict is crated here to avoid KeyError when calc_distance() returns 0
        this_cycle_height = str(cycle_height).zfill(3)
        if cycle_height not in simulations["sims"][str(s)]["cycles"]:
            simulations["sims"][str(s)]["cycles"][this_cycle_height] = {}
        simulations["sims"][str(s)]["cycles"][this_cycle_height]["drawn_block_hash"] = draw_block_hash
        simulations["sims"][str(s)]["cycles"][this_cycle_height]["pow_winners"] = list()
        logging.info("Cycle height: " + this_cycle_height + ", drawn block hash: " + str(draw_block_hash))
        for a in adversaries:
            if draw_block_hash in adversaries[a]["prob_block_hashes"]:
                pow_winner = True
                adversaries[a]["drawn_block_hashes"].append(str(draw_block_hash))
                simulations["sims"][str(s)]["cycles"][this_cycle_height]["pow_winners"].append(a)
                logging.info("Cycle height: " + this_cycle_height + ", PoW winner: " + a)
                if not args.pos:
                    # pow_winner: Append block to the "chain"
                    this_height = str(len(adversaries[a]["chain"])).zfill(3)
                    adversaries[a]["chain"][this_height] = {}
                    adversaries[a]["chain"][this_height].update({"block_hash": draw_block_hash,
                                                                 "from_cycle": this_cycle_height})

        if not pow_winner:
            # This cycles are going to be ignored as if miners took more than average time to mine a block
            logging.info("No PoW winner for height " + this_cycle_height + "; next draw")

        else:   # If already selected at least one adversary as PoW miner; if not, will loop again
            # PoS mining
            if args.pos:  # If not, this simulation is a pure PoW and this code block can be skipped
                simulations["sims"][str(s)]["cycles"][this_cycle_height]["pos_winners"] = list()

                # Draws how many tickets will be drawn for this block based on historical proportions
                # defined in the beginning of this file
                pos_allowed_drawn_tickets = \
                    int(random.choices(
                        [5, 4, 3], [pos_prop_blocks_5votes, pos_prop_blocks_4votes, pos_prop_blocks_3votes],
                        k=1)[0])
                drawn_tickets = random.sample(range(1, pos_avg_ticket_pool_size), pos_allowed_drawn_tickets)
                logging.debug("Online tickets: " +
                              str(pos_allowed_drawn_tickets) + "; drawn tickets: " + str(drawn_tickets))

                pos_winner = False
                for a in adversaries:
                    adversaries[a]["drawn_tickets"] = [t for t in drawn_tickets if t in adversaries[a]["prob_tickets"]]
                    total_tickets = len(adversaries[a]["drawn_tickets"])

                    if a in simulations["sims"][str(s)]["cycles"][this_cycle_height]["pow_winners"]:
                        # adversary already won PoW
                        if total_tickets > pos_allowed_drawn_tickets // 2:
                            pos_winner = True
                            simulations["sims"][str(s)]["cycles"][this_cycle_height]["pos_winners"].append(a)
                            adversaries[a]["validated_blocks"] += 1
                            logging.debug("Tickets for adversary " + a + ": " +
                                          str(total_tickets) + "; drawn tickets: " +
                                          str(adversaries[a]["drawn_tickets"]))
                            logging.info("Cycle height: " + this_cycle_height + ", PoS winner: " + a)

                            # pow_winner and pos_winner: Append block to the "chain" after PoS validation
                            this_height = str(len(adversaries[a]["chain"]))
                            adversaries[a]["chain"][this_height] = {}
                            adversaries[a]["chain"][this_height].update(
                                {"block_hash": draw_block_hash,
                                 "from_cycle": this_cycle_height,
                                 "online_tickets": pos_allowed_drawn_tickets,
                                 "owned_tickets": adversaries[a]["drawn_tickets"]})
                        else:
                            logging.debug("Tickets for adversary " + a + ": " +
                                          str(total_tickets) + "; allowed drawn tickets: " +
                                          str(pos_allowed_drawn_tickets))
                            adversaries[a]["invalidated_blocks"] += 1
                            # Must undo the last block accounted for the adversary
                            # whose PoW mining has been invalidated
                            del adversaries[a]["drawn_block_hashes"][-1]

                if not pos_winner:
                    # If the adversary didn't have the necessary drawn tickets to validate his own blocks,
                    # we assume the block will be invalidated by the honest adversaries
                    pow_winner = False
                    logging.info("PoS and PoW winner don't match for block height " + this_cycle_height + "; next draw")


def calc_distance(s, cycle_height):
    if cycle_height < 1:
        return 0  # distance is 0 if we haven't started
    # elif cycle_height == 1:
    #     return 1    # distance is 1 from and to any adversary

    seq = list()
    for a in adversaries:
        seq.append(len(adversaries[a]["drawn_block_hashes"]))

    # Calculate probabilities of catching up: first part
    # The simulator allows for more than two adversaries...
    leading_height = max(seq)
    lagging_height = min(seq)
    leading_adv, lagging_adv = "", ""
    for a in adversaries:
        if len(adversaries[a]["drawn_block_hashes"]) == lagging_height:
            # Found the (last) lagging adversary to use later
            lagging_adv = a
        elif len(adversaries[a]["drawn_block_hashes"]) == leading_height:
            # Found the (last) lagging adversary to use later
            # If lagging_height == leading_height, this block won't run, leaving leading_adv == ""
            leading_adv = a

    # Calculate the maximum distance between any two adversaries
    distances = [abs(i - j) for i in seq for j in seq if i != j]
    try:
        calculated_distance = max(distances)
    except ValueError:
        calculated_distance = 0

    this_cycle_height = str(cycle_height).zfill(3)
    if calculated_distance == 2 and simulations["sims"][str(s)]["2-block-diff"] == -1:
        # Adding 1 because the cycle height starts in 0 and I want to know after how many cycles
        simulations["sims"][str(s)]["2-block-diff"] = cycle_height + 1    # first time reached 2-block distance

        # Who reached 2-block diff first and how many blocks were mined
        winner_list = {}
        for a in adversaries:
            winner_list.update({a: str(adversaries[a]["sum_blocks"])})
        winner = max(winner_list, key=winner_list.get)

        simulations["sims"][str(s)]["2-block-diff_winner"] = winner
        simulations["sims"][str(s)]["2-block-diff_winner_score"] = winner_list[winner]

        logging.info("2-block-diff updated with cycle height " + this_cycle_height +
                     " (after " + str(cycle_height + 1) + " cycles)")

    elif calculated_distance == 6:
        # Adding 1 because the cycle height starts in 0 and I want to know after how many cycles
        simulations["sims"][str(s)]["6-block-diff"] = cycle_height + 1    # reached 6-block distance

        # Who reached 6-block diff and how many blocks were mined
        winner_list = {}
        for a in adversaries:
            winner_list.update({a: str(adversaries[a]["sum_blocks"])})
        winner = max(winner_list, key=winner_list.get)

        simulations["sims"][str(s)]["6-block-diff_winner"] = winner
        simulations["sims"][str(s)]["6-block-diff_winner_score"] = winner_list[winner]

        logging.info("6-block-diff updated with cycle height " + this_cycle_height +
                     " (after " + str(cycle_height + 1) + " cycles)")
        logging.info("End of simulation reached with 6 blocks of difference")

    elif calculated_distance > 6:
        logging.critical("Error while calculating distance from adversaries (distances: " +
                         str(distances) + " calculated_distance: " + str(calculated_distance) + ")")
        exit(5)

    # Calculate probabilities of catching up: second part
    # Probability of success for the adversary that is lagging behind to catch up with leader
    if lagging_adv != "":
        q = adversaries[lagging_adv]["hashpower"] / 100
        if args.pos:
            # q *= (adversaries[lagging_adv]["stakesize"] / 100)
            q_hash = adversaries[lagging_adv]["hashpower"] / 100
            q_stake = adversaries[lagging_adv]["stakesize"] / 100
            q = pow(q_hash * q_stake, 1 - q_stake)

        # The information written to JSON refers to the distance and probability before
        # the mining done on this cycle, that is just starting
        str_prob = str(attacker_success_probability(q, calculated_distance))
        this_cycle_height = str(cycle_height).zfill(3)
        simulations["sims"][str(s)]["cycles"][this_cycle_height] = {}
        simulations["sims"][str(s)]["cycles"][this_cycle_height]["distance_before_this_cycle"] = calculated_distance
        simulations["sims"][str(s)]["cycles"][this_cycle_height]["probability_before_this_cycle"] = str_prob
        logging.debug("Cycle height: " + this_cycle_height +
                      ", distance before this cycle: " + str(calculated_distance))
        if leading_adv == "":   # If the first part wasn't run, they are at the same height
            logging.info("Probability of catching up is " + str_prob + " because their heights are the same")
        else:
            logging.info("Probability of " + lagging_adv + " catching up to " + leading_adv + ": " + str_prob)

    return calculated_distance


def run_simulation(s):
    sim_start_time = datetime.datetime.now()
    logging.info("Running simulation " + str(s))
    simulations["sims"][str(s)]["2-block-diff"] = -1
    simulations["sims"][str(s)]["6-block-diff"] = -1
    cycle_height = len(simulations["sims"][str(s)]["cycles"])

    # Simulation runs until we reach a 6-block distance from other chains
    while calc_distance(s, cycle_height) < 6:
        # This is the core, the most time-consuming function
        mine_block(s, cycle_height)

        for a in adversaries:
            sum_blocks = len(adversaries[a]["drawn_block_hashes"])
            adversaries[a]["sum_blocks"] = sum_blocks
            logging.info("Adversary " + a + " already mined " + str(sum_blocks) + " blocks")

        cycle_height += 1

    # At this point, distance == 6, this simulation is over
    # Clean up the JSON before saving the simulation to file, if that's the case
    for a in adversaries:
        if not args.noeraseprob:
            adversaries[a].pop('prob_block_hashes', None)
            adversaries[a].pop('prob_tickets', None)

        if not args.noerasedrawn:
            adversaries[a].pop('drawn_block_hashes', None)
            adversaries[a].pop('drawn_tickets', None)

    # Save the details before starting another simulation
    simulations["sims"][str(s)]["adversaries"] = adversaries

    # Save to calculate averages on calc_averages()
    block_diff_2.append(simulations["sims"][str(s)]["2-block-diff"])
    block_diff_6.append(simulations["sims"][str(s)]["6-block-diff"])
    sim_end_time = datetime.datetime.now()
    sim_duration_times.append(sim_end_time - sim_start_time)


def log_debug_info():
    logging.debug("Block Hash Space: " + str(block_hash_space))
    logging.debug("Average ticket pool size: " + str(pos_avg_ticket_pool_size))
    logging.debug("Number of blocks with 5 votes: " + str(pos_blocks_with_5votes))
    logging.debug("Number of blocks with 4 votes: " + str(pos_blocks_with_4votes))
    logging.debug("Number of blocks with 3 votes: " + str(pos_blocks_with_3votes))
    logging.debug("Total number of blocks with votes: " + str(pos_blocks_with_votes))
    logging.debug("Proportion of blocks with 5 votes: " + str(pos_prop_blocks_5votes))
    logging.debug("Proportion of blocks with 4 votes: " + str(pos_prop_blocks_4votes))
    logging.debug("Proportion of blocks with 3 votes: " + str(pos_prop_blocks_3votes))


def run_batch_simulations(total_simulations=1, rewind_blocks=0, rewind_adv=0):
    global batch_start_time, batch_end_time
    log_debug_info()
    logging.info("Starting simulation batch")
    batch_start_time = datetime.datetime.now()
    simulations["sims"] = {}
    for s in range(int(total_simulations)):
        calc_hashpower(args.pow, args.pos)
        create_simulation(s)
        int(rewind_blocks) > 0 and setup_block_rewind(s, rewind_blocks, rewind_adv)
        run_simulation(s)

    batch_end_time = datetime.datetime.now()
    logging.info("End of simulation batch")
    if args.verbose:
        print("Simulations:")
        pprint.pprint(simulations, indent=4)
    calc_averages()
    print_summary(args.simulations)
    save_output(args.outputfile)


def calc_averages():
    global block_diff_2, block_diff_6, simulations
    simulations["summary"] = {}

    simulations["summary"]["batch_start"] = batch_start_time.isoformat(' ')
    simulations["summary"]["batch_end"] = batch_end_time.isoformat(' ')
    # statistics.mean() can't be used for datetime.timedelta()
    sum_timedelta = datetime.timedelta()
    for idx, t in enumerate(sim_duration_times):
        sum_timedelta += sim_duration_times[idx]
    avg_timedelta = sum_timedelta / len(sim_duration_times)
    simulations["summary"]["sim_mean_time"] = avg_timedelta.total_seconds()

    simulations["summary"]["total"] = len(block_diff_2)                 # Total number of simulations
    simulations["summary"]["rewind_blocks"] = args.rewind_blocks        # Number of blocks to rewind
    simulations["summary"]["rewind_adv"] = "A" + str(args.rewind_adv)   # Adversary trying to back in history
    simulations["summary"]["pow"] = {}
    simulations["summary"]["pow"]["2-block-diff-average"] = round(statistics.mean(block_diff_2), 6)
    simulations["summary"]["pow"]["6-block-diff-average"] = round(statistics.mean(block_diff_6), 6)

    simulations["summary"]["total_wins"] = {}
    simulations["summary"]["perc_wins"] = {}
    simulations["summary"]["sum_blocks"] = {}
    for a in adversaries:
        simulations["summary"]["sum_blocks"][a] = {}
        sum_blocks_list = list()
        win_counts = 0
        for s in simulations["sims"]:
            if type(int(s)) == int:
                if simulations["sims"][str(s)]["6-block-diff_winner"] == a:
                    win_counts += 1
            sum_blocks_list.append(int(simulations["sims"][str(s)]["adversaries"][a]["sum_blocks"]))
        simulations["summary"]["total_wins"][a] = win_counts
        simulations["summary"]["perc_wins"][a] = str(round(win_counts / len(simulations["sims"]) * 100, 4)) + "%"
        simulations["summary"]["sum_blocks"][a]["average"] = round(statistics.mean(sum_blocks_list), 6)

    if args.pos:
        simulations["summary"]["pos"] = {}
        for a in adversaries:
            simulations["summary"]["pos"][a] = {}
            simulations["summary"]["pos"][a]["invalidated_blocks"] = list()
            simulations["summary"]["pos"][a]["validated_blocks"] = list()

        for s in simulations["sims"]:
            for a in simulations["sims"][str(s)]["adversaries"]:
                simulations["summary"]["pos"][a]["invalidated_blocks"].append(
                    simulations["sims"][str(s)]["adversaries"][a]["invalidated_blocks"])
                simulations["summary"]["pos"][a]["validated_blocks"].append(
                    simulations["sims"][str(s)]["adversaries"][a]["validated_blocks"])

        # This is the correct position for this code block
        for a in adversaries:
            simulations["summary"]["pos"][a]["invalidated_blocks-average"] = \
                round(statistics.mean(simulations["summary"]["pos"][a]["invalidated_blocks"]), 6)
            simulations["summary"]["pos"][a]["validated_blocks-average"] = \
                round(statistics.mean(simulations["summary"]["pos"][a]["validated_blocks"]), 6)


def print_summary(num_sims=1):
    if not args.pos:
        print("\nPure PoW simulation:")
        print("--------------------")
        print("Number of simulations:", simulations["summary"]["total"])
        if simulations["summary"]["rewind_blocks"] > 0:
            print("Simulating that adversary", simulations["summary"]["rewind_adv"], "is",
                  simulations["summary"]["rewind_blocks"], "blocks ahead")

        # Table section
        table = {}
        for a in adversaries:
            table.update({a: {'hpow': adversaries[a]["pow_hashpower"],
                              'sims_wins_n': simulations["summary"]["total_wins"][a],
                              'sims_wins_p': simulations["summary"]["perc_wins"][a]
                              }})

        print(f'{"Adversary":9} {"Hashpower":>10} {"Simulations won":>16} {"Simulations won":>16}')
        for adv in table.items():
            print(f'{adv[0]:9} {adv[1]["hpow"]:>10} {adv[1]["sims_wins_n"]:>16} {adv[1]["sims_wins_p"]:>16}')

        # After table
        batch_duration = batch_end_time - batch_start_time
        print("Total time for the batch of simulations:", batch_duration. total_seconds(), "seconds")
        print("Average duration of simulations:", simulations["summary"]["sim_mean_time"], "seconds")
        print(f'{"Average of " if int(num_sims) > 1 else ""}2-block advantage for', len(block_diff_2),
              f'{"simulation" if int(num_sims) < 2 else "simulations"} reached in:',
              simulations["summary"]["pow"]["2-block-diff-average"])
        print(f'{"Average of " if int(num_sims) > 1 else ""}6-block advantage for', len(block_diff_6),
              f'{"simulation" if int(num_sims) < 2 else "simulations"} reached in:',
              simulations["summary"]["pow"]["6-block-diff-average"])

        # Attacker success probability:
        for a in adversaries:
            q = float(adversaries[a]["hashpower"]) / 100
            if q < 0.50:
                print("Attacker probability of catching up for " + a + ": (z=number of blocks behind)")
                str_zp = ""
                for z in range(1, 7):
                    str_zp += "z=" + str(z) + ", p=" + \
                              str(round(attacker_success_probability(q, z), 6)) + \
                              "; "
                print(str_zp)
    else:
        print("\nPoW + PoS simulation:")
        print("_____________________")
        print("Number of simulations:", simulations["summary"]["total"])
        if simulations["summary"]["rewind_blocks"] > 0:
            print("Simulating that adversary", simulations["summary"]["rewind_adv"], "is",
                  simulations["summary"]["rewind_blocks"],
                  f'{"block" if int(simulations["summary"]["rewind_blocks"]) < 2 else "blocks"} ahead')

        # Table section
        table = {}
        for a in adversaries:
            table.update({a: {'hpow': adversaries[a]["pow_hashpower"],
                              'ssize': adversaries[a]["pos_stakesize"],
                              'sims_wins_n': simulations["summary"]["total_wins"][a],
                              'sims_wins_p': simulations["summary"]["perc_wins"][a],
                              'inv_blocks': simulations["summary"]["pos"][a]["invalidated_blocks-average"],
                              'val_blocks': simulations["summary"]["pos"][a]["validated_blocks-average"]}})

        print(f'{"Adversary":9} {"Hashpower":>10} {"Stake":>10} '
              f'{"Simulations won":>16} {"Simulations won":>16} {"Avg Invalidated Blocks":>23} '
              f'{"Avg Validated Blocks":>21}')
        for adv in table.items():
            print(f'{adv[0]:9} {adv[1]["hpow"]:>10} {adv[1]["ssize"]:>10} {adv[1]["sims_wins_n"]:>16} '
                  f'{adv[1]["sims_wins_p"]:>16} {adv[1]["inv_blocks"]:>23} {adv[1]["val_blocks"]:>21}')

        # After table
        print("Total time for the batch of simulations:", batch_end_time - batch_start_time)
        print("Average duration of simulations:", simulations["summary"]["sim_mean_time"], "seconds")
        print(f'{"Average of " if int(num_sims) > 1 else ""}2-block advantage for', len(block_diff_2),
              f'{"simulation" if int(num_sims) < 2 else "simulations"} reached in:',
              simulations["summary"]["pow"]["2-block-diff-average"], "blocks")
        print(f'{"Average of " if int(num_sims) > 1 else ""}6-block advantage for', len(block_diff_6),
              f'{"simulation" if int(num_sims) < 2 else "simulations"} reached in:',
              simulations["summary"]["pow"]["6-block-diff-average"], "blocks")

        # Attacker success probability:
        for a in adversaries:
            q_hash = adversaries[a]["hashpower"] / 100
            q_stake = adversaries[a]["stakesize"] / 100
            q = pow(q_hash * q_stake, 1 - q_stake)
            if q <= 0.50:
                print("Attacker probability of catching up for " + a + ": (z=number of blocks behind)")
                str_zp = ""
                for z in range(1, 7):
                    str_zp += "z=" + str(z) + ", p=" + \
                              str(round(attacker_success_probability(q, z), 6)) + \
                              "; "
                print(str_zp)

    # Losses amount
    loss_list = list()
    for i in table:
        loss_list.append(table[i]["sims_wins_n"])
    if max(loss_list) != min(loss_list):
        # We have winners and losers; print about the losers
        for a in adversaries:
            if (simulations["summary"]["sum_blocks"][a]["average"] > 0) and \
                    (int(table[a]["sims_wins_n"]) < max(loss_list)):
                if args.pos:
                    print("Assuming that", a, "won\'t fork the blockchain, the attack cost",
                          simulations["summary"]["sum_blocks"][a]["average"], "PoW block reward, on average,",
                          "due to PoS invalidation of bad PoW mined blocks.")
                else:
                    print("Assuming that", a, "won\'t fork the blockchain, the attack cost",
                          simulations["summary"]["sum_blocks"][a]["average"],
                          "PoW block reward, on average.")
            elif simulations["summary"]["sum_blocks"][a]["average"] == 0:
                print("Assuming that", a, "won\'t try to fork the blockchain,", a, "won't forgo any PoW reward",
                      "because no block was successfully mined.")
    else:
        # We have a draw; print about all of them
        print("Assuming that no adversary will fork the blockchain:")
        for a in adversaries:
            if (simulations["summary"]["sum_blocks"][a]["average"] > 0) and \
                    (int(table[a]["sims_wins_n"]) <= max(loss_list)):
                print(a, "lost the equivalent of",
                      simulations["summary"]["sum_blocks"][a]["average"], "PoW block rewards, on average")


def save_output(output_file):
    if output_file and not args.nooutputjson:
        try:
            with open(output_file, args.outputmode) as ofh:
                pprint.pprint(simulations, ofh)
        except PermissionError:
            logging.error("Missing write permission while saving output to", output_file)
            exit(6)
        else:
            logging.info("Saved simulation JSON object to " + output_file)


def config_logging(logfile, logmode, loglevel):
    numeric_log_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_log_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    try:
        logging.raiseExceptions = False
        logging.basicConfig(format='%(levelname)s:%(message)s',
                            filename=logfile, filemode=logmode, level=numeric_log_level)
    except PermissionError:
        print("Missing write permission while saving logs to", logfile)
        pass


def attacker_success_probability(q, z):
    # Ported to Python from Bitcoin whitepaper
    # (Satoshi Nakamoto, 2009, page 7, available at https://bitcoin.org/bitcoin.pdf)
    import math
    p = float(1.0 - q)
    lambda_var = float(z * (q / p))
    sum_value = 1.0
    for k in range(0, z + 1):
        poisson = float(math.exp(-lambda_var))
        for i in range(1, k + 1):
            poisson *= lambda_var / i
        sum_value -= poisson * (1 - pow(q / p, z - k))
    return sum_value


def test_attacker_success_probability(q=0.1):
    # Expect the same results as in Bitcoin whitepaper page 8, available at https://bitcoin.org/bitcoin.pdf
    print("q =", q)
    for z in range(0, 11):
        print("z =", z, "P =", attacker_success_probability(q, z))


def main():
    try:
        if args.runtest:
            test_attacker_success_probability()
            args.verbose = True
            args.pow = [90, 10]     # Pure PoW: A0 represents the honest nodes (90%)
            args.pos = []           # and A1 a dishonest adversary (10%)
            run_batch_simulations(total_simulations=1, rewind_blocks=0, rewind_adv=0)
        else:
            run_batch_simulations(total_simulations=args.simulations, rewind_blocks=args.rewind_blocks,
                                  rewind_adv=args.rewind_adv)
    except KeyboardInterrupt:
        print("Keyboard interruption. Simulation terminated.")
        logging.critical("Keyboard interruption. Simulation terminated.")
        exit(7)
    exit(0)


if __name__ == "__main__":
    args.version and print_version()
    config_logging(args.logfile, args.logmode, args.loglevel)
    args.runtest or sanity_check(args.pow, args.pos, args.rewind_adv)
    read_config(args.configfile)

    main()
