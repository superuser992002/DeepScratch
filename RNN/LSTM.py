import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim


class LSTMcell(nn.Module):
    def __init__(self, hidden_size: int, input_size: int):
        super(LSTMcell, self).__init__()
        self.hidden_size = hidden_size
        self.input_size = input_size
        
        #Forget Gate
        self.Wfh = nn.Parameter(torch.zeros(self.hidden_size, self.hidden_size))
        self.Wfx = nn.Parameter(torch.zeros(self.hidden_size, self.input_size))
        self.Bf = nn.Parameter(torch.zeros(self.hidden_size))
        
        #Weighter Input Gate

        self.Wwh = nn.Parameter(torch.zeros(self.hidden_size, self.hidden_size))
        self.Wwx = nn.Parameter(torch.zeros(self.hidden_size, self.input_size))
        self.Bw = nn.Parameter(torch.zeros(self.hidden_size))
            
        #Input Gate
        self.Wih = nn.Parameter(torch.zeros(self.hidden_size, self.hidden_size))
        self.Wix = nn.Parameter(torch.zeros(self.hidden_size, self.input_size))
        self.Bi = nn.Parameter(torch.zeros(self.hidden_size))
        
        #Short-term memory Gate
        self.Wch = nn.Parameter(torch.zeros(self.hidden_size, self.hidden_size))
        self.Wcx = nn.Parameter(torch.zeros((self.hidden_size, self.input_size)))
        self.Bc = nn.Parameter(torch.zeros(self.hidden_size))



    def forward(self, c: torch.Tensor, h: torch.Tensor , x: torch.Tensor):
        batch_size = x.size()[0]
        weighted_forget = torch.einsum("xy, ay -> ax", [self.Wfh, h]) + (x@self.Wfx.T) + self.Bf.repeat(batch_size).view(batch_size, -1)
        input_weight = torch.einsum("xy, ay -> ax", [self.Wwh, h]) + (x@self.Wwx.T) + self.Bw.repeat(batch_size).view(batch_size, -1)
        input = torch.einsum("xy, ay -> ax", [self.Wih, h]) + (x@self.Wix.T) + self.Bi.repeat(batch_size).view(batch_size, -1)
        memory_weight = torch.einsum("xy, ay -> ax", [self.Wch, h]) + (x@self.Wcx.T) + self.Bc.repeat(batch_size).view(batch_size, -1)
        forgeted_c = c.mul(torch.sigmoid(weighted_forget))
        input_inject = torch.sigmoid(input_weight).mul(torch.tanh(input))
        c = forgeted_c + input_inject
        short_memory = torch.tanh(c).mul(torch.sigmoid(memory_weight))
        return c, short_memory

class LSTM(nn.Module):
    def __init__(self, hidden_size: int, input_size: int, num_layers: int, bidirectional: bool):
        super(LSTM, self).__init__()
        self.num_layers = num_layers
        self.hidden_size = hidden_size
        self.input_size = input_size
        self.bidirectional = bidirectional  
        if self.bidirectional:
            input_layer = nn.ModuleList([LSTMcell(self.hidden_size, self.input_size) for i in range(2)])
            hidden_layer = nn.ModuleList([LSTMcell(self.hidden_size, 2*self.hidden_size) for i in range(2)])
            self.mod = nn.ModuleList([input_layer])
            if self.num_layers > 1:
                self.mod.extend([hidden_layer for i in range(num_layers-1)])
        else:
            input_layer = LSTMcell(self.hidden_size, self.input_size)
            hidden_layer = LSTMcell(self.hidden_size, self.hidden_size)
            self.mod = nn.ModuleList([input_layer])
            if self.num_layers > 1:
                self.mod.extend([hidden_layer for i in range(num_layers-1)])
    def __call__(self, sequence):
        #batch_sequence = [batch_size, seq_len, embedding]
        batch_size = sequence.size()[0]
        seq_len = sequence.size()[1]
        if self.bidirectional is False:
            #Initialize C, H matrix
            C = torch.zeros(batch_size, self.hidden_size, self.num_layers)
            H = torch.zeros(batch_size, self.hidden_size, self.num_layers)
            for t in range(seq_len):
                x = sequence[:, t, :]
                for layer in range(self.num_layers):
                    C[:, :, layer], H[:, :, layer] = self.mod[layer](C[:, :, layer],H[:, :, layer],x)
                    x = H[:, :, layer].clone()
            return H[:, :, -1]
        else:
            C = torch.zeros(batch_size, seq_len+1, self.num_layers, self.hidden_size, 2)
            H = torch.zeros(batch_size, seq_len+1, self.num_layers, self.hidden_size, 2)
            for layer in range(self.num_layers):
                for t in range(seq_len):
                    x = sequence[:, t, :]
                    C[:, t+1, layer, :, 0], H[:, t+1, layer, :, 0] = self.mod[layer][0](C[:, t, layer, :, 0],
                                                                                        H[:, t, layer, :, 0], x)
                            
                for t in reversed(range(seq_len)):
                    x = sequence[:, t, :]
                    C[:, t+1, layer, :, 1], H[:, t+1, layer, :, 1] = self.mod[layer][1](C[:, t, layer, :, 1],
                                                                                        H[:, t, layer, :, 1], x)
                left = H[:, 1:, layer, :, 0]
                right = H[:, 1:, layer, :, 1]
                sequence = torch.cat([left, right], dim = 2)
            return sequence[:, -1, :]
def _test():
    LSTM_test = LSTM(128, 60, 2, False)
    sequence = torch.rand(5, 12,60)
    LSTM_test(sequence)
    LSTM_test = LSTM(128, 60, 2, True)
    sequence = torch.rand(5, 12,60)
    print(LSTM_test(sequence).shape)

if __name__ == "__main__":
    _test()