import torch
import torch.nn as nn
import torch.autograd as autograd
import torch.optim as optim
import torch.nn.functional as F
import torchvision.transforms as T
import random
import numpy as np
from collections import namedtuple, deque

device = torch.device("cpu")

class DQNAgent():
    def __init__(self,budget,state,observation_space,action_space):
        super(DQNAgent, self).__init__()
        self.budget = budget
        self.state = state
        self.next_state = []
        self.reward = []
        self.action = 0
        self.bidprice = 0
        self.episode_reward = 0
        self.win_period = 0
        self.interval = deque(maxlen=200)
        self.win_rate = deque(maxlen=1000)
        self.network = DQN(observation_space,action_space).to(device)
        self.optimizer = torch.optim.Adam(self.network.parameters())
        self.replayBuffer = ReplayBuffer
        self.act = self.network.act
        self.win_log = []
        self.bid_log = []
        self.budget_log = []
        self.win = 0
        self.consumption = deque(maxlen=200)
        self.feedback = 0
        self.log = [[0,0] for i in range(90)]
        self.w = [0 for i in range(90)]
        self.dw = [0 for i in range(90)]

    def get_price(self,w,dw,l):
        bid_price = 50
        for i in range(10,100):
            temp = (dw[i-10]/(l+0.00000001)-w[i-10])/(dw[i-10]+0.0000001)
            if abs(temp - i) < bid_price:
                bid_price = temp
        return bid_price

    def get_lambda(self,w,dw,bid_price):
        return dw[bid_price-10]/(w[bid_price-10]+bid_price*dw[bid_price-10]+0.000001)

    def update_w_dw(self,bid_price,flag, request):
        bid_price = int(bid_price)
        if bid_price > 99:
            bid_price = 99
        elif bid_price < 10:
            bid_price = 10
        self.log[bid_price-10][0] += 1
        if flag == 1:
            self.log[bid_price-10][1] += 1
        self.dw = [self.log[i][1]/request for i in range(90)]
        self.w[bid_price-10] = self.log[bid_price-10][0]/(self.log[bid_price-10][1]+0.00001)

    def setup(self):
        self.reward = []
        self.action = 0
        self.bidprice = 0
        self.episode_reward = 0
        self.win_period = 0
        self.interval = deque(maxlen=200)
        self.win_rate = deque(maxlen=200)
        self.replayBuffer = ReplayBuffer
        self.win_log = []
        self.bid_log = []
        self.budget_log = []
        self.win = 0
        self.consumption = deque(maxlen=200)
        self.feedback = 0
        self.log = [[0, 0] for i in range(90)]
        self.w = [0 for i in range(90)]
        self.dw = [0 for i in range(90)]

class DQN(nn.Module):
    def __init__(self, state_space, bid_price):
        super(DQN, self).__init__()
        self.layers = nn.Sequential(
            nn.Linear(state_space, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, bid_price)
        )
        self.state_space = state_space
        self.bid_price = bid_price
        self.q_value = 1

    def forward(self, x):
        return self.layers(x)

    def act(self, state, epsilon):
        if random.random() > epsilon:
            # print(state)
            state = torch.FloatTensor(state).unsqueeze(0).to(device)
            q_value = self.forward(state)
            self.q_value = q_value
            # print(q_value)
            action = q_value.max(1)[1].data[0]
            # print(action)
            action = action.detach().cpu().numpy()
            action = int(action)
            # print(action)
        else:
            action = random.randrange(self.bid_price)
        return action

class ReplayBuffer(object):
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        state = np.expand_dims(state, 0)
        next_state = np.expand_dims(next_state, 0)
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        state, action, reward, next_state, done = zip(*random.sample(self.buffer, batch_size))

        return np.concatenate(state), action, reward, np.concatenate(next_state), done

def compute_td_loss(model, optimizer, replay_buffer, gamma, batch_size):
    state, action, reward, next_state, done = replay_buffer.sample(batch_size)
    state = torch.FloatTensor(np.float32(state)).to(device)
    next_state = torch.FloatTensor(np.float32(next_state)).to(device)
    # print(action)
    action = torch.LongTensor(action).to(device)
    reward = torch.FloatTensor(reward).to(device)
    done = torch.FloatTensor(done).to(device)
    # print(state,action,reward,next_state,done)
    q_values = model(state)
    # print(q_values)
    next_q_values = model(next_state)
    # print(action)
    # print(next_q_values)
    q_value = q_values.gather(1, action.unsqueeze(1)).squeeze(1)

    next_q_value = max(next_q_values[0])
    # print(next_q_value)
    # print(q_value,next_q_value)
    expected_q_value = reward + gamma * next_q_value * (1 - done)
    # print(expected_q_value)
    loss = (q_value - expected_q_value.data.to(device)).pow(2).mean()

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    return loss