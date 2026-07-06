# import gymnasium as gym
# import numpy as np

# env = gym.make("MountainCar-v0",)
# num_pos_bins=20
# num_vel_bins=20


# pos_space = np.linspace(env.observation_space.low[0],env.observation_space.high[0],num_pos_bins)
# vel_space = np.linspace(env.observation_space.low[1], env.observation_space.high[1], num_vel_bins)


# def discretise_state(state):
#   pos, vel = state
#   pos_bin = np.digitize(pos, pos_space)
#   vel_bin = np.digitize(vel, vel_space)
#   return pos_bin, vel_bin

# Q = np.zeros((num_pos_bins, num_vel_bins, env.action_space.n))

# alpha = 0.1
# gamma =  0.99
# epsilon = 1.0
# epsilon_decay = 0.9995
# epsilon_min = 0.05
# num_episode = 7000

# for episode in range(num_episode):
#   state,info = env.reset()
#   state = discretise_state(state)
#   done = False
#   total_reward = 0

#   while not done:
#     if np.random.random() < epsilon:
#       action = env.action_space.sample()
#     else :
#       action = np.argmax(Q[state])

#     next_state,reward,terminated,truncated,info = env.step(action)
#     next_state_d = discretise_state(next_state)
#     done = terminated or truncated

#     best_next_q = np.max(Q[next_state_d])
#     Q[state][action] += alpha * (reward + gamma * best_next_q - Q[state][action])
  
#     state = next_state_d
#     total_reward += reward

#   epsilon = max(epsilon_min, epsilon * epsilon_decay)

#   if episode % 10 == 0:
#     print("episode", episode, "total reward", total_reward, "epsilon", round(epsilon, 3))




# test_env = gym.make("MountainCar-v0", render_mode="human")
# state, info = test_env.reset()
# state = discretise_state(state)
# done = False
# total_reward = 0

# while not done:
#     action = np.argmax(Q[state])
#     next_state, reward, terminated, truncated, info = test_env.step(action)
#     state = discretise_state(next_state)
#     total_reward += reward
#     done = terminated or truncated

# print("evaluation run, total reward:", total_reward)
# test_env.close()

import gymnasium as gym
from gymnasium import Env
from gymnasium.spaces import Box,Discrete
import pprint
import numpy as np

class State(object):
    """
    Represents a state or a point in the grid.
    coord: coordinate in grid world
    """
    def __init__(self, coord, is_terminal):
        self.coord = coord
        self.action_state_transitions = self._getActionStateTranstions()
        self.is_terminal = is_terminal
        self.reward = 5 if is_terminal else -1

    # Returns a dictionary mapping each action to the following state
    # it would put the agent in from the currrent state
    def _getActionStateTranstions(self):
        action_state_transitions = {}
        # Action 0 - up
        if self._isFirstRowState():
            action_state_transitions[0] = self.coord
        else:
            # prev row, same col
            action_state_transitions[0] = (self.coord[0]-1, self.coord[1])

        # Action 1 - right
        if self._isLastColState():
            action_state_transitions[1] = self.coord
        else:
            # same row, next col
            action_state_transitions[1] = (self.coord[0], self.coord[1]+1)

        # Action 2 - down
        if self._isLastRowState():
            action_state_transitions[2] = self.coord
        else:
            # next row, same col
            action_state_transitions[2] = (self.coord[0]+1, self.coord[1])

        # Action 3 - left
        if self._isFirstColState():
            action_state_transitions[3] = self.coord
        else:
            action_state_transitions[3] = (self.coord[0], self.coord[1]-1)

        return action_state_transitions

    def _isFirstRowState(self):
        return self.coord[0] == 0

    def _isLastRowState(self):
        return self.coord[0] == 3

    def _isFirstColState(self):
        return self.coord[1] == 0

    def _isLastColState(self):
        return self.coord[1] == 3

    # Returns if the current state is a terminal state
    def isTerminal(self):
        return self.is_terminal

    # Gets the action required to move the agent from the current state
    # to some state s2. If the agent cannot move to s2 it returns None
    def getActionTransiton(self, s2):
        for action, next_state in self.action_state_transitions.items():
            if next_state == s2.coord:
                return action
        return None

    # Returns the likelihood of ending up in state s_prime after taking
    # action a from the current state
    def getNextStateLikelihood(self, a, s_prime):
        if self.action_state_transitions[a] == s_prime.coord:
            return 1
        else:
            return 0

    # Returrn the reward for stepping into this state
    def getReward(self):
        return self.reward



