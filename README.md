# InvalidationGame

InvalidationGame simulates a (double-spending) attack on a (simulated) version of pure PoW blockchain mining mechanisms like Bitcoin and also of a PoW + PoS hybrid mining blockchains like the one introduced by [Decred Project](https://decred.org).

Purpose: understand the security provided by PoW + PoS mechanism. PoS works like a 2FA mechanism, validating (or invalidating) the PoW processing.

Why double-spending attack? Because attacks cost upfront money (PoW) and the adversary attacking the network must have economic incentives to execute the attack.
Other possible scenarios would be:
- the sabotage performed by wealthy adversaries, like governments;
- an adversary mining empty blocks (low probability without economic incentives)

Stakeholders can withhold a miner’s reward invalidating blocks even if the block conforms to the consensus rules of the network. This desincentivizes bad behavior such as miners mining empty blocks or attempting double-spending attacks.
InvalidationGame was named after "The Imitation Game".

Please refer to the explanations given by Satoshi Nakamoto in the Bitcoin whitepaper from 2008, available at https://bitcoin.org/bitcoin.pdf:

"We consider the scenario of an attacker trying to generate an alternate chain faster than the honest chain. Even if this is accomplished, it does not throw the system open to arbitrary changes, such as creating value out of thin air or taking money that never belonged to the attacker. Nodes are not going to accept an invalid transaction as payment, and honest nodes will never accept a block containing them. An attacker can only try to change one of his own transactions to take back money he recently spent." (page 7).

"If a greedy attacker is able to assemble more CPU power than all the honest nodes, he would have to choose between using it to defraud people by stealing back his payments, or using it to generate new coins. He ought to find it more profitable to play by the rules, such rules that favour him with more new coins than everyone else combined, than to undermine the system and the validity of his own wealth." (page 4).

To learn more about Proof-of-Stake (PoS), take a look at [Decred PoS overview](https://docs.decred.org/proof-of-stake/overview/).

### Assumptions

1) An adversary is assumed to behave badly in order to 'game the system'. The adversary objective is to increase their outcomes by reducing costs or increasing profits. Such adversary may try to implement a double-spending attack or to mine an empty block.
2) More hashpower increases the probability of mining a block before the adversaries
3) A block is mined in average time for that blockchain protocol
4) Network propagation capacity is the same for all adversaries
5) Adversaries are not members of mining pools
6) Adversaries will always work on their own chain, without switching to a longer chain to restart the attack ("Once the transaction is sent, the dishonest sender starts working in secret on a parallel chain containing an alternate version of his transaction.", Bitcoin whitepaper, page 7)
7) All adversaries are connected to the same network all the time (DDoS attacks are not considered)
8) For PoW, both adversaries mining the same block hash mean they were able to mine a block at the same time (same cycle) on two different chains
9) For PoS, after one ticket is drawn another is bought and gets the same number, maintaining proportion between adversaries. It is also assumed that ticket prices are steady.
10) The simulation ends when one of the chains reaches a difference of 6 blocks from the others

### Caveats

