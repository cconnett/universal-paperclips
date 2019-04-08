# python3
"""Yomi tournament optimization."""

import collections
import concurrent.futures
import random

EVEN_SPLIT = object()
Score = collections.namedtuple('Score', 'hero_value villain_value')

Grid = collections.namedtuple('Grid', 'a b c d')


def Random(_):

  def Eval(_):
    return EVEN_SPLIT

  return Eval


def A100(_):

  def Eval(_):
    return 0

  return Eval


def B100(_):

  def Eval(_):
    return 1

  return Eval


def Greedy(grid):
  const = 0 if max(grid.a, grid.b) >= max(grid.c, grid.d) else 1

  def Eval(_):
    return const

  return Eval


def Generous(grid):
  const = 0 if max(grid.a, grid.c) >= max(grid.b, grid.d) else 1

  def Eval(_):
    return const

  return Eval


def Minimax(grid):
  const = 0 if min(grid.a, grid.c) <= min(grid.b, grid.d) else 1

  def Eval(_):
    return const

  return Eval


def TitForTat(_):

  def Eval(opp):
    return opp

  return Eval


def BeatLast(grid):
  """BeatLast strat."""
  best_moves = [0 if grid.a >= grid.c else 1, 0 if grid.b >= grid.d else 1]

  def Eval(opp):
    """Eval for BeatLast."""
    if opp == EVEN_SPLIT:
      hero = 0
      if grid.a >= grid.c:
        hero += (grid.a + grid.b) / 2
      else:
        hero += (grid.c + grid.d) / 2
      if grid.b >= grid.d:
        hero += (grid.a + grid.b) / 2
      else:
        hero += (grid.c + grid.d) / 2
      hero_expectation = hero / 2

      villain = 0
      if grid.a >= grid.c:
        villain += (grid.a + grid.c) / 2
      else:
        villain += (grid.b + grid.d) / 2
      if grid.b >= grid.d:
        villain += (grid.a + grid.c) / 2
      else:
        villain += (grid.b + grid.d) / 2
      villain_expecation = villain / 2

      return Score(hero_expectation, villain_expecation)
    return best_moves[opp]

  return Eval


ALL_STRATS = [
    'Random',
    'A100',
    'B100',
    'Greedy',
    'Generous',
    'Minimax',
    'TitForTat',
    'BeatLast',
]


def Flipped(grid):
  return grid._replace(b=grid.c, c=grid.b)


def RandomGrid():
  return Grid(*(random.randint(1, 10) for _ in range(4)))


def PrintGrid(grid):
  print(f'{grid.a:2d}, {grid.a:2d} | {grid.b:2d}, {grid.c:2d}')
  print(f'---------------')
  print(f'{grid.c:2d}, {grid.b:2d} | {grid.d:2d}, {grid.d:2d}')


def RunTournament(grid):
  """Run a full tournament on `grid`."""
  scores = collections.defaultdict(int)
  hero_strats = list(
      zip(ALL_STRATS, map(lambda name: globals()[name](grid), ALL_STRATS)))
  villain_strats = list(
      zip(ALL_STRATS,
          map(lambda name: globals()[name](Flipped(grid)), ALL_STRATS)))
  grid_as_nested_list = [[grid.a, grid.b], [grid.c, grid.d]]

  hero_position = None
  villain_position = None
  for hero, hero_func in hero_strats:
    for _, villain_func in villain_strats:
      for _ in range(10):
        hero_position, villain_position = (hero_func(villain_position),
                                           villain_func(hero_position))
        if hero_position == EVEN_SPLIT:
          row_vector = [(grid.a + grid.c) / 2, (grid.b + grid.d) / 2]
        elif isinstance(hero_position, Score):
          scores[hero] += hero_position.hero_value
          continue
        else:
          row_vector = grid_as_nested_list[hero_position]

        if villain_position == EVEN_SPLIT:
          scores[hero] += sum(row_vector) / 2
        elif isinstance(villain_position, Score):
          # villain_value from the perspective of the villain is the hero's
          # expected value.
          scores[hero] += villain_position.villain_value
        else:
          scores[hero] += row_vector[villain_position]
  return dict(sorted(scores.items(), key=lambda entry: entry[1], reverse=True))


# g = RandomGrid()
# PrintGrid(g)
# results = RunTournament(g)
# for strat, score in results.items():
#   print(f'{strat:9s}   {score:4.1f}')

all_grids = [
    Grid(a + 1, b + 1, c + 1, d + 1) for a in range(10) for b in range(10)
    for c in range(10) for d in range(10)
]
pool = concurrent.futures.ProcessPoolExecutor()
tournament_results = pool.map(RunTournament, all_grids, chunksize=50)
print(collections.Counter(next(iter(result)) for result in tournament_results))