class GB(Env):
  def __init__(self):
     super().__init__()
     self.action_space= Discrete(4)
     self.observation_space = Box(low=0, high=1, shape=(4,4), dtype=np.uint8)
     self.grid = np.zeros([4,4])
     self.grid[0,0]=1
     self.grid[3,3]=1

  def step(self,action):
    assert self.action_space.contains(action)
    done=False
    reward=-1

    if action == 0: # up
      new_pos = (self.pos[0] - 1, self.pos[1])
    elif action == 1: # right
      new_pos = (self.pos[0], self.pos[1] + 1)
    elif action == 2: # down
      new_pos = (self.pos[0] + 1, self.pos[1])
    elif action == 3: # left
      new_pos = (self.pos[0], self.pos[1] - 1)

    if self._onGrid(new_pos):
      self.pos = new_pos


    if self._inTerminalPos():
        done = True
        reward = 5
    return self.grid.copy(), reward, done, False, {}

  def _onGrid(self,pos):
    return pos[0] in range(0,4) and pos[1] in range(0,4)

  def _inTerminalPos(self):
    return self.grid[self.pos[0]][self.pos[1]] == 1

  def reset(self,seed=None, options=None):
    super().reset(seed=seed)
    self.pos = (0, 3)
    return self.grid.copy(), {}

  def render(self):
    new_grid = list(
        map(lambda r:
            list(map(lambda c: str(c), r)),
        self.grid)
    )
    new_grid[self.pos[0]][self.pos[1]]='X'
    pprint.pprint(new_grid)
    
    
class PolicyI():
  def __init__(self, gamma):
    self.gamma = gamma
    self.num_states = 16
    self.num_actions = 4
  def _printStateValues(self, V):
    grid = np.zeros([4,4])
    for s,v in V.items():
      x = s.coord[0]
      y = s.coord[1]
      grid[x,y]=v
      
    print("Value Function : ")
    pprint.pprint(grid)
    print('\n')
  
  def _printPolicy(self, pi):
    grid = np.zeros([4,4])
    for state, actions in pi.items():
        x = state.coord[0]
        y = state.coord[1]
        grid[x, y] = np.argmax(actions)

    arrow_grid = []
    for row_idx, row in enumerate(grid):
        arrow_grid_row = []
        for col_idx, col in enumerate(row):
            if (row_idx == 0 and col_idx == 0) or \
               (row_idx == 3 and col_idx == 3):
                arrow_grid_row.append('')
            else:
                if col == 0:
                    arrow_grid_row.append('↑')
                elif col == 1:
                    arrow_grid_row.append('→')
                elif col == 2:
                    arrow_grid_row.append('↓')
                elif col == 3:
                    arrow_grid_row.append('←')

        arrow_grid.append(arrow_grid_row)

    print("Policy:")
    pprint.pprint(arrow_grid)
    print()
    
  def initSVP(self):
    self.S=[]
    V={}
    pi={}
    
    for r in range(4):
      for c in range(4):
        is_terminal = False
        if (r==0 and c==0 ) or (r==3 and c==3):
          is_terminal = True
        s = State((r,c), is_terminal)
        self.S.append(s)
        V[s] = 0
        pi[s] = self.num_actions *[0.25]
    return V, pi

  def getAVS(self,s,V):
    action_values=[]
    for action in range(self.num_actions):
      action_value =0
      for s_prime in self.S:
        p = s.getNextStateLikelihood(action,s_prime)
        action_value += p*(s_prime.getReward() + self.gamma * V[s_prime])
      action_values.append(action_value)
    return action_values

class PIA(PolicyI):
  def __init__(self,gamma):
    super().__init__(gamma)
    
  def policyIterate(self):
    V,pi = self.initSVP()
    policy_start = False
    i = 1
    
    while not policy_start :
      print(f"Policy Iteratingggg... {i}")
      V= self._iterPolicyEval(pi,V)
      pi, V, policy_start = self._PolicyImprove(pi,V)
      self._printPolicy(pi)
      i +=1
      
  def _iterPolicyEval(self,pi,V):
    theta =0.01
    while True:
      delta=0
      for s in self.S:
        v = V[s]
        V[s]=0
        if s.isTerminal():
          continue
        for s_prime in self.S:
          p = self._p(s,s_prime,pi)
          V[s]+=p*(s_prime.getReward() + self.gamma*V[s_prime])
        delta = max(delta,abs(v-V[s]))
      self._printStateValues(V)
      if delta<theta:
        break
    return V
  
  def _PolicyImprove(self,pi,V):
    policy_start = True
    for s in self.S:
      old_best_action = np.argmax(pi[s])
      if s.isTerminal():
        continue
      action_values = self.getAVS(s,V)
      new_best_action = np.argmax(action_values)
      
      for action in range(self.num_actions):
        if action!=new_best_action:
          pi[s][action]=0
        else:
          pi[s][action]=1
      if old_best_action != new_best_action:
        policy_start = False
    return pi,V,policy_start
          
  def _p(self, s, s_prime, pi):
    transition_action = s.getActionTransiton(s_prime)
    if transition_action == None:
      return 0
    return pi[s][transition_action]

  

      
env = GB()
env.reset()
env.render()
ag = PIA(0.9)
ag.policyIterate()

# for _ in range(5):
#     env.render()
#     action = env.action_space.sample()

#     obs, reward, terminated, truncated, info = env.step(action)

#     print("Reward:", reward)

#     if terminated:
#         print("Reached terminal state!")
#         break