1) There is no real blockchain mining happening under the hood. Just a bunch of random functions simulating a simplified version of a blockchain. Also, there are no transactions being processed.
2) Although it would be possible to do some real mining, it is complicated to separate processing power from a single multi-core CPU for multiple adversaries. Python multiprocessing or multithreading have limitations and it is not possible (to the best of my knowledge) to reserve percentual processing power for processes or threads.
3) To speed up and simplify the process, 'block hashes' are generated on-the-fly from a range of 10000 sequencial integers (to allow two floating point numbers representing hashpower percentages). Each adversary gets an amount of 'block hashes' according to their processing power. A single 'block hash' can be 'mined' by multiple adversaries at the same time. It only means that they were able to mine their block roughly at the same time t, not that they mined the same block or that their blocks have the same block hash. 
4) To simulate concurrency, processing cycles are used. A processing cycle is a 'for loop' where the action happens in sequence for all adversaries. The structure documented in the "cycles" node in the output JSON object shown below should not be confused for blockchain height which is registered in "chain" node. 
5) The proportions of online voting tickets (3, 4 or 5) per block were extracted from Decred blockchain using dcrdata. Learn more at Stakey Club: [Querying dcrdata](https://stakey.club/en/querying-dcrdata/).

### Rewind blocks

To simulate when one adversary is in advantage. Example: Adversary A0 represents the honest nodes and Adversary A1 the attacker. A1 spends a transaction hash and the seller waits a 2-block confirmation to provide goods/services. After 2 blocks, A1 decides to perform a double-spending attack. InvalidationGame can recreate this situation in a simulation where A1 will try to "rewind" the blockchain to that block height and start mining new blocks from there. 

## Release notes

This repository contains all InvalidationGame files (one file). 

## Requirements

Based on Python 3, requires only default libraries: argparse, random, pprint, statistics, datetime, logging, os, stat, configparser

- Clone this repository (or download the single Python script)

## Execution

### Tests

This script was successfully executed with:
- macOS Catalina 10.15.3
- Python 3.7.4

### Command line options

At least two PoW adversaries are required.
```
$ python invalidationgame.py --help
usage: invalidationgame.py [-h] [-v] [-o OUTPUTFILE] [-w POW] [-s POS]
                           [-i SIMULATIONS] [-c CONFIGFILE] [--verbose]
                           [--log-level LOGLEVEL] [--log-file LOGFILE]
                           [--log-mode LOGMODE] [--output-mode OUTPUTMODE]
                           [--rewind-blocks REWIND_BLOCKS]
                           [--rewind-adv REWIND_ADV] [--no-erase-prob]
                           [--no-erase-drawn] [--no-create-config] [--runtest]

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         Prints version
  -o OUTPUTFILE, --output OUTPUTFILE
                        Saves simulations to output file
  -w POW, --pow POW     Informs adversaries' PoW hashpower
  -s POS, --pos POS     Informs adversaries' PoS stake size
  -i SIMULATIONS, --simulations SIMULATIONS
                        Number of simulations to be run
  -c CONFIGFILE, --config CONFIGFILE
                        Configuration file
  --verbose             Prints the simulation at the end
  --log-level LOGLEVEL  Logs this level and above to the screen
  --log-file LOGFILE    Logs to the selected file. Default:
                        invalidationgame.log
  --log-mode LOGMODE    Overwrite (w) or append (a) to log file. Default: w
  --output-mode OUTPUTMODE
                        Overwrite (w) or append (a) to output file. Default: w
  --rewind-blocks REWIND_BLOCKS
                        Number of blocks to pre-mine for an adversary.
                        Default: 0
  --rewind-adv REWIND_ADV
                        Which adversary will be ahead in number of blocks
                        (advantage). Default: 0
  --no-erase-prob       Doesn't erase prob_block_hashes from adversary array
                        object
  --no-erase-drawn      Doesn't erase drawn_blocks from adversary array object
  --no-create-config    Doesn't create the configuration file from default
                        values
  --runtest             Tests basic functionality and exit
```

### Examples

```
Execution example 1: Pure PoW, 1 simulation, save output to file sim_pow.txt:
$ python invalidationgame.py -w 50.01 -w 49.99 -o sim_pow.txt

Execution example 2: PoW + PoS, 1 simulation, save output to file invalidationgame.json5:
$ python invalidationgame.py -w 50 -w 50 -s 50 -s 50

Execution example 3: PoW + PoS, 3 simulations, adversary A1 trying to rewrite last two blocks, save output to file sim_pow_pos2.txt:
$ python invalidationgame.py -w 50 -w 50 -s 50 -s 50 -i 3 --block-rewind 2 -o sim_pow_pos2.txt

Execution example 4: PoW + PoS, 1 simulation, logging debug level information:
$ python invalidationgame.py -w 50 -w 50 -s 50 -s 50 --log-level DEBUG
```

### Processing output

Sample stdout output:
```
PoW + PoS simulation:
_____________________
Number of simulations: 1
Adversary  Hashpower      Stake  Simulations won  Simulations won  Avg Invalidated Blocks  Avg Validated Blocks
A0            60.00%     67.00%                1           100.0%                       1                     6
A1            40.00%     33.00%                0             0.0%                       6                     0
Total time for the batch of simulations: 0:00:00.085523
Average duration of simulations: 0.032032 seconds
2-block difference for 1 simulation reached in: 3 blocks
6-block difference for 1 simulation reached in: 7 blocks
```

Sample JSON output:
```
{'sims': {'0': {'2-block-diff': 3,
                '2-block-diff_winner': 'A0',
                '2-block-diff_winner_score': '2',
                '6-block-diff': 7,
                '6-block-diff_winner': 'A0',
                '6-block-diff_winner_score': '6',
                'adversaries': {'A0': {'chain': {'0': {'block_hash': 2677,
                                                       'online_tickets': 5,
                                                       'owned_tickets': [23151,
                                                                         10386,
                                                                         4381]},
                                                 '1': {'block_hash': 1832,
                                                       'online_tickets': 5,
                                                       'owned_tickets': [8623,
                                                                         39394,
                                                                         20025,
                                                                         16238,
                                                                         25474]},
                                                 '2': {'block_hash': 3652,
                                                       'online_tickets': 5,
                                                       'owned_tickets': [25167,
                                                                         14301,
                                                                         20597]},
                                                 '3': {'block_hash': 2299,
                                                       'online_tickets': 5,
                                                       'owned_tickets': [26348,
                                                                         36727,
                                                                         26882,
                                                                         31441,
                                                                         9881]},
                                                 '4': {'block_hash': 5720,
                                                       'online_tickets': 5,
                                                       'owned_tickets': [9419,
                                                                         6256,
                                                                         6885,
                                                                         15808]},
                                                 '5': {'block_hash': 1861,
                                                       'online_tickets': 4,
                                                       'owned_tickets': [37355,
                                                                         39183,
                                                                         9022,
                                                                         34363]}},
                                       'hashpower': 60.0,
                                       'invalidated_blocks': 1,
                                       'pos_stakesize': '67.00%',
                                       'pow_hashpower': '60.00%',
                                       'stakesize': 67.0,
                                       'sum_blocks': 6,
                                       'validated_blocks': 6},
                                'A1': {'chain': {},
                                       'hashpower': 40.0,
                                       'invalidated_blocks': 6,
                                       'pos_stakesize': '33.00%',
                                       'pow_hashpower': '40.00%',
                                       'stakesize': 33.0,
                                       'sum_blocks': 0,
                                       'validated_blocks': 0}},
                'cycles': {'0': {'drawn_block_hash': 2677,
                                 'pos_winners': ['A0'],
                                 'pow_winners': ['A0']},
                           '1': {'drawn_block_hash': 1832,
                                 'pos_winners': ['A0'],
                                 'pow_winners': ['A0', 'A1']},
                           '2': {'drawn_block_hash': 3652,
                                 'pos_winners': ['A0'],
                                 'pow_winners': ['A0', 'A1']},
                           '3': {'drawn_block_hash': 2299,
                                 'pos_winners': ['A0'],
                                 'pow_winners': ['A0', 'A1']},
                           '4': {'drawn_block_hash': 5720,
                                 'pos_winners': ['A0'],
                                 'pow_winners': ['A0', 'A1']},
                           '5': {'drawn_block_hash': 1861,
                                 'pos_winners': ['A0'],
                                 'pow_winners': ['A0']},
                           '6': {'distance_before_this_cycle': 6,
                                 'probability_before_this_cycle': '0.0012620916488757833'}}}},
 'summary': {'batch_end': '2020-05-11 23:34:05.135781',
             'batch_start': '2020-05-11 23:34:05.050258',
             'perc_wins': {'A0': '100.0%', 'A1': '0.0%'},
             'pos': {'A0': {'invalidated_blocks': [1],
                            'invalidated_blocks-average': 1,
                            'validated_blocks': [6],
                            'validated_blocks-average': 6},
                     'A1': {'invalidated_blocks': [6],
                            'invalidated_blocks-average': 6,
                            'validated_blocks': [0],
                            'validated_blocks-average': 0}},
             'pow': {'2-block-diff-average': 3, '6-block-diff-average': 7},
             'rewind_adv': 'A0',
             'rewind_blocks': 0,
             'sim_mean_time': 0.032032,
             'sum_blocks': {'A0': {'average': 6}, 'A1': {'average': 0}},
             'total': 1,
             'total_wins': {'A0': 1, 'A1': 0}}}
```
