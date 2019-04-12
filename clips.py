# python3
"""Clip sim."""

import collections
import heapq
import math

rate = 30
state_attrs = [
    't',
    'history',
    'clips',
    'inventory',
    'funds',
    'price',
    'marketing',
    'wire',
    'wire_base_price',
    'research',
    'autoclippers',
    'megaclippers',
    'trust',
    'processors',
    'memory',
    'ops',
    'creat',
]
State = collections.namedtuple('State', state_attrs)
initial_state = State(*(0 for _ in range(len(state_attrs))))
initial_state = initial_state._replace(history=[], marketing=1, research=set())
queue = [initial_state]
# A maxiumum of all the places.
frontier = initial_state


def AutoclipperPrice(n):
  """The cost to purchase another autoclipper when you own n."""
  return 5 + 1.1**n


def MegaclipperPrice(m):
  """The cost to purchase another megaclipper when you own m."""
  if m == 0:
    return 500
  return 1000 * 1.07**m


def Succ(state):
  """Generate successors of `state`."""
  # First: compute the natural change.
  # Clips made by autoclippers and megaclippers.
  autoclipper_boost = 1
  if 'improved_autoclippers' in state.research:
    autoclipper_boost += 0.25
  if 'better_autoclippers' in state.research:
    autoclipper_boost += 0.5
  if 'optimized_autoclippers' in state.research:
    autoclipper_boost += 0.75
  if 'hadwiger_diagrams' in state.research:
    autoclipper_boost += 5
  megaclipper_boost = 1
  if 'improved_autoclippers' in state.research:
    megaclipper_boost += 0.25
  if 'better_autoclippers' in state.research:
    megaclipper_boost += 0.5
  if 'optimized_autoclippers' in state.research:
    megaclipper_boost += 0.75

  machined_clips = (
      state.autoclippers * autoclipper_boost +
      500 * state.megaclippers * megaclipper_boost)
  state = state._replace(
      clips=state.clips + machined_clips,
      inventory=state.inventory + machined_clips)

  if state.ops >= state.memory * 1000:
    # This crazy expression is what's in the game code, but it's basically
    # linear over the region that we care about.
    creativity_speed = (
        math.log10(state.processors) * state.processors**1.1 + state.processors
        - 1)
    # Creativity is only handed out in whole units when we cross a threshold of
    # ticks and no fractional creativity is stored. The rate of creativity
    # generation is discontinuous.
    state = state._replace(
        creat=state.creat + 1 / math.ceil(400 / creativity_speed))
  # Ops from processors
  state = state._replace(
      ops=min(state.memory * 1000, state.ops + state.processors * 10))

  # Sales
  public_demand = 0.08 / state.price * 1.1 * (state.marketing - 1)
  if 'hostile' in state.research:
    public_demand *= 5
  if 'monopoly' in state.research:
    public_demand *= 10
  # Demand less than 1000% means we won't always sell. Scale the sales by the
  # expected number of frames where we would make a sale.
  probabalistic_sales = min(1.0, public_demand / 10)
  sales = min(state.inventory,
              math.floor(0.7 * public_demand**1.15) * probabalistic_sales)
  state = state._replace(
      inventory=state.inventory - sales,
      funds=state.funds + sales * state.price)

  # Options:
  # Make clips for 1 second
  if state.wire >= rate:
    yield state._replace(
        t=state.t + 1,
        clips=state.clips + rate,
        wire=state.wire - rate,
        history=state.history + ['Make clips.'])
  # QCompute - this is on a global timer from the point the first chip is
  # acquired

  # Set price - takes 2 seconds - not allowed to change it again until some
  # research or marketing or 30 seconds pass.

  last_price_change = len(state.history) - 1
  while (last_price_change >= 0 and
         not state.history[last_price_change].startswith('Set price')):
    last_price_change -= 1
  actions_since = state.history[last_price_change:]
  if ('research' in actions_since or 'marketing' in actions_since or
      state.history[last_price_change].t + 30 < state.t):
    for delta in range(-20, 21):
      if state.price + delta >= 1:
        yield state._replace(
            t=state.t + 2,
            price=state.price + delta,
            history=state.history + [f'Set price to {state.price + delta}.'])
  # Buy clippers - takes 1 second
  funds = state.funds
  autoclippers = state.autoclippers
  while funds >= AutoclipperPrice(autoclippers) and autoclippers < 75:
    funds -= AutoclipperPrice(autoclippers)
    autoclippers += 1
  if autoclippers != state.autoclippers:
    yield state._replace(funds=funds, autoclippers=autoclippers)

  funds = state.funds
  megaclippers = state.megaclippers
  while funds >= MegaclipperPrice(megaclippers) and megaclippers < 75:
    funds -= MegaclipperPrice(megaclippers)
    megaclippers += 1
  if megaclippers != state.megaclippers:
    yield state._replace(funds=funds, megaclippers=megaclippers)

  # Buy wire - assume advances exactly 1.5% of the time. It's on a 100ms cycle,
  # so it advances every 6.6s.
  if 'wire_buyer' not in state.research:
    wire_yield = 1000
    # TODO: calculate wire yield based on research
    wire_counter = state.t / (20 / 3)
    wire_price_adjustment = 6 * math.sin(wire_counter)
    wire_price = math.ceil(state.wire_base_price + wire_price_adjustment)

    funds = state.funds
    wire = state.wire
    while funds >= wire_price:
      funds -= wire_price
      wire += wire_yield
    if wire > state.wire:
      yield state.replace_(t=t + 1, funds=state.funds, wire=state.wire)

  # Allocate trust.
  spare_trust = state.trust - (state.processors + state.memory)
  if spare_trust > 0:
    for p in range(spare_trust):
      yield state._replace(
          processors=state.processors + p,
          memory=state.memory + (spare_trust - p))

  # Don't add any states that are already dominated - that has to be the
  # heuristic: dominated/not-dominated. I would avoid something like average
  # clips per second since that will delay exploration of any strategies that
  # save up for automation. You can determine domination by tracking the
  # combined max of all the state elements. An undominated state will be maximal
  # in one of those attributes.
  return


def Goal(state):
  return state.trust >= 100 and state.creat >= 19000


def Heuristic(state):
  return state.clips / state.t


while queue:
  (_, head) = heapq.heappop(queue)
  if Goal(head):
    print(head.history)
    break

  for successor in Succ(head):
    heapq.heappush(queue, (Heuristic(successor), successor))
